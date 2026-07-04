from django.utils import timezone


def site_context(request):
    unread_notification_count = 0
    if request.user.is_authenticated:
        from notifications.models import Notification
        unread_notification_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return {'now': timezone.now(), 'unread_notification_count': unread_notification_count}
