from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AssistantTopic(models.Model):
    class TopicKey(models.TextChoices):
        PASSPORT_RENEWAL = 'PASSPORT_RENEWAL', _('Passport Renewal')
        LOST_PASSPORT = 'LOST_PASSPORT', _('Lost Passport')
        VISA = 'VISA', _('Visa')
        BIRTH_CERTIFICATE = 'BIRTH_CERTIFICATE', _('Birth Certificate')
        MARRIAGE = 'MARRIAGE', _('Marriage')
        EMERGENCY_TRAVEL = 'EMERGENCY_TRAVEL', _('Emergency Travel')
        DOCUMENT_AUTHENTICATION = 'DOCUMENT_AUTHENTICATION', _('Document Authentication')
        CITIZENSHIP = 'CITIZENSHIP', _('Citizenship')
        REQUIRED_DOCUMENTS = 'REQUIRED_DOCUMENTS', _('Required Documents')
        OFFICE_HOURS = 'OFFICE_HOURS', _('Office Hours')
        APPOINTMENT_GUIDANCE = 'APPOINTMENT_GUIDANCE', _('Appointment Guidance')
        COMPLAINT_GUIDANCE = 'COMPLAINT_GUIDANCE', _('Complaint Guidance')

    class SuggestedAction(models.TextChoices):
        BOOK_APPOINTMENT = 'book_appointment', _('Book Appointment')
        SUBMIT_COMPLAINT = 'submit_complaint', _('Submit Complaint')
        VIEW_REQUIREMENTS = 'view_requirements', _('View Requirements')
        TRACK_COMPLAINT = 'track_complaint', _('Track a Complaint')
        NONE = 'none', _('None')

    topic_key = models.CharField(max_length=40, choices=TopicKey.choices, unique=True)
    title = models.CharField(max_length=200)
    keywords = models.TextField(help_text=_('Comma-separated keywords used to match citizen questions.'))
    answer = models.TextField()
    suggested_action = models.CharField(max_length=30, choices=SuggestedAction.choices, default=SuggestedAction.NONE)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def keyword_list(self):
        return [k.strip().lower() for k in self.keywords.split(',') if k.strip()]


class AssistantConversationLog(models.Model):
    """Records every question asked so a future AI provider has real training/eval data."""

    session_key = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    query_text = models.TextField()
    matched_topic = models.ForeignKey(AssistantTopic, on_delete=models.SET_NULL, null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.query_text[:60]
