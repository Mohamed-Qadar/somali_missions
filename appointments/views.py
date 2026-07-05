import io
from datetime import timedelta

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from missions.models import Mission, MissionService
from missions.utils.audit import log_audit_action
from missions.utils.permissions import missions_for_user, user_can_manage_mission
from notifications.channels import notify

from .forms import AppointmentActionForm, AppointmentSlotForm, BookAppointmentForm
from .models import Appointment, AppointmentSlot, AppointmentStatusHistory


def _record_appointment_status(appointment, old_status, new_status, user=None, note=''):
    AppointmentStatusHistory.objects.create(
        appointment=appointment, old_status=old_status, new_status=new_status,
        changed_by=user, note=note,
    )


def _send_confirmation_email(appointment):
    if not appointment.email:
        return
    confirm_url = f'/appointments/confirmation/{appointment.qr_token}/'
    send_mail(
        subject=_('Your appointment request - %(mission)s') % {'mission': appointment.mission.name},
        message=_(
            'Dear %(name)s,\n\n'
            'Your appointment request for %(service)s at %(mission)s has been received.\n'
            'Status: %(status)s\n'
            'Reference code: %(code)s\n\n'
            'View your confirmation and QR code at: %(url)s'
        ) % {
            'name': appointment.full_name,
            'service': appointment.service.name,
            'mission': appointment.mission.name,
            'status': appointment.get_status_display(),
            'code': appointment.qr_token,
            'url': confirm_url,
        },
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[appointment.email],
        fail_silently=True,
    )
    appointment.confirmation_sent = True
    appointment.save(update_fields=['confirmation_sent'])


def book_appointment_view(request):
    missions = Mission.objects.all().order_by('country', 'name')
    selected_mission_id = request.GET.get('mission', '')
    selected_service_id = request.GET.get('service', '')
    services = []
    slots = []

    if selected_mission_id:
        services = MissionService.objects.filter(mission_id=selected_mission_id, is_active=True)
    if selected_mission_id and selected_service_id:
        slots = AppointmentSlot.objects.filter(
            mission_id=selected_mission_id,
            service_id=selected_service_id,
            is_active=True,
            date__gte=timezone.now().date(),
        ).order_by('date', 'start_time')

    if request.method == 'POST':
        form = BookAppointmentForm(request.POST)
        slot_id = request.POST.get('slot')
        if selected_mission_id:
            services = MissionService.objects.filter(mission_id=selected_mission_id, is_active=True)
        if selected_mission_id and selected_service_id:
            slots = AppointmentSlot.objects.filter(
                mission_id=selected_mission_id, service_id=selected_service_id,
                is_active=True, date__gte=timezone.now().date(),
            ).order_by('date', 'start_time')

        if form.is_valid() and slot_id:
            with transaction.atomic():
                slot = AppointmentSlot.objects.select_for_update().filter(pk=slot_id).first()
                if not slot:
                    form.add_error(None, _('Selected time slot no longer exists.'))
                else:
                    status = Appointment.Status.WAITLISTED if slot.is_full else Appointment.Status.PENDING
                    appointment = Appointment.objects.create(
                        mission=slot.mission,
                        service=slot.service,
                        slot=slot,
                        citizen_user=request.user if request.user.is_authenticated else None,
                        full_name=form.cleaned_data['full_name'],
                        email=form.cleaned_data['email'],
                        phone=form.cleaned_data['phone'],
                        status=status,
                    )
                    _record_appointment_status(appointment, '', status, note=_('Citizen booked appointment.'))
                    _send_confirmation_email(appointment)
                    return redirect('appointment_confirmation', qr_token=appointment.qr_token)
        elif not slot_id:
            form.add_error(None, _('Please select an available time slot.'))
    else:
        form = BookAppointmentForm()

    # Show the service's required documents before the citizen books, so
    # nobody travels to an appointment without the right paperwork.
    selected_service = None
    if selected_service_id:
        selected_service = (
            MissionService.objects.filter(pk=selected_service_id, is_active=True)
            .prefetch_related('required_documents')
            .first()
        )

    return render(request, 'appointments/book_appointment.html', {
        'missions': missions,
        'services': services,
        'slots': slots,
        'selected_mission_id': selected_mission_id,
        'selected_service_id': selected_service_id,
        'selected_service': selected_service,
        'form': form,
    })


def appointment_confirmation_view(request, qr_token):
    appointment = get_object_or_404(Appointment, qr_token=qr_token)
    return render(request, 'appointments/confirmation.html', {'appointment': appointment})


def appointment_qr_image_view(request, qr_token):
    appointment = get_object_or_404(Appointment, qr_token=qr_token)
    img = qrcode.make(f'APPOINTMENT:{appointment.qr_token}')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')


def _staff_missions(request):
    return missions_for_user(request.user)


@login_required
def staff_appointments_view(request):
    view_mode = request.GET.get('view', 'daily')
    day = request.GET.get('date', '')
    missions = _staff_missions(request)
    appointments = Appointment.objects.filter(mission__in=missions).select_related('mission', 'service', 'slot')

    today = timezone.now().date()
    if view_mode == 'weekly':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        appointments = appointments.filter(slot__date__range=[start, end])
    elif view_mode == 'monthly':
        appointments = appointments.filter(slot__date__year=today.year, slot__date__month=today.month)
    else:
        target_day = today
        if day:
            try:
                from datetime import date
                target_day = date.fromisoformat(day)
            except ValueError:
                pass
        appointments = appointments.filter(slot__date=target_day)

    return render(request, 'appointments/staff_appointments.html', {
        'appointments': appointments.order_by('slot__date', 'slot__start_time'),
        'view_mode': view_mode,
        'missions': missions,
    })


@login_required
def appointment_action_view(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if not user_can_manage_mission(request.user, appointment.mission):
        return redirect('staff_appointments')

    if request.method == 'POST':
        form = AppointmentActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            note = form.cleaned_data['note']
            old_status = appointment.status
            if action == 'approve':
                appointment.status = Appointment.Status.CONFIRMED
            elif action == 'reject':
                appointment.status = Appointment.Status.REJECTED
            elif action == 'cancel':
                appointment.status = Appointment.Status.CANCELLED
            elif action == 'complete':
                appointment.status = Appointment.Status.COMPLETED
            elif action == 'no_show':
                appointment.status = Appointment.Status.NO_SHOW
            elif action == 'reschedule':
                new_slot = form.cleaned_data.get('new_slot')
                if new_slot:
                    appointment.slot = new_slot
                    appointment.mission = new_slot.mission
                    appointment.service = new_slot.service
                appointment.status = Appointment.Status.RESCHEDULED
            if note:
                appointment.staff_notes = note
            appointment.save()
            _record_appointment_status(appointment, old_status, appointment.status, user=request.user, note=note)
            log_audit_action(
                request.user, None, f'Appointment {action}',
                f'Appointment {appointment.qr_token} ({appointment.mission.name}): {old_status} -> {appointment.status}',
                request=request,
            )
            if appointment.citizen_user:
                notify(
                    appointment.citizen_user,
                    title=_('Appointment %(code)s: %(status)s') % {
                        'code': appointment.qr_token, 'status': appointment.get_status_display(),
                    },
                    body=_('Your appointment at %(mission)s for %(service)s is now %(status)s.') % {
                        'mission': appointment.mission.name, 'service': appointment.service.name,
                        'status': appointment.get_status_display(),
                    },
                    link_url=f'/appointments/confirmation/{appointment.qr_token}/',
                    channels=['email'],
                )
            messages.success(request, _('Appointment %(code)s updated to %(status)s.') % {
                'code': appointment.qr_token, 'status': appointment.get_status_display(),
            })
    return redirect('staff_appointments')


@login_required
def manage_slots_view(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    if not user_can_manage_mission(request.user, mission):
        return redirect('staff_appointments')

    if request.method == 'POST':
        form = AppointmentSlotForm(request.POST, mission=mission)
        if form.is_valid():
            slot = form.save(commit=False)
            slot.mission = mission
            slot.save()
            messages.success(request, _('Slot created for %(date)s.') % {'date': slot.date})
            return redirect('manage_appointment_slots', mission_pk=mission.pk)
    else:
        form = AppointmentSlotForm(mission=mission)

    slots = mission.appointment_slots.filter(date__gte=timezone.now().date()).order_by('date', 'start_time')
    return render(request, 'appointments/manage_slots.html', {
        'mission': mission, 'form': form, 'slots': slots,
    })


@login_required
def appointment_waitlist_view(request):
    missions = _staff_missions(request)
    waitlisted = Appointment.objects.filter(
        mission__in=missions, status=Appointment.Status.WAITLISTED
    ).select_related('mission', 'service', 'slot').order_by('created_at')
    return render(request, 'appointments/waitlist.html', {'waitlisted': waitlisted})


@login_required
def appointment_stats_view(request):
    missions = _staff_missions(request)
    qs = Appointment.objects.filter(mission__in=missions)
    total = qs.count()
    by_status = qs.values('status').annotate(count=Count('id')).order_by('-count')
    by_service = qs.values('service__name').annotate(count=Count('id')).order_by('-count')[:10]
    no_show_count = qs.filter(status=Appointment.Status.NO_SHOW).count()
    completed_count = qs.filter(status=Appointment.Status.COMPLETED).count()
    no_show_rate = round((no_show_count / total) * 100, 1) if total else 0

    return render(request, 'appointments/stats.html', {
        'total': total,
        'by_status': by_status,
        'by_service': by_service,
        'no_show_rate': no_show_rate,
        'completed_count': completed_count,
    })
