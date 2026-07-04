from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from missions.models import UserProfile

from .channels import notify
from .models import Notification


@login_required
def notification_history_view(request):
    qs = Notification.objects.filter(recipient=request.user)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'notifications/history.html', {'page_obj': page})


@login_required
def mark_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return redirect(notification.link_url or 'notification_history')


@login_required
def mark_all_read_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, _('All notifications marked as read.'))
    return redirect('notification_history')


@login_required
def emergency_broadcast_view(request):
    if request.user.profile.role != UserProfile.Role.MINISTRY_ADMIN and not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        audience = request.POST.get('audience')
        title = request.POST.get('title', '').strip()
        body = request.POST.get('body', '').strip()

        if audience == 'all_staff':
            recipients = User.objects.filter(
                profile__role__in=[UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER]
            )
        elif audience == 'all_citizens':
            recipients = User.objects.filter(profile__role=UserProfile.Role.CITIZEN)
        else:
            recipients = User.objects.all()

        count = 0
        for recipient in recipients:
            notify(
                recipient, title, body,
                category=Notification.Category.EMERGENCY,
                priority=Notification.Priority.CRITICAL,
                channels=['email'],
            )
            count += 1
        messages.success(request, _('Emergency notification sent to %(count)s recipient(s).') % {'count': count})
        return redirect('emergency_broadcast')

    return render(request, 'notifications/emergency_broadcast.html')
