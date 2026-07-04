import secrets
import string

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from missions.models import Mission, MissionService


def generate_qr_token():
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        token = ''.join(secrets.choice(alphabet) for _ in range(10))
        if not Appointment.objects.filter(qr_token=token).exists():
            return token
    return secrets.token_hex(5).upper()


class AppointmentSlot(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='appointment_slots')
    service = models.ForeignKey(MissionService, on_delete=models.CASCADE, related_name='appointment_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ('mission', 'service', 'date', 'start_time')
        indexes = [models.Index(fields=['mission', 'date'])]

    def __str__(self):
        return f"{self.mission.name} - {self.service.name} - {self.date} {self.start_time}"

    @property
    def booked_count(self) -> int:
        return self.appointments.filter(
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        ).count()

    @property
    def is_full(self) -> bool:
        return self.booked_count >= self.capacity


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Approval')
        CONFIRMED = 'CONFIRMED', _('Confirmed')
        REJECTED = 'REJECTED', _('Rejected')
        RESCHEDULED = 'RESCHEDULED', _('Rescheduled')
        CANCELLED = 'CANCELLED', _('Cancelled')
        COMPLETED = 'COMPLETED', _('Completed')
        NO_SHOW = 'NO_SHOW', _('No Show')
        WAITLISTED = 'WAITLISTED', _('Waitlisted')

    ACTIVE_STATUSES = (Status.PENDING, Status.CONFIRMED)

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(MissionService, on_delete=models.CASCADE, related_name='appointments')
    slot = models.ForeignKey(AppointmentSlot, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    citizen_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments'
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    qr_token = models.CharField(max_length=12, unique=True, editable=False, blank=True)
    staff_notes = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)
    confirmation_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mission', 'status']),
            models.Index(fields=['qr_token']),
        ]

    def __str__(self):
        return f"Appointment {self.qr_token} - {self.mission.name}"

    def save(self, *args, **kwargs):
        if not self.qr_token:
            self.qr_token = generate_qr_token()
        super().save(*args, **kwargs)


class AppointmentStatusHistory(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.appointment.qr_token}: {self.old_status} -> {self.new_status}"
