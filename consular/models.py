import secrets
import string

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from missions.models import Mission, MissionService, RequiredDocument


def generate_reference_code():
    """Human-friendly unique application reference, e.g. 'CS-A1B2C3D4'."""
    alphabet = string.ascii_uppercase + string.digits
    for _attempt in range(20):
        code = 'CS-' + ''.join(secrets.choice(alphabet) for _ in range(8))
        if not ConsularApplication.objects.filter(reference_code=code).exists():
            return code
    return 'CS-' + secrets.token_hex(4).upper()


class ConsularApplication(models.Model):
    """A citizen's online consular service application to a specific mission.

    Reuses the existing per-mission MissionService catalogue as the definition
    of *what* is being applied for, so nothing about services is duplicated -
    this model only adds the citizen-facing workflow (status, documents,
    reference number, optional appointment link) on top."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        SUBMITTED = 'SUBMITTED', _('Submitted')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        DOCS_REQUIRED = 'DOCS_REQUIRED', _('Additional Documents Required')
        APPROVED = 'APPROVED', _('Approved / Ready')
        APPOINTMENT_REQUIRED = 'APPOINTMENT_REQUIRED', _('Appointment Required')
        COMPLETED = 'COMPLETED', _('Completed')
        REJECTED = 'REJECTED', _('Rejected')
        CANCELLED = 'CANCELLED', _('Cancelled')

    # Statuses that count as still-in-progress for citizen/staff dashboards.
    OPEN_STATUSES = (
        Status.SUBMITTED, Status.UNDER_REVIEW, Status.DOCS_REQUIRED,
        Status.APPROVED, Status.APPOINTMENT_REQUIRED,
    )
    CLOSED_STATUSES = (Status.COMPLETED, Status.REJECTED, Status.CANCELLED)

    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE, related_name='consular_applications',
    )
    service = models.ForeignKey(
        MissionService, on_delete=models.PROTECT, related_name='consular_applications',
    )
    citizen_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consular_applications',
    )
    reference_code = models.CharField(max_length=12, unique=True, editable=False, blank=True)

    # Applicant details - only what a consular application legitimately needs.
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    passport_number = models.CharField(max_length=50, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    notes = models.TextField(
        blank=True, help_text=_('Anything the mission should know about your request.'),
    )

    status = models.CharField(max_length=25, choices=Status.choices, default=Status.SUBMITTED)
    # Internal, staff-only notes never shown to the citizen.
    staff_notes = models.TextField(blank=True, default='')
    # A message written by staff that the citizen *does* see on their tracker.
    citizen_message = models.TextField(blank=True, default='')

    # Where physical attendance is required, connect to the existing appointment
    # system rather than building a parallel one.
    appointment = models.ForeignKey(
        'appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consular_applications',
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mission', 'status']),
            models.Index(fields=['reference_code']),
            models.Index(fields=['citizen_user', 'status']),
        ]

    def __str__(self):
        return f'{self.reference_code} - {self.service.name} ({self.mission.name})'

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = generate_reference_code()
        if self.status != self.Status.DRAFT and not self.submitted_at:
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @property
    def needs_appointment(self):
        return self.status == self.Status.APPOINTMENT_REQUIRED

    @property
    def can_upload_more(self):
        """Citizens may add documents while the request is still open."""
        return self.status in (
            self.Status.SUBMITTED, self.Status.UNDER_REVIEW, self.Status.DOCS_REQUIRED,
        )


class ConsularApplicationDocument(models.Model):
    application = models.ForeignKey(
        ConsularApplication, on_delete=models.CASCADE, related_name='documents',
    )
    # Optional link to the service's declared requirement, so staff can see
    # which checklist item a file satisfies. Free-form uploads leave it null.
    requirement = models.ForeignKey(
        RequiredDocument, on_delete=models.SET_NULL, null=True, blank=True,
    )
    file = models.FileField(upload_to='consular/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()  # bytes
    file_type = models.CharField(max_length=100)  # mime-type
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f'{self.file_name} for {self.application.reference_code}'


class ConsularApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        ConsularApplication, on_delete=models.CASCADE, related_name='status_history',
    )
    old_status = models.CharField(max_length=25, blank=True)
    new_status = models.CharField(max_length=25, choices=ConsularApplication.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.application.reference_code}: {self.old_status} -> {self.new_status}'
