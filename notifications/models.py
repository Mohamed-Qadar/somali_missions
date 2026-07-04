from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Category(models.TextChoices):
        INFO = 'INFO', _('Information')
        SUCCESS = 'SUCCESS', _('Success')
        WARNING = 'WARNING', _('Warning')
        EMERGENCY = 'EMERGENCY', _('Emergency')

    class Priority(models.IntegerChoices):
        LOW = 0, _('Low')
        NORMAL = 1, _('Normal')
        HIGH = 2, _('High')
        CRITICAL = 3, _('Critical')

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.INFO)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.NORMAL)
    link_url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f"{self.title} -> {self.recipient.username}"


class NotificationDeliveryLog(models.Model):
    """Records every channel attempted for a notification, honestly noting
    whether a channel actually delivered (email) or only logged an intent
    (SMS/WhatsApp, since no provider credentials are configured)."""

    class Channel(models.TextChoices):
        IN_APP = 'IN_APP', _('In-App')
        EMAIL = 'EMAIL', _('Email')
        SMS = 'SMS', _('SMS')
        WHATSAPP = 'WHATSAPP', _('WhatsApp')

    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='delivery_logs')
    channel = models.CharField(max_length=20, choices=Channel.choices)
    delivered = models.BooleanField(default=False)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.notification_id}: {self.channel} delivered={self.delivered}"
