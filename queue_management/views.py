from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from missions.models import Mission, MissionService
from missions.utils.audit import log_audit_action
from missions.utils.permissions import missions_for_user, user_can_manage_mission

from .models import QueueTicket


def join_queue_view(request):
    missions = Mission.objects.all().order_by('country', 'name')
    selected_mission_id = request.GET.get('mission', '')
    services = MissionService.objects.filter(mission_id=selected_mission_id, is_active=True) if selected_mission_id else []

    if request.method == 'POST':
        mission = get_object_or_404(Mission, pk=request.POST.get('mission'))
        service_id = request.POST.get('service') or None
        full_name = request.POST.get('full_name', '').strip()
        today = timezone.now().date()

        with transaction.atomic():
            existing = QueueTicket.objects.select_for_update().filter(mission=mission, date=today)
            next_number = (existing.aggregate(m=Max('ticket_number'))['m'] or 0) + 1
            ticket = QueueTicket.objects.create(
                mission=mission,
                service_id=service_id,
                date=today,
                ticket_number=next_number,
                full_name=full_name,
            )
        return redirect('queue_ticket_status', pk=ticket.pk)

    return render(request, 'queue_management/join_queue.html', {
        'missions': missions, 'services': services, 'selected_mission_id': selected_mission_id,
    })


def _average_minutes(seconds_list):
    if not seconds_list:
        return None
    return round((sum(seconds_list) / len(seconds_list)) / 60, 1)


def queue_ticket_status_view(request, pk):
    ticket = get_object_or_404(QueueTicket, pk=pk)
    now_serving = QueueTicket.objects.filter(
        mission=ticket.mission, date=ticket.date, status=QueueTicket.Status.SERVING
    ).order_by('-called_at').first()
    people_ahead = QueueTicket.objects.filter(
        mission=ticket.mission, date=ticket.date, status=QueueTicket.Status.WAITING,
        ticket_number__lt=ticket.ticket_number,
    ).count()
    completed_today = QueueTicket.objects.filter(
        mission=ticket.mission, date=ticket.date, status=QueueTicket.Status.COMPLETED
    )
    avg_minutes = _average_minutes([t.service_seconds for t in completed_today if t.service_seconds is not None])
    estimated_wait_minutes = round(people_ahead * avg_minutes) if avg_minutes else None

    return render(request, 'queue_management/ticket_status.html', {
        'ticket': ticket,
        'now_serving': now_serving,
        'people_ahead': people_ahead,
        'estimated_wait_minutes': estimated_wait_minutes,
    })


def queue_display_view(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    today = timezone.now().date()
    now_serving = QueueTicket.objects.filter(
        mission=mission, date=today, status=QueueTicket.Status.SERVING
    ).order_by('-called_at').first()
    upcoming = QueueTicket.objects.filter(
        mission=mission, date=today, status=QueueTicket.Status.WAITING
    ).order_by('-priority', 'ticket_number')[:10]

    return render(request, 'queue_management/display_screen.html', {
        'mission': mission, 'now_serving': now_serving, 'upcoming': upcoming,
    })


@login_required
def staff_queue_dashboard(request):
    missions = missions_for_user(request.user)
    today = timezone.now().date()
    tickets = QueueTicket.objects.filter(mission__in=missions, date=today).select_related('mission', 'service')
    return render(request, 'queue_management/staff_dashboard.html', {
        'tickets': tickets.order_by('-priority', 'ticket_number'),
        'missions': missions,
    })


@login_required
def queue_call_next_view(request, mission_pk):
    mission = get_object_or_404(Mission, pk=mission_pk)
    if not user_can_manage_mission(request.user, mission):
        return redirect('staff_queue_dashboard')

    today = timezone.now().date()
    with transaction.atomic():
        next_ticket = QueueTicket.objects.select_for_update().filter(
            mission=mission, date=today, status=QueueTicket.Status.WAITING
        ).order_by('-priority', 'ticket_number').first()
        if next_ticket:
            # Anyone still being served is marked completed automatically when staff calls the next number.
            QueueTicket.objects.filter(mission=mission, date=today, status=QueueTicket.Status.SERVING).update(
                status=QueueTicket.Status.COMPLETED, completed_at=timezone.now()
            )
            next_ticket.status = QueueTicket.Status.SERVING
            next_ticket.called_at = timezone.now()
            next_ticket.called_by = request.user
            next_ticket.save(update_fields=['status', 'called_at', 'called_by'])
            log_audit_action(
                request.user, None, 'Queue Call Next',
                f'Called ticket #{next_ticket.ticket_number} at {mission.name}.', request=request,
            )
            messages.success(request, _('Now serving ticket #%(number)s.') % {'number': next_ticket.ticket_number})
        else:
            messages.error(request, _('No one is waiting in the queue.'))
    return redirect('staff_queue_dashboard')


@login_required
def queue_ticket_action_view(request, pk, action):
    ticket = get_object_or_404(QueueTicket, pk=pk)
    if not user_can_manage_mission(request.user, ticket.mission):
        return redirect('staff_queue_dashboard')

    if action == 'skip':
        ticket.status = QueueTicket.Status.SKIPPED
    elif action == 'recall':
        ticket.status = QueueTicket.Status.WAITING
        ticket.called_at = None
    elif action == 'complete':
        ticket.status = QueueTicket.Status.COMPLETED
        ticket.completed_at = timezone.now()
    elif action == 'no_show':
        ticket.status = QueueTicket.Status.NO_SHOW
    ticket.save()
    log_audit_action(
        request.user, None, f'Queue Ticket {action}',
        f'Ticket #{ticket.ticket_number} at {ticket.mission.name}.', request=request,
    )
    return redirect('staff_queue_dashboard')


@login_required
def queue_analytics_view(request):
    missions = missions_for_user(request.user)
    today = timezone.now().date()
    qs = QueueTicket.objects.filter(mission__in=missions, date=today)
    completed = qs.filter(status=QueueTicket.Status.COMPLETED)

    avg_wait_minutes = _average_minutes([t.wait_seconds for t in qs if t.wait_seconds is not None]) or 0
    avg_service_minutes = _average_minutes([t.service_seconds for t in completed if t.service_seconds is not None]) or 0

    return render(request, 'queue_management/analytics.html', {
        'total_today': qs.count(),
        'completed_today': completed.count(),
        'waiting_today': qs.filter(status=QueueTicket.Status.WAITING).count(),
        'avg_wait_minutes': avg_wait_minutes,
        'avg_service_minutes': avg_service_minutes,
    })
