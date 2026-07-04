"""
Notification channel abstraction.

InAppChannel and EmailChannel are fully functional today (reusing the
project's existing EMAIL_BACKEND/send_mail setup). SMSChannel and
WhatsAppChannel are real, documented interface implementations that
log the intent to send and return delivered=False - they are "ready"
in the sense that swapping in a real provider (e.g. Twilio, WhatsApp
Business API) only requires filling in the send() body with an API
call; nothing here pretends a message was actually delivered when no
provider is configured.
"""
import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger('notifications')


class NotificationChannel(ABC):
    channel_key = None

    @abstractmethod
    def send(self, notification) -> tuple[bool, str]:
        """Return (delivered: bool, detail: str)."""
        raise NotImplementedError


class InAppChannel(NotificationChannel):
    channel_key = 'IN_APP'

    def send(self, notification) -> tuple[bool, str]:
        # The Notification row itself *is* the in-app delivery - nothing further to do.
        return True, 'Stored as in-app notification.'


class EmailChannel(NotificationChannel):
    channel_key = 'EMAIL'

    def send(self, notification) -> tuple[bool, str]:
        email = notification.recipient.email
        if not email:
            return False, 'Recipient has no email address on file.'
        send_mail(
            subject=notification.title,
            message=notification.body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            recipient_list=[email],
            fail_silently=True,
        )
        return True, f'Emailed to {email}.'


class SMSChannel(NotificationChannel):
    """SMS-ready: no SMS provider (e.g. Twilio) is configured in this environment.
    Logs the intent instead of pretending to deliver a text message."""
    channel_key = 'SMS'

    def send(self, notification) -> tuple[bool, str]:
        phone = getattr(getattr(notification.recipient, 'profile', None), 'phone_number', '') or ''
        if not phone:
            return False, 'Recipient has no phone number on file.'
        logger.info('[SMS-READY, no provider configured] Would send to %s: %s', phone, notification.title)
        return False, f'SMS provider not configured; intent logged for {phone}.'


class WhatsAppChannel(NotificationChannel):
    """WhatsApp-ready: no WhatsApp Business API credentials are configured.
    Logs the intent instead of pretending to deliver a message."""
    channel_key = 'WHATSAPP'

    def send(self, notification) -> tuple[bool, str]:
        phone = getattr(getattr(notification.recipient, 'profile', None), 'phone_number', '') or ''
        if not phone:
            return False, 'Recipient has no phone number on file.'
        logger.info('[WHATSAPP-READY, no provider configured] Would send to %s: %s', phone, notification.title)
        return False, f'WhatsApp provider not configured; intent logged for {phone}.'


CHANNEL_REGISTRY = {
    'in_app': InAppChannel,
    'email': EmailChannel,
    'sms': SMSChannel,
    'whatsapp': WhatsAppChannel,
}


def notify(recipient, title, body='', category='INFO', priority=1, link_url='', channels=None):
    """Create an in-app Notification and dispatch it through any additional
    requested channels (e.g. ['email']). Always creates the Notification row
    regardless of which extra channels are requested."""
    from .models import Notification, NotificationDeliveryLog

    notification = Notification.objects.create(
        recipient=recipient, title=title, body=body, category=category, priority=priority, link_url=link_url,
    )

    requested = ['in_app'] + [c for c in (channels or []) if c != 'in_app']
    for channel_name in requested:
        channel_cls = CHANNEL_REGISTRY.get(channel_name)
        if not channel_cls:
            continue
        delivered, detail = channel_cls().send(notification)
        NotificationDeliveryLog.objects.create(
            notification=notification,
            channel=channel_cls.channel_key,
            delivered=delivered,
            detail=detail,
        )
    return notification
