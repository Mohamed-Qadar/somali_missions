from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from missions.models import Mission, MissionService
from missions.utils.audit import log_audit_action
from missions.utils.permissions import missions_for_user, user_can_manage_mission
from notifications.channels import notify

from .forms import ConsularApplicationForm, StaffApplicationActionForm
from .models import (
    ConsularApplication, ConsularApplicationDocument,
    ConsularApplicationStatusHistory,
)
from .services import SERVICE_CATEGORIES, types_for_category

# Reuse the exact upload validation rules the complaints module already applies.
ALLOWED_DOCUMENT_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'application/pdf',
}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_status(application, old_status, new_status, user=None, note=''):
    ConsularApplicationStatusHistory.objects.create(
        application=application, old_status=old_status or '', new_status=new_status,
        changed_by=user if (user and user.is_authenticated) else None, note=note,
    )


def _save_documents(application, uploaded_files, user=None):
    saved = []
    for f in uploaded_files:
        if f.size > MAX_DOCUMENT_SIZE or f.content_type not in ALLOWED_DOCUMENT_TYPES:
            continue
        saved.append(ConsularApplicationDocument.objects.create(
            application=application, file=f, file_name=f.name,
            file_size=f.size, file_type=f.content_type,
            uploaded_by=user if (user and user.is_authenticated) else None,
        ))
    return saved


def _owns(user, application):
    return application.citizen_user_id == user.id


# ---------------------------------------------------------------------------
# Citizen-facing views
# ---------------------------------------------------------------------------

def consular_services_view(request):
    """Public landing page: category cards + entry point to apply/track."""
    return render(request, 'consular/services.html', {
        'categories': SERVICE_CATEGORIES,
    })


@login_required
def apply_view(request):
    """Guided application: select mission -> select service -> details + docs.

    Mission/service are driven by GET params (same progressive pattern as the
    existing appointment booking flow) so the service's document checklist can
    be shown before the citizen commits."""
    missions = Mission.objects.all().order_by('country', 'name')
    category = request.GET.get('category', '')
    selected_mission_id = request.POST.get('mission') or request.GET.get('mission', '')
    selected_service_id = request.POST.get('service') or request.GET.get('service', '')

    services = MissionService.objects.none()
    if selected_mission_id:
        services = MissionService.objects.filter(
            mission_id=selected_mission_id, is_active=True,
        ).order_by('name')
        type_filter = types_for_category(category)
        if type_filter:
            services = services.filter(service_type__in=type_filter)

    selected_service = None
    if selected_service_id:
        selected_service = (
            MissionService.objects.filter(pk=selected_service_id, is_active=True)
            .select_related('mission').prefetch_related('required_documents').first()
        )

    # Prefill applicant details from the citizen's profile where available.
    profile = getattr(request.user, 'profile', None)
    initial = {
        'full_name': (profile.full_name if profile else '') or request.user.get_full_name(),
        'email': request.user.email,
        'phone': getattr(profile, 'phone_number', '') or '',
        'national_id': getattr(profile, 'national_id', '') or '',
    }

    form = ConsularApplicationForm(initial=initial)

    if request.method == 'POST' and request.POST.get('submit_application'):
        form = ConsularApplicationForm(request.POST)
        if not selected_service:
            messages.error(request, _('Please choose a mission and a service before submitting.'))
        elif form.is_valid():
            application = form.save(commit=False)
            application.mission = selected_service.mission
            application.service = selected_service
            application.citizen_user = request.user
            application.status = ConsularApplication.Status.SUBMITTED
            application.save()

            _save_documents(application, request.FILES.getlist('documents'), user=request.user)
            _record_status(
                application, '', application.status, user=request.user,
                note=_('Citizen submitted application.'),
            )
            log_audit_action(
                request.user, None, 'Consular application submitted',
                f'{application.reference_code}: {selected_service.name} @ {selected_service.mission.name}',
                request=request,
            )
            notify(
                request.user,
                title=_('Application %(ref)s received') % {'ref': application.reference_code},
                body=_('Your %(service)s application at %(mission)s has been received.') % {
                    'service': selected_service.name, 'mission': selected_service.mission.name,
                },
                link_url=f'/consular/application/{application.reference_code}/',
            )
            messages.success(request, _('Your application has been submitted. Reference: %(ref)s') % {
                'ref': application.reference_code,
            })
            return redirect('consular_application_detail', reference_code=application.reference_code)

    return render(request, 'consular/apply.html', {
        'missions': missions,
        'services': services,
        'selected_mission_id': str(selected_mission_id),
        'selected_service_id': str(selected_service_id),
        'selected_service': selected_service,
        'category': category,
        'form': form,
    })


@login_required
def my_applications_view(request):
    applications = (
        ConsularApplication.objects.filter(citizen_user=request.user)
        .select_related('mission', 'service').order_by('-created_at')
    )
    open_count = sum(1 for a in applications if a.is_open)
    return render(request, 'consular/my_applications.html', {
        'applications': applications,
        'total': len(applications),
        'open_count': open_count,
    })


@login_required
def application_detail_view(request, reference_code):
    application = get_object_or_404(
        ConsularApplication.objects.select_related('mission', 'service', 'appointment'),
        reference_code=reference_code,
    )
    if not _owns(request.user, application):
        return redirect('my_consular_applications')

    if request.method == 'POST' and request.POST.get('upload_documents'):
        if application.can_upload_more:
            saved = _save_documents(
                application, request.FILES.getlist('documents'), user=request.user,
            )
            if saved:
                # A citizen answering a documents request moves it back into the
                # review queue automatically.
                if application.status == ConsularApplication.Status.DOCS_REQUIRED:
                    old = application.status
                    application.status = ConsularApplication.Status.UNDER_REVIEW
                    application.save(update_fields=['status', 'updated_at'])
                    _record_status(
                        application, old, application.status, user=request.user,
                        note=_('Citizen uploaded requested documents.'),
                    )
                messages.success(request, _('%(n)s document(s) uploaded.') % {'n': len(saved)})
            else:
                messages.error(request, _('No valid documents were uploaded (PDF or image, max 10 MB).'))
        else:
            messages.error(request, _('Documents can no longer be added to this application.'))
        return redirect('consular_application_detail', reference_code=reference_code)

    if request.method == 'POST' and request.POST.get('link_appointment'):
        # Connect an appointment the citizen booked through the existing
        # booking flow to this application, by its reference (QR) code.
        from appointments.models import Appointment
        token = (request.POST.get('qr_token') or '').strip().upper()
        appointment = Appointment.objects.filter(
            qr_token=token, mission=application.mission,
        ).first()
        if not appointment:
            messages.error(request, _('No appointment with that reference was found for this mission.'))
        elif appointment.citizen_user_id and appointment.citizen_user_id != request.user.id:
            messages.error(request, _('That appointment belongs to a different account.'))
        else:
            application.appointment = appointment
            application.save(update_fields=['appointment', 'updated_at'])
            _record_status(
                application, application.status, application.status, user=request.user,
                note=_('Citizen linked appointment %(code)s.') % {'code': appointment.qr_token},
            )
            messages.success(request, _('Appointment %(code)s linked to your application.') % {
                'code': appointment.qr_token,
            })
        return redirect('consular_application_detail', reference_code=reference_code)

    if request.method == 'POST' and request.POST.get('cancel_application'):
        if application.is_open:
            old = application.status
            application.status = ConsularApplication.Status.CANCELLED
            application.save(update_fields=['status', 'updated_at'])
            _record_status(application, old, application.status, user=request.user,
                           note=_('Citizen cancelled application.'))
            messages.success(request, _('Your application has been cancelled.'))
        return redirect('consular_application_detail', reference_code=reference_code)

    required_documents = application.service.required_documents.all()
    return render(request, 'consular/application_detail.html', {
        'application': application,
        'documents': application.documents.all(),
        'history': application.status_history.all(),
        'required_documents': required_documents,
        'Status': ConsularApplication.Status,
    })


# ---------------------------------------------------------------------------
# Mission-staff views
# ---------------------------------------------------------------------------

@login_required
def staff_applications_view(request):
    missions = missions_for_user(request.user)
    applications = (
        ConsularApplication.objects.filter(mission__in=missions)
        .select_related('mission', 'service', 'citizen_user')
    )

    status = request.GET.get('status', '')
    mission_id = request.GET.get('mission', '')
    if status:
        applications = applications.filter(status=status)
    if mission_id:
        applications = applications.filter(mission_id=mission_id)

    open_total = ConsularApplication.objects.filter(
        mission__in=missions, status__in=ConsularApplication.OPEN_STATUSES,
    ).count()

    return render(request, 'consular/staff_applications.html', {
        'applications': applications.order_by('-created_at'),
        'missions': missions,
        'status_choices': ConsularApplication.Status.choices,
        'open_total': open_total,
        'selected_status': status,
        'selected_mission': mission_id,
        'denied': not missions.exists(),
    })


# Maps a form action to (new status, default citizen-facing note).
_STAFF_ACTIONS = {
    'under_review': (ConsularApplication.Status.UNDER_REVIEW, _('Your application is now under review.')),
    'request_documents': (ConsularApplication.Status.DOCS_REQUIRED, _('Additional documents are required.')),
    'approve': (ConsularApplication.Status.APPROVED, _('Your application is approved and ready.')),
    'require_appointment': (ConsularApplication.Status.APPOINTMENT_REQUIRED, _('Please book an appointment to attend the mission.')),
    'complete': (ConsularApplication.Status.COMPLETED, _('Your consular service has been completed.')),
    'reject': (ConsularApplication.Status.REJECTED, _('Your application has been rejected.')),
}


@login_required
def staff_application_detail_view(request, pk):
    application = get_object_or_404(
        ConsularApplication.objects.select_related('mission', 'service', 'citizen_user', 'appointment'),
        pk=pk,
    )
    if not user_can_manage_mission(request.user, application.mission):
        return redirect('consular_staff_applications')

    form = StaffApplicationActionForm()
    if request.method == 'POST':
        form = StaffApplicationActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            citizen_message = form.cleaned_data['citizen_message'].strip()
            staff_notes = form.cleaned_data['staff_notes'].strip()
            new_status, default_message = _STAFF_ACTIONS[action]
            old_status = application.status

            application.status = new_status
            if citizen_message:
                application.citizen_message = citizen_message
            if staff_notes:
                # Append rather than overwrite so the internal trail is kept.
                stamp = f'[{request.user.username}] {staff_notes}'
                application.staff_notes = (application.staff_notes + '\n' + stamp).strip()
            application.save()

            shown_message = citizen_message or str(default_message)
            _record_status(application, old_status, new_status, user=request.user, note=shown_message)
            log_audit_action(
                request.user, None, f'Consular application {action}',
                f'{application.reference_code}: {old_status} -> {new_status}',
                request=request,
            )
            if application.citizen_user:
                notify(
                    application.citizen_user,
                    title=_('Application %(ref)s: %(status)s') % {
                        'ref': application.reference_code, 'status': application.get_status_display(),
                    },
                    body=shown_message,
                    link_url=f'/consular/application/{application.reference_code}/',
                    channels=['email'],
                )
            messages.success(request, _('Application updated to %(status)s.') % {
                'status': application.get_status_display(),
            })
            return redirect('consular_staff_application_detail', pk=application.pk)

    return render(request, 'consular/staff_application_detail.html', {
        'application': application,
        'documents': application.documents.all(),
        'history': application.status_history.all(),
        'required_documents': application.service.required_documents.all(),
        'form': form,
    })
