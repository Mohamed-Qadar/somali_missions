import secrets
import string

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


def generate_tracking_code():
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        if not Complaint.objects.filter(tracking_code=code).exists():
            return code
    return secrets.token_hex(4).upper()


class Mission(models.Model):
    class MissionType(models.TextChoices):
        EMBASSY = 'EM', _('Embassy')
        CONSULATE = 'CO', _('Consulate')

    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True, null=True)
    working_hours = models.TextField(blank=True)
    mission_type = models.CharField(
        max_length=2,
        choices=MissionType.choices,
        default=MissionType.EMBASSY,
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    staff_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='assigned_missions',
    )

    def __str__(self):
        return self.name


class MissionService(models.Model):
    class ServiceType(models.TextChoices):
        PASSPORT_RENEWAL = 'PASSPORT_RENEWAL', _('Passport renewal')
        DOCUMENT_AUTHENTICATION = 'DOCUMENT_AUTHENTICATION', _('Document authentication')
        VISA = 'VISA', _('Visa issue')
        LOST_PASSPORT = 'LOST_PASSPORT', _('Lost passport')
        EMERGENCY_ASSISTANCE = 'EMERGENCY_ASSISTANCE', _('Emergency assistance')
        CIVIL_REGISTRATION = 'CIVIL_REGISTRATION', _('Civil registration')
        OTHER = 'OTHER', _('Other')

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=150)
    service_type = models.CharField(max_length=30, choices=ServiceType.choices, default=ServiceType.OTHER)
    description = models.TextField(blank=True)
    expected_processing_time = models.CharField(max_length=120, blank=True)
    appointment_required = models.BooleanField(default=True)
    best_arrival_time = models.CharField(max_length=120, blank=True)
    fee_note = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['mission__country', 'mission__city', 'name']
        unique_together = ('mission', 'service_type', 'name')

    def __str__(self):
        return f"{self.name} - {self.mission.name}"


class RequiredDocument(models.Model):
    service = models.ForeignKey(MissionService, on_delete=models.CASCADE, related_name='required_documents')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class EmergencySupportContact(models.Model):
    class ContactType(models.TextChoices):
        ASSOCIATION = 'ASSOCIATION', _('Somali association')
        STUDENT_GROUP = 'STUDENT_GROUP', _('Student group')
        SHELTER = 'SHELTER', _('Shelter')
        HOTEL = 'HOTEL', _('Affordable accommodation')
        TRANSPORT = 'TRANSPORT', _('Transport guidance')
        EMERGENCY = 'EMERGENCY', _('Emergency contact')
        OTHER = 'OTHER', _('Other')

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='support_contacts')
    name = models.CharField(max_length=180)
    contact_type = models.CharField(max_length=20, choices=ContactType.choices, default=ContactType.OTHER)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['contact_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()})"


class UserProfile(models.Model):
    class Role(models.TextChoices):
        CITIZEN = 'CITIZEN', _('Citizen')
        EMBASSY_STAFF = 'EMBASSY_STAFF', _('Embassy Staff (Legacy)')
        EMBASSY_OFFICER = 'EMBASSY_OFFICER', _('Embassy Officer')
        EMBASSY_MANAGER = 'EMBASSY_MANAGER', _('Embassy Manager')
        MINISTRY_REVIEWER = 'MINISTRY_REVIEWER', _('Ministry Reviewer')
        MINISTRY_ADMIN = 'MINISTRY_ADMIN', _('Ministry Administrator')
        COMMUNITY_REP = 'COMMUNITY_REP', _('Community Representative')

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CITIZEN)
    mission = models.ForeignKey(Mission, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profiles')
    full_name = models.CharField(max_length=150)
    national_id = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    country_of_residence = models.CharField(max_length=100, blank=True, null=True)
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class CommunityStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending review')
    VERIFIED = 'VERIFIED', _('Verified')
    REJECTED = 'REJECTED', _('Rejected')
    SUSPENDED = 'SUSPENDED', _('Suspended')


class CommunityGroup(models.Model):
    name = models.CharField(max_length=180)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='community/logos/', null=True, blank=True)
    contact_email = models.EmailField(blank=True)
    phone_whatsapp = models.CharField(max_length=60, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    office_location = models.TextField(blank=True)
    emergency_support_available = models.BooleanField(default=False)
    emergency_support_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=CommunityStatus.choices, default=CommunityStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['country', 'city', 'name']

    def __str__(self):
        return self.name

    @property
    def is_public(self):
        return self.status == CommunityStatus.VERIFIED


class StudentAssociation(models.Model):
    name = models.CharField(max_length=180)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    university_name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='student_associations/logos/', null=True, blank=True)
    contact_email = models.EmailField(blank=True)
    phone_whatsapp = models.CharField(max_length=60, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    office_location = models.TextField(blank=True)
    emergency_support_available = models.BooleanField(default=False)
    emergency_support_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=CommunityStatus.choices, default=CommunityStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['country', 'city', 'university_name', 'name']

    def __str__(self):
        return self.name

    @property
    def is_public(self):
        return self.status == CommunityStatus.VERIFIED


class CommunityRepresentative(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='community_representations')
    community_group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='representatives')
    student_association = models.ForeignKey(StudentAssociation, on_delete=models.CASCADE, null=True, blank=True, related_name='representatives')
    title = models.CharField(max_length=120, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('user', 'community_group'),
            ('user', 'student_association'),
        )

    def __str__(self):
        target = self.community_group or self.student_association
        return f"{self.user.username} - {target}"


class CommunityEvent(models.Model):
    class EventType(models.TextChoices):
        EVENT = 'EVENT', _('Event')
        MEETING = 'MEETING', _('Meeting')
        ORIENTATION = 'ORIENTATION', _('Student orientation')
        VOLUNTEER = 'VOLUNTEER', _('Volunteer campaign')
        GUIDANCE = 'GUIDANCE', _('Travel guidance')

    community_group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    student_association = models.ForeignKey(StudentAssociation, on_delete=models.CASCADE, null=True, blank=True, related_name='events')
    title = models.CharField(max_length=180)
    event_type = models.CharField(max_length=15, choices=EventType.choices, default=EventType.EVENT)
    description = models.TextField()
    location = models.CharField(max_length=180, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-starts_at']

    def __str__(self):
        return self.title


class CommunityAnnouncement(models.Model):
    class AnnouncementType(models.TextChoices):
        GENERAL = 'GENERAL', _('Community announcement')
        EMERGENCY = 'EMERGENCY', _('Emergency notice')
        ACCOMMODATION = 'ACCOMMODATION', _('Accommodation support')
        TRAVEL = 'TRAVEL', _('Travel guidance')
        EMBASSY_VISIT = 'EMBASSY_VISIT', _('Embassy/consulate visit guidance')
        VOLUNTEER = 'VOLUNTEER', _('Volunteer campaign')

    community_group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    student_association = models.ForeignKey(StudentAssociation, on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    title = models.CharField(max_length=180)
    announcement_type = models.CharField(max_length=20, choices=AnnouncementType.choices, default=AnnouncementType.GENERAL)
    body = models.TextField()
    is_public = models.BooleanField(default=False)
    is_moderated = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class CommunityVerificationRequest(models.Model):
    class Decision(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    community_group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='verification_requests')
    student_association = models.ForeignKey(StudentAssociation, on_delete=models.CASCADE, null=True, blank=True, related_name='verification_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    evidence = models.FileField(upload_to='community/verification/', null=True, blank=True)
    notes = models.TextField(blank=True)
    decision = models.CharField(max_length=10, choices=Decision.choices, default=Decision.PENDING)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='community_reviews')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Verification request #{self.pk}"


class CommunityMessage(models.Model):
    community_group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    student_association = models.ForeignKey(StudentAssociation, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    sender_name = models.CharField(max_length=150)
    sender_email = models.EmailField(blank=True)
    sender_phone = models.CharField(max_length=60, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.sender_name}"


class EmergencySupportOffer(models.Model):
    class OfferType(models.TextChoices):
        ACCOMMODATION = 'ACCOMMODATION', _('Accommodation')
        TRANSLATION = 'TRANSLATION', _('Translation')
        TRANSPORT = 'TRANSPORT', _('Transport guidance')
        FOOD = 'FOOD', _('Food/basic needs')
        VOLUNTEER = 'VOLUNTEER', _('Volunteer support')
        OTHER = 'OTHER', _('Other')

    community_group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='support_offers')
    student_association = models.ForeignKey(StudentAssociation, on_delete=models.CASCADE, null=True, blank=True, related_name='support_offers')
    offer_type = models.CharField(max_length=20, choices=OfferType.choices)
    title = models.CharField(max_length=180)
    description = models.TextField()
    contact_phone = models.CharField(max_length=60, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_verified', 'offer_type', 'title']

    def __str__(self):
        return self.title


class Complaint(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', _('Submitted')
        ASSIGNED = 'ASSIGNED', _('Assigned')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        INVESTIGATION = 'INVESTIGATION', _('Investigation')
        AWAITING_RESPONSE = 'AWAITING_RESPONSE', _('Awaiting Response')
        RESOLVED = 'RESOLVED', _('Resolved')
        CLOSED = 'CLOSED', _('Closed')
        # Compatibility with old DB values
        NEW = 'NEW', _('Submitted (New)')
        PRO = 'PRO', _('Under Review (In Progress)')
        RES = 'RES', _('Resolved')
        CLO = 'CLO', _('Closed')

    class Sentiment(models.TextChoices):
        POSITIVE = 'POS', _('Positive')
        NEUTRAL = 'NEU', _('Neutral')
        NEGATIVE = 'NEG', _('Negative')
        UNKNOWN = 'UNK', _('Unknown')

    class Category(models.TextChoices):
        PASSPORT = 'PASSPORT', _('Passport Delays')
        VISA = 'VISA', _('Visa Problems')
        CONSULAR = 'CONSULAR', _('Consular Services')
        STAFF = 'STAFF', _('Staff Misconduct')
        CORRUPTION = 'CORRUPTION', _('Corruption')
        APPOINTMENT = 'APPOINTMENT', _('Appointment Issues')
        AUTHENTICATION = 'AUTHENTICATION', _('Document Authentication')
        LOST_DOCS = 'LOST_DOCS', _('Lost Documents')
        EMERGENCY = 'EMERGENCY', _('Emergency Assistance')
        OTHER = 'OTHER', _('Other')
        # Compatibility with old database values
        DELAY = 'DELAY', _('Delay')
        DOCUMENT = 'DOCUMENT', _('Document')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        MEDIUM = 'MEDIUM', _('Medium')
        HIGH = 'HIGH', _('High')
        CRITICAL = 'CRITICAL', _('Critical')

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='complaints')
    tracking_code = models.CharField(max_length=8, unique=True, editable=False, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rate the service from 1 to 5 stars.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.LOW,
    )
    sentiment = models.CharField(
        max_length=3,
        choices=Sentiment.choices,
        default=Sentiment.UNKNOWN,
        blank=True,
    )
    suggested_department = models.CharField(max_length=100, blank=True, default='')
    citizen_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='complaints',
    )
    satisfaction_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
    )
    satisfaction_comment = models.TextField(blank=True, default='')
    original_language = models.CharField(max_length=5, default='en')
    translated_subject = models.CharField(max_length=255, blank=True, default='')
    translated_message = models.TextField(blank=True, default='')
    internal_notes = models.TextField(blank=True, default='')
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_complaints',
    )
    is_anonymous = models.BooleanField(default=False)
    currently_at_mission = models.BooleanField(default=False)
    travelled_from_another_city = models.BooleanField(default=False)
    no_accommodation = models.BooleanField(default=False)
    has_return_ticket = models.BooleanField(default=False)
    waiting_more_than_two_hours = models.BooleanField(default=False)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    critical_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_critical_reason(self, has_evidence=False):
        reasons = []
        if self.currently_at_mission:
            reasons.append(_('citizen is currently at the mission'))
        if self.travelled_from_another_city:
            reasons.append(_('citizen travelled from another city or country'))
        if self.no_accommodation:
            reasons.append(_('citizen has no accommodation'))
        if self.has_return_ticket:
            reasons.append(_('citizen already has a return ticket'))
        if self.waiting_more_than_two_hours:
            reasons.append(_('citizen has waited more than two hours'))
        has_saved_evidence = self.evidence.exists() if self.pk else False
        if has_evidence or has_saved_evidence:
            reasons.append(_('evidence was attached'))
        if self.category in {
            Complaint.Category.CORRUPTION,
            Complaint.Category.STAFF,
            Complaint.Category.EMERGENCY,
        }:
            reasons.append(_('category indicates corruption, abuse, misconduct, or emergency'))
        return '; '.join(str(reason) for reason in reasons)

    def refresh_priority_from_rules(self, has_evidence=False, save=True):
        reason = self.calculate_critical_reason(has_evidence=has_evidence)
        if reason:
            self.priority = Complaint.Priority.CRITICAL
            self.critical_reason = reason
        if save:
            self.save(update_fields=['priority', 'critical_reason', 'updated_at'])
        return reason

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = generate_tracking_code()
        if self.is_anonymous:
            self.full_name = ''
            self.email = ''
            self.phone = ''
            self.citizen_user = None

        # Run simulated AI classification for priority, category suggestion, and department
        from missions.utils.ai_helpers import classify_complaint_ai
        ai_res = classify_complaint_ai(self.subject, self.message, self.category)
        
        # Auto-set priority if low or empty
        if not self.priority or self.priority == Complaint.Priority.LOW:
            self.priority = ai_res['priority']
        self.suggested_department = ai_res['department']

        # Auto-populate translation if original language is not English
        if self.original_language != 'en' and (not self.translated_subject or not self.translated_message):
            from missions.utils.ai_helpers import translate_text_ai
            self.translated_subject = translate_text_ai(self.subject, self.original_language, 'en')
            self.translated_message = translate_text_ai(self.message, self.original_language, 'en')

        from missions.utils.sentiment import compute_sentiment
        self.sentiment = compute_sentiment(self.rating, self.message)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Complaint #{self.id} for {self.mission.name}"

    @property
    def has_public_response(self):
        return self.responses.filter(is_public=True).exists()

    def public_responses(self):
        return self.responses.filter(is_public=True).order_by('created_at')


class ComplaintEvidence(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='evidence')
    file = models.FileField(upload_to='evidence/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()  # bytes
    file_type = models.CharField(max_length=100)  # mime-type
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence for Complaint #{self.complaint.id} - {self.file_name}"


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=Complaint.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.complaint.tracking_code}: {self.old_status} -> {self.new_status}"


class EscalationRule(models.Model):
    name = models.CharField(max_length=120)
    after_hours = models.PositiveIntegerField()
    target_role = models.CharField(max_length=30, choices=UserProfile.Role.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['after_hours']

    def __str__(self):
        return f"{self.name} ({self.after_hours}h)"


class EscalationLog(models.Model):
    class Channel(models.TextChoices):
        EMAIL = 'EMAIL', _('Email')
        SMS = 'SMS', _('SMS')
        WHATSAPP = 'WHATSAPP', _('WhatsApp')
        IN_APP = 'IN_APP', _('In-app')

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='escalation_logs')
    rule = models.ForeignKey(EscalationRule, on_delete=models.SET_NULL, null=True, blank=True)
    target_role = models.CharField(max_length=30, choices=UserProfile.Role.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.IN_APP)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Escalation {self.target_role} for {self.complaint.tracking_code}"


class NotificationLog(models.Model):
    class Type(models.TextChoices):
        EMAIL = 'EMAIL', _('Email')
        SMS = 'SMS', _('SMS')
        WHATSAPP = 'WHATSAPP', _('WhatsApp')
        IN_APP = 'IN_APP', _('In-app')
    
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=10, choices=Type.choices, default=Type.EMAIL)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='SENT')

    def __str__(self):
        return f"Notification to {self.recipient} via {self.notification_type} at {self.sent_at}"


class EmbassyResponse(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='responses')
    responder_name = models.CharField(max_length=150)
    message = models.TextField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to Complaint #{self.complaint.id}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.email})"


# Signals to automatically create user profile
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        role = UserProfile.Role.MINISTRY_ADMIN if instance.is_superuser else UserProfile.Role.CITIZEN
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'role': role,
                'full_name': instance.get_full_name() or instance.username,
            }
        )


class EmbassyInvitation(models.Model):
    email = models.EmailField(unique=True)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='invitations')
    role = models.CharField(
        max_length=20,
        choices=[
            ('EMBASSY_OFFICER', _('Embassy Officer')),
            ('EMBASSY_MANAGER', _('Embassy Manager'))
        ],
        default='EMBASSY_OFFICER'
    )
    token = models.CharField(max_length=64, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation to {self.email} for {self.mission.name} ({self.role})"


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=150)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on Case #{self.complaint.id} at {self.timestamp}"


class MissionPerformanceScore(models.Model):
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='performance_scores')
    month = models.DateField()
    total_complaints = models.PositiveIntegerField(default=0)
    critical_complaints = models.PositiveIntegerField(default=0)
    resolved_complaints = models.PositiveIntegerField(default=0)
    unresolved_complaints = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    satisfaction_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    average_response_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ai_summary = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month', 'mission__name']
        unique_together = ('mission', 'month')

    def __str__(self):
        return f"{self.mission.name} - {self.month:%Y-%m}"


class SecureMessage(models.Model):
    class SenderType(models.TextChoices):
        CITIZEN = 'CITIZEN', _('Citizen')
        EMBASSY = 'EMBASSY', _('Embassy')
        MINISTRY = 'MINISTRY', _('Ministry')

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='secure_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    sender_type = models.CharField(max_length=10, choices=SenderType.choices, default=SenderType.CITIZEN)
    message = models.TextField()
    attachment = models.FileField(upload_to='secure_messages/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} on Case #{self.complaint.id}"


