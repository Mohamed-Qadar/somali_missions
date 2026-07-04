import csv
import json
import random
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext as _

from .forms import (
    ComplaintForm, ReportForm, TrackComplaintForm,
    ComplaintStatusForm, EmbassyResponseForm, ContactForm,
    LoginForm, CitizenRegistrationForm,
)
from .models import (
    Mission, Complaint, UserProfile, ComplaintEvidence,
    NotificationLog, EmbassyInvitation, AuditLog, SecureMessage, ComplaintStatusHistory,
    EscalationRule, EscalationLog, CommunityStatus,
    CommunityGroup, StudentAssociation, CommunityEvent, CommunityAnnouncement,
    CommunityRepresentative, CommunityMessage,
)

from .pdf_reports import build_pdf_report
from .utils.permissions import user_can_manage_mission, missions_for_user
from .utils.audit import log_audit_action
from .utils.rate_limit import is_rate_limited, increment_rate_limit


ALLOWED_EVIDENCE_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'application/pdf',
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 'audio/mp4',
    'video/mp4', 'video/quicktime', 'video/x-msvideo',
}
MAX_EVIDENCE_SIZE = 10 * 1024 * 1024


def _save_evidence_files(complaint, uploaded_files):
    saved = []
    for f in uploaded_files:
        if f.size > MAX_EVIDENCE_SIZE or f.content_type not in ALLOWED_EVIDENCE_TYPES:
            continue
        evidence = ComplaintEvidence.objects.create(
            complaint=complaint,
            file=f,
            file_name=f.name,
            file_size=f.size,
            file_type=f.content_type,
        )
        saved.append(evidence)
    if saved:
        complaint.refresh_priority_from_rules(has_evidence=True)
    return saved


def _record_status_change(user, complaint, old_status, new_status, note=''):
    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        old_status=old_status or '',
        new_status=new_status,
        changed_by=user if (user and user.is_authenticated) else None,
        note=note,
    )


def _ensure_default_escalation_rules():
    defaults = [
        ('Critical case manager alert', 2, UserProfile.Role.EMBASSY_MANAGER),
        ('Critical case ministry review', 6, UserProfile.Role.MINISTRY_REVIEWER),
        ('Critical case ministry administration', 24, UserProfile.Role.MINISTRY_ADMIN),
    ]
    for name, hours, role in defaults:
        EscalationRule.objects.get_or_create(
            name=name,
            defaults={'after_hours': hours, 'target_role': role, 'is_active': True},
        )


def _mission_search_filter(search_text):
    filters = Q(name__icontains=search_text) | Q(country__icontains=search_text) | Q(city__icontains=search_text)
    normalized = search_text.lower()
    embassy_terms = ('embassy', 'safaarad', 'safaaradda')
    consulate_terms = ('consulate', 'qunsuliyad', 'qunsuliyada', 'qunsuliyadda')

    if any(term in normalized for term in embassy_terms):
        filters |= Q(mission_type=Mission.MissionType.EMBASSY)
    if any(term in normalized for term in consulate_terms):
        filters |= Q(mission_type=Mission.MissionType.CONSULATE)
    return filters


def _evaluate_escalations(complaint):
    if complaint.priority != Complaint.Priority.CRITICAL:
        return []
    if complaint.status in [Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO]:
        return []

    _ensure_default_escalation_rules()
    age_hours = (timezone.now() - complaint.created_at).total_seconds() / 3600
    created = []
    for rule in EscalationRule.objects.filter(is_active=True, after_hours__lte=age_hours).order_by('after_hours'):
        exists = EscalationLog.objects.filter(complaint=complaint, rule=rule).exists()
        if exists:
            continue
        message = _(
            'Critical case %(code)s has exceeded %(hours)s hour SLA for %(mission)s.'
        ) % {'code': complaint.tracking_code, 'hours': rule.after_hours, 'mission': complaint.mission.name}
        log = EscalationLog.objects.create(
            complaint=complaint,
            rule=rule,
            target_role=rule.target_role,
            channel=EscalationLog.Channel.IN_APP,
            message=message,
        )
        NotificationLog.objects.create(
            complaint=complaint,
            recipient=rule.target_role,
            notification_type=NotificationLog.Type.IN_APP,
            subject=_('SLA escalation alert'),
            message=message,
        )
        created.append(log)
    return created


def _burst_alert_for_mission(mission):
    window_start = timezone.now() - timedelta(hours=2)
    critical_count = mission.complaints.filter(
        priority=Complaint.Priority.CRITICAL,
        created_at__gte=window_start,
    ).count()
    if critical_count < 3:
        return
    recent = mission.complaints.filter(
        priority=Complaint.Priority.CRITICAL,
        created_at__gte=window_start,
    ).order_by('-created_at').first()
    if recent and not NotificationLog.objects.filter(
        complaint=recent,
        subject__icontains='Critical complaint spike',
    ).exists():
        NotificationLog.objects.create(
            complaint=recent,
            recipient='ministry-alerts@mfa.gov.so',
            notification_type=NotificationLog.Type.WHATSAPP,
            subject='Critical complaint spike',
            message=f'{critical_count} critical complaints were submitted against {mission.name} within 2 hours.',
        )


def _captcha_numbers(request):
    if 'captcha_num1' not in request.session:
        request.session['captcha_num1'] = random.randint(1, 9)
        request.session['captcha_num2'] = random.randint(1, 9)
    return request.session['captcha_num1'], request.session['captcha_num2']


def _refresh_captcha(request):
    request.session['captcha_num1'] = random.randint(1, 9)
    request.session['captcha_num2'] = random.randint(1, 9)
    return request.session['captcha_num1'], request.session['captcha_num2']


def mission_list(request):
    q = request.GET.get('q', '').strip()
    country = request.GET.get('country', '').strip()
    mission_type = request.GET.get('mission_type', '').strip()
    min_rating = request.GET.get('min_rating', '').strip()
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    missions = Mission.objects.annotate(
        complaint_count=Count('complaints'),
        average_rating=Avg('complaints__rating'),
    ).order_by('country', 'name')

    if q:
        missions = missions.filter(_mission_search_filter(q))
    if country:
        missions = missions.filter(country__iexact=country)
    if mission_type in ('EM', 'CO'):
        missions = missions.filter(mission_type=mission_type)
    if min_rating:
        try:
            missions = missions.filter(average_rating__gte=float(min_rating))
        except ValueError:
            pass

    countries = Mission.objects.values_list('country', flat=True).distinct().order_by('country')
    map_missions = [
        {
            'name': m.name,
            'city': m.city,
            'country': m.country,
            'lat': float(m.latitude) if m.latitude else None,
            'lng': float(m.longitude) if m.longitude else None,
            'url': f'/mission/{m.pk}/',
        }
        for m in missions if m.latitude and m.longitude
    ]
    monthly_complaints = Complaint.objects.filter(created_at__gte=month_start)
    resolved_statuses = [Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO]

    return render(request, 'missions/index.html', {
        'missions': missions,
        'search_query': q,
        'countries': countries,
        'selected_country': country,
        'selected_mission_type': mission_type,
        'selected_min_rating': min_rating,
        'map_missions_json': json.dumps(map_missions),
        'home_stats': {
            'total_missions': Mission.objects.count(),
            'monthly_complaints': monthly_complaints.count(),
            'average_rating': Complaint.objects.aggregate(avg=Avg('rating'))['avg'] or 0,
            'monthly_resolved': monthly_complaints.filter(status__in=resolved_statuses).count(),
        },
    })


def mission_detail(request, pk):
    mission = get_object_or_404(
        Mission.objects.annotate(average_rating=Avg('complaints__rating')),
        pk=pk,
    )
    captcha = _captcha_numbers(request)
    rate_limited = is_rate_limited(request, f'complaint_mission_{pk}', limit=3)

    if request.method == 'POST':
        if rate_limited:
            form = ComplaintForm(request.POST, captcha_expected=captcha)
            form.add_error(None, _('Daily submission limit reached for this mission. Please try again tomorrow.'))
        else:
            form = ComplaintForm(request.POST, captcha_expected=captcha)
            if form.is_valid():
                complaint = form.save(commit=False)
                complaint.mission = mission
                complaint.save()
                increment_rate_limit(request, f'complaint_mission_{pk}')
                _refresh_captcha(request)
                request.session['last_tracking_code'] = complaint.tracking_code
                return redirect('complaint_success')
        _refresh_captcha(request)
        captcha = _captcha_numbers(request)
    else:
        form = ComplaintForm(captcha_expected=captcha)

    complaints = mission.complaints.all().prefetch_related('responses').order_by('-created_at')[:20]
    services = mission.services.filter(is_active=True).prefetch_related('required_documents')
    support_contacts = mission.support_contacts.filter(is_public=True)
    nearby_community_groups = CommunityGroup.objects.filter(
        status=CommunityStatus.VERIFIED,
        country__iexact=mission.country,
        city__iexact=mission.city,
    )[:6]
    nearby_student_associations = StudentAssociation.objects.filter(
        status=CommunityStatus.VERIFIED,
        country__iexact=mission.country,
        city__iexact=mission.city,
    )[:6]

    return render(request, 'missions/mission_detail.html', {
        'mission': mission,
        'form': form,
        'complaints': complaints,
        'rate_limited': rate_limited,
        'services': services,
        'support_contacts': support_contacts,
        'nearby_community_groups': nearby_community_groups,
        'nearby_student_associations': nearby_student_associations,
    })


def complaint_success(request):
    tracking_code = request.session.pop('last_tracking_code', None)
    return render(request, 'missions/complaint_success.html', {'tracking_code': tracking_code})


def track_complaint(request):
    complaint = None
    form = TrackComplaintForm(request.GET if request.GET.get('tracking_code') else None)
    
    timeline_statuses = [
        ('SUBMITTED', _('Submitted')),
        ('ASSIGNED', _('Assigned')),
        ('UNDER_REVIEW', _('Under Review')),
        ('INVESTIGATION', _('Investigation')),
        ('AWAITING_RESPONSE', _('Awaiting Response')),
        ('RESOLVED', _('Resolved')),
        ('CLOSED', _('Closed')),
    ]
    
    if request.GET.get('tracking_code') and form.is_valid():
        code = form.cleaned_data['tracking_code'].strip().upper()
        complaint = Complaint.objects.filter(tracking_code=code).select_related('mission').first()
        if not complaint:
            form.add_error('tracking_code', _('No complaint found with this tracking code.'))
        else:
            # Store tracked code in session for message authorization
            request.session['tracked_code'] = code
            
    current_step_idx = 0
    messages = []
    if complaint:
        messages = complaint.secure_messages.all().order_by('created_at')
        status_val = complaint.status
        if status_val == 'NEW':
            status_val = 'SUBMITTED'
        elif status_val == 'PRO':
            status_val = 'UNDER_REVIEW'
        elif status_val == 'RES':
            status_val = 'RESOLVED'
        elif status_val == 'CLO':
            status_val = 'CLOSED'
            
        for idx, (code_name, label) in enumerate(timeline_statuses):
            if code_name == status_val:
                current_step_idx = idx
                break
                
    return render(request, 'missions/track.html', {
        'form': form,
        'complaint': complaint,
        'timeline_statuses': timeline_statuses,
        'current_step_idx': current_step_idx,
        'messages': messages,
    })


def privacy_view(request):
    return render(request, 'missions/privacy.html')


def faq_view(request):
    return render(request, 'missions/faq.html')


def analysis_view(request):
    period = request.GET.get('period', '30')
    now = timezone.now()

    if period == '365':
        start_date = now - timedelta(days=365)
        period_label = _('Last 365 days')
        chart_days = 365
    elif period == 'all':
        start_date = None
        period_label = _('All time')
        chart_days = 90
    else:
        period = '30'
        start_date = now - timedelta(days=30)
        period_label = _('Last 30 days')
        chart_days = 30

    complaint_filter = Q()
    if start_date:
        complaint_filter = Q(complaints__created_at__gte=start_date)

    most_complained = Mission.objects.annotate(
        complaint_count=Count('complaints', filter=complaint_filter),
    ).filter(complaint_count__gt=0).order_by('-complaint_count')[:10]

    highest_rated = Mission.objects.annotate(
        avg_rating=Avg('complaints__rating', filter=complaint_filter),
    ).filter(avg_rating__isnull=False).order_by('-avg_rating')[:10]

    lowest_rated = Mission.objects.annotate(
        avg_rating=Avg('complaints__rating', filter=complaint_filter),
    ).filter(avg_rating__isnull=False).order_by('avg_rating')[:10]

    complaints_qs = Complaint.objects.all()
    if start_date:
        complaints_qs = complaints_qs.filter(created_at__gte=start_date)

    category_stats = []
    for row in complaints_qs.values('category').annotate(count=Count('id')).order_by('-count'):
        label = dict(Complaint.Category.choices).get(row['category'], row['category'])
        category_stats.append({'label': label, 'count': row['count']})

    daily_labels = []
    daily_counts = []
    days = chart_days
    if period == 'all' and complaints_qs.exists():
        first_date = complaints_qs.order_by('created_at').first().created_at
        days = min(90, (now - first_date).days + 1)
    for offset in range(days - 1, -1, -1):
        day = (now - timedelta(days=offset)).date()
        daily_labels.append(day.strftime('%b %d'))
        daily_counts.append(complaints_qs.filter(created_at__date=day).count())

    mission_chart_labels = [m.name[:25] for m in most_complained[:8]]
    mission_chart_counts = [m.complaint_count for m in most_complained[:8]]

    return render(request, 'missions/analysis.html', {
        'most_complained': most_complained,
        'highest_rated': highest_rated,
        'lowest_rated': lowest_rated,
        'category_stats': category_stats,
        'period': period,
        'period_label': period_label,
        'daily_labels_json': json.dumps(daily_labels),
        'daily_counts_json': json.dumps(daily_counts),
        'mission_labels_json': json.dumps(mission_chart_labels),
        'mission_counts_json': json.dumps(mission_chart_counts),
    })


def about_view(request):
    return render(request, 'missions/about.html')


def contact_view(request):
    form = ContactForm(request.POST or None)
    submitted = False
    if request.method == 'POST':
        if is_rate_limited(request, 'contact', limit=5):
            form.add_error(None, _('Too many messages sent today. Please try again tomorrow.'))
        elif form.is_valid():
            form.save()
            increment_rate_limit(request, 'contact')
            submitted = True
            form = ContactForm()
    return render(request, 'missions/contact.html', {'form': form, 'submitted': submitted})


def _filtered_complaints(form):
    complaints_qs = Complaint.objects.select_related('mission').all()
    consulate = form.cleaned_data.get('consulate')
    date_range = form.cleaned_data.get('date')

    if consulate and consulate != 'All Consulates':
        complaints_qs = complaints_qs.filter(mission__name__icontains=consulate)
    if date_range:
        complaints_qs = complaints_qs.filter(created_at__date__gte=date_range)
    return complaints_qs


@login_required
def report_dashboard(request):
    last_30_days = timezone.now() - timedelta(days=30)
    missions = Mission.objects.annotate(
        complaint_count=Count('complaints'),
        average_rating=Avg('complaints__rating'),
    ).order_by('-complaint_count')

    form = ReportForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        complaints_qs = _filtered_complaints(form)
        buffer = build_pdf_report(
            form.cleaned_data['report_type'],
            complaints_qs,
            missions,
            form.cleaned_data,
        )
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="somali_missions_report.pdf"'
        return response

    total = Complaint.objects.count()
    negative = Complaint.objects.filter(rating__lte=2).count()
    negative_ratio = f'{(negative / total * 100):.1f}%' if total else '0%'

    recent_complaints = Complaint.objects.select_related('mission').order_by('-created_at')[:5]

    return render(request, 'missions/reports.html', {
        'missions': missions[:6],
        'summary_cards': [
            {'label': _('Total Complaints'), 'value': total},
            {'label': _('Monthly Complaints'), 'value': Complaint.objects.filter(created_at__gte=last_30_days).count()},
            {'label': _('Avg. Star Rating'), 'value': f"{Complaint.objects.aggregate(avg=Avg('rating'))['avg'] or 0:.1f}"},
            {'label': _('Negative Ratio'), 'value': negative_ratio},
        ],
        'recent_complaints': recent_complaints,
        'form': form,
    })


@login_required
def export_complaints_csv(request):
    form = ReportForm(request.GET or None)
    complaints_qs = Complaint.objects.select_related('mission').all()
    if form.is_valid():
        complaints_qs = _filtered_complaints(form)

    log_audit_action(request.user, None, 'Export', 'Exported complaints to CSV.', request=request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="complaints_export.csv"'
    writer = csv.writer(response)
    writer.writerow(['tracking_code', 'mission', 'subject', 'category', 'rating', 'status', 'sentiment', 'created_at'])
    for complaint in complaints_qs.order_by('-created_at'):
        writer.writerow([
            complaint.tracking_code,
            complaint.mission.name,
            complaint.subject,
            complaint.get_category_display(),
            complaint.rating,
            complaint.get_status_display(),
            complaint.get_sentiment_display(),
            complaint.created_at.isoformat(),
        ])
    return response


@login_required
def export_complaints_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill

    form = ReportForm(request.GET or None)
    complaints_qs = Complaint.objects.select_related('mission').all()
    if form.is_valid():
        complaints_qs = _filtered_complaints(form)

    log_audit_action(request.user, None, 'Export', 'Exported complaints to Excel.', request=request)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Complaints'

    headers = ['Tracking Code', 'Mission', 'Country', 'Subject', 'Category', 'Rating', 'Status', 'Sentiment', 'Created At']
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color='183059', end_color='183059', fill_type='solid')

    for complaint in complaints_qs.order_by('-created_at'):
        sheet.append([
            complaint.tracking_code,
            complaint.mission.name,
            complaint.mission.country,
            complaint.subject,
            complaint.get_category_display(),
            complaint.rating,
            complaint.get_status_display(),
            complaint.get_sentiment_display(),
            complaint.created_at.replace(tzinfo=None).isoformat(),
        ])

    for column_cells in sheet.columns:
        length = max(len(str(cell.value)) for cell in column_cells if cell.value is not None) if column_cells else 10
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 50)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="complaints_export.xlsx"'
    workbook.save(response)
    return response


def redirect_after_login(user):
    try:
        role = user.profile.role
    except Exception:
        role = 'CITIZEN'
    if role == 'CITIZEN':
        return 'citizen_dashboard'
    elif role == 'EMBASSY_OFFICER':
        return 'embassy_officer_dashboard'
    elif role == 'EMBASSY_MANAGER':
        return 'embassy_manager_dashboard'
    elif role == 'MINISTRY_REVIEWER':
        return 'ministry_reviewer_dashboard'
    elif role == 'MINISTRY_ADMIN':
        return 'ministry_admin_dashboard'
    elif role == 'EMBASSY_STAFF':
        return 'staff_dashboard'
    else:
        return 'home'


def login_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_after_login(request.user))
    error = None
    login_rate_limited = is_rate_limited(request, 'login_attempts', limit=10, window_seconds=600)
    if request.method == 'POST':
        if login_rate_limited:
            error = _('Too many login attempts. Please wait a few minutes and try again.')
            form = LoginForm(request.POST)
        else:
            form = LoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                remember_me = form.cleaned_data['remember_me']
                user = authenticate(request, username=username, password=password)
                if user is not None and user.is_active:
                    login(request, user)
                    if remember_me:
                        request.session.set_expiry(1209600)  # 2 weeks
                    else:
                        request.session.set_expiry(0)  # browser close
                    return redirect(redirect_after_login(user))
                increment_rate_limit(request, 'login_attempts', window_seconds=600)
                error = _('Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'missions/login.html', {'form': form, 'error': error})


def logout_view(request):
    logout(request)
    return redirect('home')


def _send_verification_email(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        f'/verify-email/{uidb64}/{token}/'
    )
    send_mail(
        subject=_('Verify your Somali Missions account'),
        message=_(
            'Please confirm your email address by opening this link:\n%(url)s'
        ) % {'url': verify_url},
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[user.email],
        fail_silently=True,
    )
    return uidb64, token


def register_view(request):
    if request.user.is_authenticated:
        return redirect(redirect_after_login(request.user))
    if request.method == 'POST':
        form = CitizenRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            uidb64, token = _send_verification_email(request, user)
            return render(request, 'missions/verify_pending.html', {
                'email': user.email,
                'uidb64': uidb64,
                'token': token,
                'is_debug': settings.DEBUG,
            })
    else:
        form = CitizenRegistrationForm()
    return render(request, 'missions/register.html', {'form': form})


def verify_email_view(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, 'missions/verify_success.html', {'invalid': True})

    profile = user.profile
    profile.email_verified = True
    profile.save(update_fields=['email_verified'])
    return render(request, 'missions/verify_success.html', {'invalid': False})


@login_required
def citizen_dashboard(request):
    if request.user.profile.role != UserProfile.Role.CITIZEN:
        return redirect('home')
        
    complaints = Complaint.objects.filter(citizen_user=request.user, is_anonymous=False).order_by('-created_at')
    
    total = complaints.count()
    open_cases = complaints.filter(status__in=[
        Complaint.Status.SUBMITTED,
        Complaint.Status.ASSIGNED,
        Complaint.Status.UNDER_REVIEW,
        Complaint.Status.INVESTIGATION,
        Complaint.Status.AWAITING_RESPONSE,
        Complaint.Status.NEW,
        Complaint.Status.PRO
    ]).count()
    resolved = complaints.filter(status__in=[Complaint.Status.RESOLVED, Complaint.Status.RES]).count()
    closed = complaints.filter(status__in=[Complaint.Status.CLOSED, Complaint.Status.CLO]).count()
    
    return render(request, 'missions/citizen_dashboard.html', {
        'complaints': complaints,
        'total': total,
        'open_cases': open_cases,
        'resolved': resolved,
        'closed': closed,
    })


def submit_satisfaction(request, tracking_code):
    complaint = get_object_or_404(Complaint, tracking_code=tracking_code)
    if request.method == 'POST':
        rating = request.POST.get('satisfaction_rating')
        comment = request.POST.get('satisfaction_comment', '').strip()
        if rating:
            complaint.satisfaction_rating = int(rating)
            complaint.satisfaction_comment = comment
            complaint.save()
            
            # Log notification to Admin/Oversight
            NotificationLog.objects.create(
                complaint=complaint,
                recipient="ministry-admin@somali-gov.so",
                notification_type=NotificationLog.Type.EMAIL,
                subject=f"Satisfaction Feedback - {complaint.tracking_code}",
                message=f"Citizen feedback: {rating}/5 stars. Comment: {comment}"
            )
    return redirect(f'/track/?tracking_code={tracking_code}')




@login_required
def staff_dashboard(request):
    user_missions = missions_for_user(request.user)
    if not user_missions.exists():
        return render(request, 'missions/staff_dashboard.html', {'missions': user_missions, 'denied': True})
    return render(request, 'missions/staff_dashboard.html', {'missions': user_missions, 'denied': False})


@login_required
def staff_mission_manage(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if not user_can_manage_mission(request.user, mission):
        return redirect('staff_dashboard')

    complaints = mission.complaints.all().order_by('-created_at')
    selected_id = request.GET.get('complaint') or request.POST.get('complaint_id')
    selected_complaint = None
    status_form = ComplaintStatusForm(prefix='status')
    response_form = EmbassyResponseForm(prefix='response')

    if selected_id:
        selected_complaint = get_object_or_404(Complaint, pk=selected_id, mission=mission)
        status_form = ComplaintStatusForm(instance=selected_complaint, prefix='status')
        response_form = EmbassyResponseForm(prefix='response')

        if request.method == 'POST' and 'save_status' in request.POST:
            status_form = ComplaintStatusForm(request.POST, instance=selected_complaint, prefix='status')
            if status_form.is_valid():
                old_status = selected_complaint.status
                status_form.save()
                selected_complaint.refresh_from_db()
                _record_status_change(request.user, selected_complaint, old_status, selected_complaint.status, _('Staff dashboard status update.'))
                if selected_complaint.citizen_user:
                    from notifications.channels import notify
                    notify(
                        selected_complaint.citizen_user,
                        title=_('Complaint %(code)s: %(status)s') % {
                            'code': selected_complaint.tracking_code, 'status': selected_complaint.get_status_display(),
                        },
                        body=_('Your complaint about %(mission)s is now %(status)s.') % {
                            'mission': mission.name, 'status': selected_complaint.get_status_display(),
                        },
                        link_url=f'/track/?tracking_code={selected_complaint.tracking_code}',
                        channels=['email'],
                    )
                messages.success(request, _('Complaint status updated to %(status)s.') % {'status': selected_complaint.get_status_display()})
                return redirect(f'{request.path}?complaint={selected_complaint.pk}')

        if request.method == 'POST' and 'save_response' in request.POST:
            response_form = EmbassyResponseForm(request.POST, prefix='response')
            if response_form.is_valid():
                response = response_form.save(commit=False)
                response.complaint = selected_complaint
                response.save()
                messages.success(request, _('Your response has been saved.'))
                return redirect(f'{request.path}?complaint={selected_complaint.pk}')

    return render(request, 'missions/staff_mission_manage.html', {
        'mission': mission,
        'complaints': complaints,
        'selected_complaint': selected_complaint,
        'status_form': status_form,
        'response_form': response_form,
    })


def submit_complaint_wizard(request):
    captcha = _captcha_numbers(request)
    missions = Mission.objects.all().order_by('country', 'name')
    selected_mission_id = request.GET.get('mission', '')
    wizard_rate_limited = is_rate_limited(request, 'complaint_wizard', limit=5)

    if request.method == 'POST':
        if wizard_rate_limited:
            _refresh_captcha(request)
            captcha = _captcha_numbers(request)
            return render(request, 'missions/submit_wizard.html', {
                'missions': missions,
                'selected_mission_id': selected_mission_id,
                'captcha_error': _('Daily submission limit reached from this network. Please try again tomorrow.'),
                'captcha': captcha,
            })
        mission_id = request.POST.get('mission')
        category = request.POST.get('category', 'OTHER')
        rating = request.POST.get('rating', '3')
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        is_anonymous = request.POST.get('is_anonymous') == 'true'
        currently_at_mission = request.POST.get('currently_at_mission') == 'true'
        travelled_from_another_city = request.POST.get('travelled_from_another_city') == 'true'
        no_accommodation = request.POST.get('no_accommodation') == 'true'
        has_return_ticket = request.POST.get('has_return_ticket') == 'true'
        waiting_more_than_two_hours = request.POST.get('waiting_more_than_two_hours') == 'true'
        
        full_name = request.POST.get('full_name', '').strip() if not is_anonymous else ''
        email = request.POST.get('email', '').strip() if not is_anonymous else ''
        phone = request.POST.get('phone', '').strip() if not is_anonymous else ''
        original_language = request.POST.get('original_language', 'en')
        
        captcha_answer = request.POST.get('captcha_answer')
        expected_captcha = captcha[0] + captcha[1]
        try:
            is_valid_captcha = int(captcha_answer) == expected_captcha
        except (ValueError, TypeError):
            is_valid_captcha = False
            
        if not is_valid_captcha:
            _refresh_captcha(request)
            captcha = _captcha_numbers(request)
            return render(request, 'missions/submit_wizard.html', {
                'missions': missions,
                'selected_mission_id': selected_mission_id,
                'captcha_error': _('Incorrect security check answer.'),
                'captcha': captcha,
            })
            
        mission = get_object_or_404(Mission, id=mission_id)
        complaint = Complaint(
            mission=mission,
            category=category,
            rating=int(rating),
            subject=subject,
            message=message,
            is_anonymous=is_anonymous,
            full_name=full_name,
            email=email,
            phone=phone,
            original_language=original_language,
            currently_at_mission=currently_at_mission,
            travelled_from_another_city=travelled_from_another_city,
            no_accommodation=no_accommodation,
            has_return_ticket=has_return_ticket,
            waiting_more_than_two_hours=waiting_more_than_two_hours,
        )
        if request.user.is_authenticated and not is_anonymous:
            complaint.citizen_user = request.user
            
        complaint.save()
        
        saved_evidence = _save_evidence_files(complaint, request.FILES.getlist('evidence_files'))
        if not saved_evidence:
            complaint.refresh_priority_from_rules(has_evidence=False)
        _record_status_change(None, complaint, '', complaint.status, _('Citizen submitted complaint.'))
        _burst_alert_for_mission(mission)
            
        # Log simulated notification
        recipient_email = email or (request.user.email if (request.user.is_authenticated and not is_anonymous) else '')
        if recipient_email:
            NotificationLog.objects.create(
                complaint=complaint,
                recipient=recipient_email,
                notification_type=NotificationLog.Type.EMAIL,
                subject="Complaint Submitted - " + complaint.tracking_code,
                message=f"Dear Citizen,\n\nYour complaint regarding {mission.name} has been successfully submitted.\nTracking Code: {complaint.tracking_code}\nStatus: Submitted\n\nYou can track the progress on our portal."
            )
        if complaint.priority == Complaint.Priority.CRITICAL:
            NotificationLog.objects.create(
                complaint=complaint,
                recipient=mission.email or 'mission-duty-officer@mfa.gov.so',
                notification_type=NotificationLog.Type.EMAIL,
                subject=f"Critical complaint received - {complaint.tracking_code}",
                message=f"Critical factors: {complaint.critical_reason or 'Emergency category'}",
            )
            
        increment_rate_limit(request, 'complaint_wizard')
        _refresh_captcha(request)
        request.session['last_tracking_code'] = complaint.tracking_code
        return redirect('complaint_success')

    else:
        _refresh_captcha(request)
        captcha = _captcha_numbers(request)

    return render(request, 'missions/submit_wizard.html', {
        'missions': missions,
        'selected_mission_id': selected_mission_id,
        'captcha': captcha,
    })


def emergency_hotline_view(request):
    missions = Mission.objects.exclude(phone='').order_by('country')
    return render(request, 'missions/emergency.html', {'missions': missions})


def submit_emergency_view(request):
    missions = Mission.objects.all().order_by('country', 'name')
    selected_mission_id = request.GET.get('mission', '')
    emergency_rate_limited = is_rate_limited(request, 'emergency_submit', limit=8)

    if request.method == 'POST':
        if emergency_rate_limited:
            return render(request, 'missions/submit_emergency.html', {
                'missions': missions,
                'selected_mission_id': selected_mission_id,
                'rate_limit_error': _('This network has reached the daily emergency submission limit. If this is a genuine emergency, please call the mission or your local police directly.'),
            })
        mission_id = request.POST.get('mission')
        category = request.POST.get('category', 'EMERGENCY')
        message = request.POST.get('message', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        currently_at_mission = request.POST.get('currently_at_mission') == 'true'
        travelled_from_another_city = request.POST.get('travelled_from_another_city') == 'true'
        no_accommodation = request.POST.get('no_accommodation') == 'true'
        has_return_ticket = request.POST.get('has_return_ticket') == 'true'
        waiting_more_than_two_hours = request.POST.get('waiting_more_than_two_hours') == 'true'
        
        mission = get_object_or_404(Mission, id=mission_id)
        
        # Emergency complaints bypass rating and are automatically CRITICAL
        complaint = Complaint(
            mission=mission,
            category=category,
            rating=5,  # Auto-top priority indicators
            subject=f"EMERGENCY REPORT - {dict(Complaint.Category.choices).get(category, category)}",
            message=message,
            is_anonymous=False,
            full_name=full_name or "Emergency Reporter",
            email=email,
            phone=phone,
            priority=Complaint.Priority.CRITICAL,
            status=Complaint.Status.SUBMITTED,
            currently_at_mission=currently_at_mission,
            travelled_from_another_city=travelled_from_another_city,
            no_accommodation=no_accommodation,
            has_return_ticket=has_return_ticket,
            waiting_more_than_two_hours=waiting_more_than_two_hours,
        )
        if request.user.is_authenticated:
            complaint.citizen_user = request.user
        complaint.save()
        
        saved_evidence = _save_evidence_files(complaint, request.FILES.getlist('evidence_files'))
        complaint.refresh_priority_from_rules(has_evidence=bool(saved_evidence))
        _record_status_change(None, complaint, '', complaint.status, _('Emergency complaint submitted.'))
        _burst_alert_for_mission(mission)
            
        # Create SMS notification log (Critical)
        if phone:
            NotificationLog.objects.create(
                complaint=complaint,
                recipient=phone,
                notification_type=NotificationLog.Type.SMS,
                message=f"CRITICAL ALERT: Your emergency report is received. Case Code: {complaint.tracking_code}. A review officer is dispatched."
            )
        NotificationLog.objects.create(
            complaint=complaint,
            recipient='ministry-alerts@mfa.gov.so',
            notification_type=NotificationLog.Type.WHATSAPP,
            subject=f"Emergency mission alert - {complaint.tracking_code}",
            message=f"Emergency case for {mission.name}. Critical factors: {complaint.critical_reason}",
        )

        increment_rate_limit(request, 'emergency_submit')
        request.session['last_tracking_code'] = complaint.tracking_code
        return redirect('complaint_success')
        
    return render(request, 'missions/submit_emergency.html', {
        'missions': missions,
        'selected_mission_id': selected_mission_id,
    })


@login_required
def ministry_operations_view(request):
    # Check permissions
    if request.user.profile.role not in [UserProfile.Role.MINISTRY_REVIEWER, UserProfile.Role.MINISTRY_ADMIN] and not request.user.is_superuser:
        return redirect('home')
        
    complaints = Complaint.objects.select_related('mission').all().order_by('-created_at')
    
    # Urgent alert cases (Critical Priority)
    urgent_alerts = complaints.filter(priority=Complaint.Priority.CRITICAL, status__in=[
        Complaint.Status.SUBMITTED, Complaint.Status.ASSIGNED, Complaint.Status.UNDER_REVIEW,
        Complaint.Status.INVESTIGATION, Complaint.Status.AWAITING_RESPONSE, Complaint.Status.NEW, Complaint.Status.PRO
    ])
    for alert in urgent_alerts[:100]:
        _evaluate_escalations(alert)
    
    # SLA violations: unresolved complaints older than 7 days
    sla_limit = timezone.now() - timedelta(days=7)
    sla_violations = complaints.filter(
        created_at__lt=sla_limit,
        status__in=[
            Complaint.Status.SUBMITTED, Complaint.Status.ASSIGNED, Complaint.Status.UNDER_REVIEW,
            Complaint.Status.INVESTIGATION, Complaint.Status.AWAITING_RESPONSE, Complaint.Status.NEW, Complaint.Status.PRO
        ]
    )
    
    # Geographic data map pins
    map_pins = []
    missions_with_complaints = Mission.objects.annotate(
        complaint_count=Count('complaints'),
        avg_rating=Avg('complaints__rating')
    ).filter(latitude__isnull=False, longitude__isnull=False)
    
    for m in missions_with_complaints:
        map_pins.append({
            'name': m.name,
            'city': m.city,
            'country': m.country,
            'lat': float(m.latitude),
            'lng': float(m.longitude),
            'complaints': m.complaint_count,
            'avg_rating': round(m.avg_rating or 0, 1),
            'url': f'/staff/mission/{m.pk}/'
        })
        
    # Calculate performance metrics per embassy (Requirement 30)
    embassy_perf = []
    all_missions = Mission.objects.all().order_by('name')
    for m in all_missions:
        m_complaints = complaints.filter(mission=m)
        m_total = m_complaints.count()
        m_unresolved = m_complaints.filter(status__in=[
            Complaint.Status.SUBMITTED, Complaint.Status.ASSIGNED, Complaint.Status.UNDER_REVIEW,
            Complaint.Status.INVESTIGATION, Complaint.Status.AWAITING_RESPONSE, Complaint.Status.NEW, Complaint.Status.PRO
        ]).count()
        m_resolved = m_complaints.filter(status__in=[
            Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO
        ]).count()
        
        m_res_rate = round((m_resolved / m_total * 100), 1) if m_total else 100.0
        
        # Avg satisfaction rating (out of 5)
        sat_avg = m_complaints.filter(satisfaction_rating__isnull=False).aggregate(avg=Avg('satisfaction_rating'))['avg']
        sat_score_pct = round(float(sat_avg) * 20, 1) if sat_avg else None
        
        # Average response time in days
        m_resolved_cases = m_complaints.filter(status__in=[
            Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO
        ])
        t_days = 0
        m_res_count = m_resolved_cases.count()
        for c in m_resolved_cases:
            t_days += (c.updated_at - c.created_at).days
        m_avg_time = round(t_days / m_res_count, 1) if m_res_count else 0.0
        
        # Flag condition: average satisfaction is less than 60% (3.0 stars) and unresolved cases > 5
        is_flagged = (sat_avg is not None and sat_avg < 3.0 and m_unresolved > 5)
        
        embassy_perf.append({
            'mission': m,
            'total': m_total,
            'unresolved': m_unresolved,
            'resolution_rate': m_res_rate,
            'satisfaction_rate': sat_score_pct,
            'avg_response_time': m_avg_time,
            'is_flagged': is_flagged
        })
        
    system_audit_logs = []
    if request.user.profile.role == UserProfile.Role.MINISTRY_ADMIN or request.user.is_superuser:
        system_audit_logs = AuditLog.objects.select_related('user', 'complaint').all().order_by('-timestamp')[:50]

    return render(request, 'missions/ministry_operations.html', {
        'complaints': complaints[:30],
        'urgent_alerts': urgent_alerts,
        'sla_violations': sla_violations,
        'escalation_logs': EscalationLog.objects.select_related('complaint', 'complaint__mission').all()[:20],
        'map_pins_json': json.dumps(map_pins),
        'embassy_perf': embassy_perf,
        'system_audit_logs': system_audit_logs,
    })


@login_required
def ministry_analytics_view(request):
    if request.user.profile.role not in [UserProfile.Role.MINISTRY_REVIEWER, UserProfile.Role.MINISTRY_ADMIN] and not request.user.is_superuser:
        return redirect('home')

    period = request.GET.get('period', '30')
    cache_key = f'ministry_analytics_data_v2:{period}'
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return render(request, 'missions/ministry_analytics.html', cached_context)

    now = timezone.now()

    if period == '365':
        start_date = now - timedelta(days=365)
    elif period == 'all':
        start_date = None
    else:
        start_date = now - timedelta(days=30)
        
    complaints = Complaint.objects.all()
    if start_date:
        complaints = complaints.filter(created_at__gte=start_date)
        
    # Stats 1: Complaints by Embassy
    embassy_stats = list(complaints.values('mission__name').annotate(count=Count('id')).order_by('-count')[:8])
    embassy_labels = [x['mission__name'] for x in embassy_stats]
    embassy_counts = [x['count'] for x in embassy_stats]
    
    # Stats 2: Complaints by Country
    country_stats = list(complaints.values('mission__country').annotate(count=Count('id')).order_by('-count')[:8])
    country_labels = [x['mission__country'] for x in country_stats]
    country_counts = [x['count'] for x in country_stats]
    
    # Stats 3: Complaints by Category
    category_stats_qs = list(complaints.values('category').annotate(count=Count('id')).order_by('-count'))
    # str() forces gettext_lazy proxies to concrete strings - json.dumps cannot
    # serialize the lazy __proxy__ objects that Category.choices labels are.
    category_display = dict(Complaint.Category.choices)
    category_labels = [str(category_display.get(x['category'], x['category'])) for x in category_stats_qs]
    category_counts = [x['count'] for x in category_stats_qs]
    
    # Stats 4: Monthly Trends (last 6 months)
    monthly_labels = []
    monthly_counts = []
    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i*30)
        label = target_date.strftime('%B %Y')
        monthly_labels.append(label)
        monthly_counts.append(complaints.filter(created_at__year=target_date.year, created_at__month=target_date.month).count())
        
    # Stats 5: Resolution Times
    resolved_cases = complaints.filter(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO])
    total_days = 0
    resolved_count = resolved_cases.count()
    for c in resolved_cases:
        total_days += (c.updated_at - c.created_at).days
    avg_resolution_days = round(total_days / resolved_count, 1) if resolved_count else 0.0
    
    # Stats 6: Satisfaction Rates
    satisfaction_avg = complaints.filter(satisfaction_rating__isnull=False).aggregate(avg=Avg('satisfaction_rating'))['avg'] or 0.0
    satisfaction_rate = round((float(satisfaction_avg) / 5.0) * 100, 1) if satisfaction_avg else 0.0

    # Stats 7: Complaints per assigned officer
    officer_stats = list(
        complaints.exclude(assigned_officer__isnull=True)
        .values('assigned_officer__username').annotate(count=Count('id')).order_by('-count')[:10]
    )

    # Stats 8: Country x Month heatmap (last 6 months, top 8 countries by volume)
    heatmap_countries = [c['mission__country'] for c in country_stats]
    heatmap_months = []
    for i in range(5, -1, -1):
        target_date = now - timedelta(days=i * 30)
        heatmap_months.append({'label': target_date.strftime('%b %Y'), 'year': target_date.year, 'month': target_date.month})
    heatmap_rows = []
    for country in heatmap_countries:
        row_counts = []
        for m in heatmap_months:
            row_counts.append(
                complaints.filter(mission__country=country, created_at__year=m['year'], created_at__month=m['month']).count()
            )
        heatmap_rows.append({'country': country, 'counts': row_counts})
    heatmap_max = max((c for row in heatmap_rows for c in row['counts']), default=0)

    # Stats 9: Operational wait times from real Appointment/Queue data (today)
    from appointments.models import Appointment as _Appointment
    from queue_management.models import QueueTicket as _QueueTicket
    today = timezone.now().date()
    todays_tickets = _QueueTicket.objects.filter(date=today, status=_QueueTicket.Status.COMPLETED)
    queue_wait_seconds = [t.wait_seconds for t in todays_tickets if t.wait_seconds is not None]
    avg_queue_wait_minutes = round((sum(queue_wait_seconds) / len(queue_wait_seconds)) / 60, 1) if queue_wait_seconds else 0
    appointments_today_count = _Appointment.objects.filter(slot__date=today).count()

    context = {
        'period': period,
        'avg_resolution_days': avg_resolution_days,
        'satisfaction_rate': satisfaction_rate,
        'embassy_labels_json': json.dumps(embassy_labels),
        'embassy_counts_json': json.dumps(embassy_counts),
        'country_labels_json': json.dumps(country_labels),
        'country_counts_json': json.dumps(country_counts),
        'category_labels_json': json.dumps(category_labels),
        'category_counts_json': json.dumps(category_counts),
        'monthly_labels_json': json.dumps(monthly_labels),
        'monthly_counts_json': json.dumps(monthly_counts),
        'officer_stats': officer_stats,
        'heatmap_months': heatmap_months,
        'heatmap_rows': heatmap_rows,
        'heatmap_max': heatmap_max,
        'avg_queue_wait_minutes': avg_queue_wait_minutes,
        'appointments_today_count': appointments_today_count,
    }
    cache.set(cache_key, context, 300)
    return render(request, 'missions/ministry_analytics.html', context)


@login_required
def ai_translation_api(request, pk):
    if request.user.profile.role not in [UserProfile.Role.MINISTRY_REVIEWER, UserProfile.Role.MINISTRY_ADMIN] and not request.user.is_superuser:
        return HttpResponse(json.dumps({'error': 'Unauthorized'}), content_type='application/json', status=403)
        
    complaint = get_object_or_404(Complaint, pk=pk)
    target_lang = request.GET.get('to', 'en')
    
    from missions.utils.ai_helpers import translate_text_ai
    trans_subject = translate_text_ai(complaint.subject, complaint.original_language, target_lang)
    trans_message = translate_text_ai(complaint.message, complaint.original_language, target_lang)
    
    complaint.translated_subject = trans_subject
    complaint.translated_message = trans_message
    complaint.save()
    
    return HttpResponse(json.dumps({
        'subject': trans_subject,
        'message': trans_message
    }), content_type='application/json')


def transparency_portal_view(request):
    cache_key = 'transparency_portal_data_v2'
    context = cache.get(cache_key)
    if context is not None:
        return render(request, 'missions/transparency.html', context)

    complaints = Complaint.objects.all()
    total = complaints.count()
    resolved_statuses = [Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO]
    resolved = complaints.filter(status__in=resolved_statuses).count()

    # Calculate response times
    resolved_cases = complaints.filter(status__in=resolved_statuses)
    total_days = 0
    resolved_count = resolved_cases.count()
    for c in resolved_cases:
        total_days += (c.updated_at - c.created_at).days
    avg_response_time = round(total_days / resolved_count, 1) if resolved_count else 0

    # Embassy Statistics & Rankings
    missions = Mission.objects.annotate(
        complaint_count=Count('complaints'),
        avg_rating=Avg('complaints__rating')
    ).order_by('-complaint_count')

    # One aggregate query for satisfaction averages per mission, instead of one
    # query per mission in the loop below.
    satisfaction_by_mission = {
        row['mission_id']: row['avg']
        for row in Complaint.objects.filter(satisfaction_rating__isnull=False)
        .values('mission_id').annotate(avg=Avg('satisfaction_rating'))
    }

    ranked_missions = []
    for m in missions:
        sat_avg = satisfaction_by_mission.get(m.id)
        if sat_avg is None:
            sat_avg = m.avg_rating or 3.0
        score = round(float(sat_avg) * 20, 1)
        ranked_missions.append({
            'mission': m,
            'complaints': m.complaint_count,
            'rating': round(m.avg_rating or 0, 1),
            'score': score
        })

    ranked_missions = sorted(ranked_missions, key=lambda x: x['score'], reverse=True)

    top_performing = [x for x in ranked_missions if x['score'] >= 70][:5]
    needs_improvement = [x for x in ranked_missions if x['score'] < 70][:5]

    success_stories = complaints.filter(
        status__in=resolved_statuses
    ).select_related('mission').prefetch_related('responses').order_by('-updated_at')[:5]

    context = {
        'total': total,
        'resolved': resolved,
        'avg_response_time': avg_response_time,
        'top_performing': top_performing,
        'needs_improvement': needs_improvement,
        'success_stories': list(success_stories),
    }
    cache.set(cache_key, context, 300)
    return render(request, 'missions/transparency.html', context)


def before_you_travel_view(request):
    missions = Mission.objects.all().order_by('country', 'name')
    selected_mission = None
    services = []
    support_contacts = []
    nearby_community_groups = []
    nearby_student_associations = []

    mission_id = request.GET.get('mission')
    if mission_id:
        selected_mission = Mission.objects.filter(pk=mission_id).first()
        if selected_mission:
            services = selected_mission.services.filter(is_active=True).prefetch_related('required_documents')
            support_contacts = selected_mission.support_contacts.filter(is_public=True)
            nearby_community_groups = CommunityGroup.objects.filter(
                status=CommunityStatus.VERIFIED,
                country__iexact=selected_mission.country,
                city__iexact=selected_mission.city,
            )[:6]
            nearby_student_associations = StudentAssociation.objects.filter(
                status=CommunityStatus.VERIFIED,
                country__iexact=selected_mission.country,
                city__iexact=selected_mission.city,
            )[:6]

    return render(request, 'missions/before_you_travel.html', {
        'missions': missions,
        'selected_mission': selected_mission,
        'services': services,
        'support_contacts': support_contacts,
        'nearby_community_groups': nearby_community_groups,
        'nearby_student_associations': nearby_student_associations,
    })


def directory_view(request):
    q = request.GET.get('q', '').strip()
    mission_type = request.GET.get('type', '').strip()
    
    missions = Mission.objects.all().order_by('country', 'name')
    
    if q:
        missions = missions.filter(_mission_search_filter(q))
    if mission_type in ('EM', 'CO'):
        missions = missions.filter(mission_type=mission_type)
        
    map_pins = [
        {
            'name': m.name,
            'city': m.city,
            'country': m.country,
            'lat': float(m.latitude) if m.latitude else None,
            'lng': float(m.longitude) if m.longitude else None,
        }
        for m in missions if m.latitude and m.longitude
    ]
    
    return render(request, 'missions/directory.html', {
        'missions': missions,
        'search_query': q,
        'selected_type': mission_type,
        'map_pins_json': json.dumps(map_pins),
    })


def community_directory_view(request):
    q = request.GET.get('q', '').strip()
    country = request.GET.get('country', '').strip()
    city = request.GET.get('city', '').strip()

    groups = CommunityGroup.objects.filter(status=CommunityStatus.VERIFIED).order_by('country', 'city', 'name')
    if q:
        groups = groups.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(country__icontains=q) | Q(city__icontains=q))
    if country:
        groups = groups.filter(country__iexact=country)
    if city:
        groups = groups.filter(city__icontains=city)

    countries = CommunityGroup.objects.filter(status=CommunityStatus.VERIFIED).values_list('country', flat=True).distinct().order_by('country')
    return render(request, 'missions/community_directory.html', {
        'groups': groups,
        'countries': countries,
        'search_query': q,
        'selected_country': country,
        'selected_city': city,
        'directory_type': 'community',
    })


def student_association_directory_view(request):
    q = request.GET.get('q', '').strip()
    country = request.GET.get('country', '').strip()
    city = request.GET.get('city', '').strip()

    groups = StudentAssociation.objects.filter(status=CommunityStatus.VERIFIED).order_by('country', 'city', 'university_name', 'name')
    if q:
        groups = groups.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(country__icontains=q) |
            Q(city__icontains=q) | Q(university_name__icontains=q)
        )
    if country:
        groups = groups.filter(country__iexact=country)
    if city:
        groups = groups.filter(city__icontains=city)

    countries = StudentAssociation.objects.filter(status=CommunityStatus.VERIFIED).values_list('country', flat=True).distinct().order_by('country')
    return render(request, 'missions/community_directory.html', {
        'groups': groups,
        'countries': countries,
        'search_query': q,
        'selected_country': country,
        'selected_city': city,
        'directory_type': 'student',
    })


def _community_profile_context(target):
    events = target.events.filter(is_public=True)[:10]
    announcements = target.announcements.filter(is_public=True, is_moderated=True)[:10]
    offers = target.support_offers.filter(is_active=True, is_verified=True)
    return {
        'group': target,
        'events': events,
        'announcements': announcements,
        'support_offers': offers,
        'is_student': isinstance(target, StudentAssociation),
    }


def community_group_detail_view(request, pk):
    group = get_object_or_404(CommunityGroup, pk=pk, status=CommunityStatus.VERIFIED)
    if request.method == 'POST':
        CommunityMessage.objects.create(
            community_group=group,
            sender_name=request.POST.get('sender_name', '').strip() or _('Citizen'),
            sender_email=request.POST.get('sender_email', '').strip(),
            sender_phone=request.POST.get('sender_phone', '').strip(),
            message=request.POST.get('message', '').strip(),
        )
        return redirect('community_group_detail', pk=group.pk)
    return render(request, 'missions/community_profile.html', _community_profile_context(group))


def student_association_detail_view(request, pk):
    group = get_object_or_404(StudentAssociation, pk=pk, status=CommunityStatus.VERIFIED)
    if request.method == 'POST':
        CommunityMessage.objects.create(
            student_association=group,
            sender_name=request.POST.get('sender_name', '').strip() or _('Citizen'),
            sender_email=request.POST.get('sender_email', '').strip(),
            sender_phone=request.POST.get('sender_phone', '').strip(),
            message=request.POST.get('message', '').strip(),
        )
        return redirect('student_association_detail', pk=group.pk)
    return render(request, 'missions/community_profile.html', _community_profile_context(group))


def _representative_targets(user):
    reps = CommunityRepresentative.objects.filter(user=user, is_approved=True).select_related('community_group', 'student_association')
    return [rep.community_group or rep.student_association for rep in reps if rep.community_group or rep.student_association]


@login_required
def community_admin_dashboard_view(request):
    targets = _representative_targets(request.user)
    is_ministry = request.user.profile.role in [UserProfile.Role.MINISTRY_ADMIN, UserProfile.Role.MINISTRY_REVIEWER] or request.user.is_superuser
    if not targets and not is_ministry:
        return render(request, 'missions/community_admin.html', {'denied': True})

    if is_ministry and not targets:
        targets = list(CommunityGroup.objects.all()[:10]) + list(StudentAssociation.objects.all()[:10])

    selected_type = request.GET.get('type', 'community')
    selected_id = request.GET.get('id')
    selected = targets[0] if targets else None
    for target in targets:
        if str(target.pk) == str(selected_id) and (
            (selected_type == 'student' and isinstance(target, StudentAssociation)) or
            (selected_type != 'student' and isinstance(target, CommunityGroup))
        ):
            selected = target
            break

    if request.method == 'POST' and selected:
        action = request.POST.get('action')
        is_student = isinstance(selected, StudentAssociation)
        if action == 'profile':
            for field in ['description', 'contact_email', 'phone_whatsapp', 'facebook_url', 'instagram_url', 'x_url', 'website_url', 'office_location']:
                setattr(selected, field, request.POST.get(field, '').strip())
            selected.emergency_support_available = request.POST.get('emergency_support_available') == 'on'
            selected.save()
        elif action == 'announcement':
            CommunityAnnouncement.objects.create(
                student_association=selected if is_student else None,
                community_group=selected if not is_student else None,
                title=request.POST.get('title', '').strip(),
                announcement_type=request.POST.get('announcement_type', CommunityAnnouncement.AnnouncementType.GENERAL),
                body=request.POST.get('body', '').strip(),
                is_public=False,
                is_moderated=False,
                created_by=request.user,
            )
        elif action == 'event':
            starts_at = request.POST.get('starts_at')
            if starts_at:
                CommunityEvent.objects.create(
                    student_association=selected if is_student else None,
                    community_group=selected if not is_student else None,
                    title=request.POST.get('title', '').strip(),
                    event_type=request.POST.get('event_type', CommunityEvent.EventType.EVENT),
                    description=request.POST.get('description', '').strip(),
                    location=request.POST.get('location', '').strip(),
                    starts_at=starts_at,
                    is_public=False,
                    created_by=request.user,
                )
        elif action == 'delete_announcement':
            selected.announcements.filter(pk=request.POST.get('announcement_id'), created_by=request.user).delete()
        return redirect(f"{request.path}?type={'student' if is_student else 'community'}&id={selected.pk}")

    announcements = selected.announcements.all()[:20] if selected else []
    events = selected.events.all()[:20] if selected else []
    messages = selected.messages.all()[:20] if selected else []
    return render(request, 'missions/community_admin.html', {
        'denied': False,
        'targets': targets,
        'selected': selected,
        'selected_is_student': isinstance(selected, StudentAssociation),
        'announcements': announcements,
        'events': events,
        'messages': messages,
    })


@login_required
def invite_embassy_user_view(request):
    if request.user.profile.role != UserProfile.Role.MINISTRY_ADMIN and not request.user.is_superuser:
        return redirect('home')

    missions = Mission.objects.all().order_by('name')
    error = None
    success = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        mission_id = request.POST.get('mission')
        role = request.POST.get('role', 'EMBASSY_OFFICER')

        if not email or not mission_id:
            error = _("Email and Mission are required.")
        else:
            mission = get_object_or_404(Mission, id=mission_id)
            import secrets
            token = secrets.token_urlsafe(32)
            
            # Deactivate any old invitation for this email
            EmbassyInvitation.objects.filter(email=email).delete()
            
            invitation = EmbassyInvitation.objects.create(
                email=email,
                mission=mission,
                role=role,
                token=token
            )
            log_audit_action(
                request.user, None, 'Invited Embassy User',
                f'Invited {email} as {role} for {mission.name}.', request=request,
            )

            # Log simulated invitation email
            activation_url = request.build_absolute_uri(f'/embassy/activate/{token}/')
            
            # Save a notification log to simulate sending the email
            NotificationLog.objects.create(
                complaint=Complaint.objects.first(),  # Dummy or system-linked complaint
                recipient=email,
                notification_type=NotificationLog.Type.EMAIL,
                subject="Embassy Portal Account Invitation",
                message=f"You have been invited to join the Somali Embassy Portal as an {invitation.get_role_display()} for {mission.name}.\n\nActivate your account securely here: {activation_url}"
            )
            success = _("Invitation email sent successfully (simulated link printed to notification logs).")

    pending_invitations = EmbassyInvitation.objects.filter(is_used=False).order_by('-created_at')

    return render(request, 'missions/invite_embassy.html', {
        'missions': missions,
        'error': error,
        'success': success,
        'pending_invitations': pending_invitations
    })


def activate_embassy_account_view(request, token):
    invitation = get_object_or_404(EmbassyInvitation, token=token, is_used=False)
    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        from django.contrib.auth.models import User
        if User.objects.filter(username__iexact=username).exists():
            error = _("A user with that username already exists.")
        elif password != confirm_password:
            error = _("Passwords do not match.")
        elif len(password) < 6:
            error = _("Password must be at least 6 characters.")
        else:
            # Create user
            user = User.objects.create_user(username=username, password=password, email=invitation.email)
            profile = user.profile
            profile.role = invitation.role
            profile.mission = invitation.mission
            profile.full_name = full_name
            profile.email_verified = True
            profile.save()
            log_audit_action(
                user, None, 'Role Assigned',
                f'Account activated with role {invitation.role} for {invitation.mission.name}.', request=request,
            )

            # Mark invitation as used
            invitation.is_used = True
            invitation.save()

            # Log user in
            login(request, user)
            return redirect('dashboard_router')

    return render(request, 'missions/embassy_activation.html', {
        'invitation': invitation,
        'error': error
    })


@login_required
def embassy_dashboard_view(request):
    user_profile = request.user.profile
    if user_profile.role not in [UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER] and not request.user.is_superuser:
        return redirect('home')

    mission = user_profile.mission
    if not mission:
        return render(request, 'missions/embassy_dashboard.html', {'denied': True})

    complaints = Complaint.objects.filter(mission=mission).select_related('assigned_officer').order_by('-created_at')

    # Performance Monitoring Metrics (Requirement 30)
    total_complaints = complaints.count()
    open_count = complaints.filter(status__in=[
        Complaint.Status.SUBMITTED, Complaint.Status.ASSIGNED, Complaint.Status.UNDER_REVIEW,
        Complaint.Status.INVESTIGATION, Complaint.Status.AWAITING_RESPONSE, Complaint.Status.NEW, Complaint.Status.PRO
    ]).count()
    resolved_count = complaints.filter(status__in=[Complaint.Status.RESOLVED, Complaint.Status.RES]).count()
    resolution_rate = round((resolved_count / total_complaints * 100), 1) if total_complaints else 0.0

    # Average Response Time (hours/days)
    resolved_cases = complaints.filter(status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO])
    total_days = 0
    resolved_total = resolved_cases.count()
    for c in resolved_cases:
        total_days += (c.updated_at - c.created_at).days
    avg_response_time = round(total_days / resolved_total, 1) if resolved_total else 0.0

    # User satisfaction average rating (Requirement 30)
    satisfaction_avg = complaints.filter(satisfaction_rating__isnull=False).aggregate(avg=Avg('satisfaction_rating'))['avg']
    satisfaction_rate = round(float(satisfaction_avg), 1) if satisfaction_avg else 0.0

    # Filter based on role
    if user_profile.role == UserProfile.Role.EMBASSY_OFFICER:
        assigned_complaints = complaints.filter(assigned_officer=request.user)
    else:  # Manager
        assigned_complaints = complaints

    # Active/Pending Response deadlines
    deadline_threshold = timezone.now() - timedelta(days=14)
    deadline_cases = complaints.filter(
        created_at__lt=deadline_threshold,
        status__in=[Complaint.Status.SUBMITTED, Complaint.Status.ASSIGNED, Complaint.Status.NEW]
    )

    # Embassy Staff list for case allocation (Requirement 27 Embassy Manager Features)
    from django.contrib.auth.models import User
    embassy_staff = User.objects.filter(profile__mission=mission, profile__role=UserProfile.Role.EMBASSY_OFFICER)

    # Allocation POST handler
    if request.method == 'POST' and user_profile.role == UserProfile.Role.EMBASSY_MANAGER:
        if 'assign_case' in request.POST:
            complaint_id = request.POST.get('complaint_id')
            officer_id = request.POST.get('officer_id')
            complaint = get_object_or_404(Complaint, id=complaint_id, mission=mission)
            
            if officer_id:
                officer = get_object_or_404(User, id=officer_id)
                complaint.assigned_officer = officer
                complaint.status = Complaint.Status.ASSIGNED
                complaint.save()
                log_audit_action(request.user, complaint, "Assigned Case", f"Assigned case to officer: {officer.username}", request=request)
            else:
                complaint.assigned_officer = None
                complaint.save()
                log_audit_action(request.user, complaint, "Unassigned Case", "Removed assignment from case", request=request)
            return redirect('dashboard_router')

    return render(request, 'missions/embassy_dashboard.html', {
        'denied': False,
        'mission': mission,
        'role': user_profile.role,
        'complaints': assigned_complaints,
        'total_complaints': total_complaints,
        'open_count': open_count,
        'resolution_rate': resolution_rate,
        'avg_response_time': avg_response_time,
        'satisfaction_rate': satisfaction_rate,
        'deadline_cases': deadline_cases,
        'embassy_staff': embassy_staff
    })


@login_required
def embassy_case_detail_view(request, pk):
    user_profile = request.user.profile
    # Authorization checks
    is_staff = user_profile.role in [UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER]
    is_ministry = user_profile.role in [UserProfile.Role.MINISTRY_REVIEWER, UserProfile.Role.MINISTRY_ADMIN]
    
    if not is_staff and not is_ministry and not request.user.is_superuser:
        return redirect('home')

    complaint = get_object_or_404(Complaint, pk=pk)
    
    # Embassy staff can only view complaints from their own mission
    if is_staff and complaint.mission != user_profile.mission and not request.user.is_superuser:
        return redirect('dashboard_router')

    # Handle status changes, internal notes, and escalation (Requirement 28 Case Management)
    if request.method == 'POST':
        # 1. Update status
        if 'update_status' in request.POST:
            new_status = request.POST.get('status')
            if new_status in Complaint.Status.values:
                old_status = complaint.status
                complaint.status = new_status
                complaint.save()
                _record_status_change(request.user, complaint, old_status, new_status, _('Case detail status update.'))
                log_audit_action(request.user, complaint, "Updated Status", f"Status changed from {old_status} to {new_status}", request=request)

        # 2. Update internal notes
        elif 'save_notes' in request.POST:
            notes = request.POST.get('internal_notes', '').strip()
            complaint.internal_notes = notes
            complaint.save()
            log_audit_action(request.user, complaint, "Updated Internal Notes", "Modified internal Notes details", request=request)

        # 3. Request more information
        elif 'request_info' in request.POST:
            old_status = complaint.status
            complaint.status = Complaint.Status.AWAITING_RESPONSE
            complaint.save()
            _record_status_change(request.user, complaint, old_status, Complaint.Status.AWAITING_RESPONSE, _('Requested more information from citizen.'))
            log_audit_action(request.user, complaint, "Information Request", "Sent information clarification request to citizen", request=request)
            
            # Notify citizen
            if complaint.email:
                NotificationLog.objects.create(
                    complaint=complaint,
                    recipient=complaint.email,
                    notification_type=NotificationLog.Type.EMAIL,
                    subject="Additional Information Requested - Case " + complaint.tracking_code,
                    message=f"Dear Citizen,\n\nThe Embassy has requested more details regarding your case ({complaint.tracking_code}). Please visit the tracking portal to respond."
                )

        # 4. Escalate to Ministry
        elif 'escalate' in request.POST:
            complaint.priority = Complaint.Priority.CRITICAL
            # Escalate status if needed
            complaint.save()
            log_audit_action(request.user, complaint, "Escalated to Ministry", "Escalated case status to ministry headquarters oversight", request=request)
            EscalationLog.objects.create(
                complaint=complaint,
                target_role=UserProfile.Role.MINISTRY_REVIEWER,
                channel=EscalationLog.Channel.IN_APP,
                message=f"Manual escalation requested by {request.user.username}.",
            )
            
            # Create notification log for Admin
            NotificationLog.objects.create(
                complaint=complaint,
                recipient="ministry-admin@somali-gov.so",
                notification_type=NotificationLog.Type.EMAIL,
                subject=f"CRITICAL ESCALATION: Case {complaint.tracking_code}",
                message=f"Case {complaint.tracking_code} regarding {complaint.mission.name} has been escalated to HQ for immediate review."
            )

        return redirect('embassy_case_detail', pk=complaint.pk)

    # Fetch audit logs and secure messaging history (Requirement 28 & 29)
    audit_logs = complaint.audit_logs.all().order_by('-timestamp')
    messages = complaint.secure_messages.all().order_by('created_at')

    # Identify sender types for messaging board styling
    for msg in messages:
        try:
            sender_role = msg.sender.profile.role
        except Exception:
            sender_role = 'CITIZEN'
        
        if sender_role == UserProfile.Role.CITIZEN:
            msg.styling = 'bg-slate-100 text-textPrimary'
        elif sender_role in [UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER]:
            msg.styling = 'bg-blue-100 text-textPrimary'
        else:  # Ministry
            msg.styling = 'bg-purple-100 text-textPrimary'

    return render(request, 'missions/embassy_case_detail.html', {
        'complaint': complaint,
        'audit_logs': audit_logs,
        'messages': messages,
        'is_staff': is_staff,
        'is_ministry': is_ministry
    })


@login_required
def post_secure_message_view(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)
    
    user_profile = request.user.profile
    is_staff = user_profile.role in [UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER]
    is_ministry = user_profile.role in [UserProfile.Role.MINISTRY_REVIEWER, UserProfile.Role.MINISTRY_ADMIN]
    is_owner = (complaint.citizen_user == request.user)
    
    # Allow if tracking code matches session and user is logged in
    has_session_access = (request.session.get('tracked_code') == complaint.tracking_code) or (request.session.get('last_tracking_code') == complaint.tracking_code)
    
    if not is_staff and not is_ministry and not is_owner and not (has_session_access and user_profile.role == UserProfile.Role.CITIZEN) and not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        text = request.POST.get('message_text', '').strip()
        attachment_file = request.FILES.get('message_attachment')
        attachment_rejected = False

        if attachment_file and (
            attachment_file.size > MAX_EVIDENCE_SIZE
            or attachment_file.content_type not in ALLOWED_EVIDENCE_TYPES
        ):
            messages.error(request, _('Attachment rejected: file must be under 10MB and a photo, PDF, audio, or video file.'))
            attachment_file = None
            attachment_rejected = True

        if text or attachment_file:
            # Determine sender type
            if is_ministry:
                sender_type = SecureMessage.SenderType.MINISTRY
            elif is_staff:
                sender_type = SecureMessage.SenderType.EMBASSY
            else:
                sender_type = SecureMessage.SenderType.CITIZEN

            SecureMessage.objects.create(
                complaint=complaint,
                sender=request.user,
                sender_type=sender_type,
                message=text,
                attachment=attachment_file
            )

            # Audit action
            log_audit_action(request.user, complaint, "Sent Secure Message", f"Sent secure message via portal. Sender type: {sender_type}", request=request)

            # Notify recipient
            notify_email = ""
            if sender_type == SecureMessage.SenderType.CITIZEN:
                notify_email = complaint.mission.email
            else:
                notify_email = complaint.email
                
            if notify_email:
                NotificationLog.objects.create(
                    complaint=complaint,
                    recipient=notify_email,
                    notification_type=NotificationLog.Type.EMAIL,
                    subject="New Secure Message - Case " + complaint.tracking_code,
                    message=f"You have received a new secure portal message on case {complaint.tracking_code}.\n\nMessage body: {text[:50]}..."
                )
            messages.success(request, _('Message sent.'))
        elif not attachment_rejected:
            messages.error(request, _('Please enter a message or attach a file before sending.'))

    # Redirect to appropriate dashboard / tracking view
    referer = request.META.get('HTTP_REFERER', '')
    if 'track' in referer:
        return redirect(f'/track/?tracking_code={complaint.tracking_code}')
    return redirect('embassy_case_detail', pk=complaint.pk)


@login_required
def dashboard_router_view(request):
    return redirect(redirect_after_login(request.user))


@login_required
def embassy_officer_dashboard_view(request):
    if request.user.profile.role != UserProfile.Role.EMBASSY_OFFICER and not request.user.is_superuser:
        return redirect('home')
    return embassy_dashboard_view(request)


@login_required
def embassy_manager_dashboard_view(request):
    if request.user.profile.role != UserProfile.Role.EMBASSY_MANAGER and not request.user.is_superuser:
        return redirect('home')
    return embassy_dashboard_view(request)


@login_required
def ministry_reviewer_dashboard_view(request):
    if request.user.profile.role != UserProfile.Role.MINISTRY_REVIEWER and not request.user.is_superuser:
        return redirect('home')
    return ministry_operations_view(request)


@login_required
def ministry_admin_dashboard_view(request):
    if request.user.profile.role != UserProfile.Role.MINISTRY_ADMIN and not request.user.is_superuser:
        return redirect('home')
    return ministry_operations_view(request)




