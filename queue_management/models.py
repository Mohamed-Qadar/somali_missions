from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from appointments.models import Appointment
from missions.models import Mission, MissionService


class QueueTicket(models.Model):
    class Status(models.TextChoices):
        WAITING = 'WAITING', _('Waiting')
        CALLED = 'CALLED', _('Called')
        SERVING = 'SERVING', _('Serving')
        COMPLETED = 'COMPLETED', _('Completed')
        SKIPPED = 'SKIPPED', _('Skipped')
        NO_SHOW = 'NO_SHOW', _('No Show')

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='queue_tickets')
    service = models.ForeignKey(
        MissionService, on_delete=models.SET_NULL, null=True, blank=True, related_name='queue_tickets'
    )
    appointment = models.ForeignKey(
        Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='queue_tickets'
    )
    ticket_number = models.PositiveIntegerField()
    date = models.DateField()
    full_name = models.CharField(max_length=150, blank=True)
    priority = models.PositiveSmallIntegerField(default=0, help_text=_('Higher value is served first.'))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING)
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    called_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='queue_calls'
    )

    class Meta:
        ordering = ['date', 'ticket_number']
        unique_together = ('mission', 'date', 'ticket_number')
        indexes = [models.Index(fields=['mission', 'date', 'status'])]

    def __str__(self):
        return f"#{self.ticket_number} - {self.mission.name} ({self.date})"

    @property
    def wait_seconds(self):
        if self.called_at:
            return (self.called_at - self.created_at).total_seconds()
        return None

    @property
    def service_seconds(self):
        if self.called_at and self.completed_at:
            return (self.completed_at - self.called_at).total_seconds()
        return None
