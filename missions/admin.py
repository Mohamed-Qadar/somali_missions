from django.contrib import admin
from .models import (
    Mission, MissionService, RequiredDocument, EmergencySupportContact,
    Complaint, ComplaintEvidence, ComplaintStatusHistory, EmbassyResponse,
    ContactMessage, EscalationRule, EscalationLog, NotificationLog,
    MissionPerformanceScore, AuditLog, CommunityStatus, CommunityGroup,
    StudentAssociation, CommunityRepresentative, CommunityEvent,
    CommunityAnnouncement, CommunityVerificationRequest, CommunityMessage,
    EmergencySupportOffer, UserProfile, EmbassyInvitation, SecureMessage,
)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'mission', 'subject', 'is_anonymous', 'category', 'rating', 'sentiment', 'status', 'created_at')
    list_filter = ('status', 'mission', 'sentiment', 'rating', 'category', 'is_anonymous')
    search_fields = ('tracking_code', 'subject', 'message', 'full_name', 'email')
    readonly_fields = ('tracking_code', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_per_page = 50


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'city', 'mission_type')
    list_filter = ('mission_type', 'country')
    search_fields = ('name', 'country', 'city')
    filter_horizontal = ('staff_users',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'mission', 'full_name', 'email_verified')
    list_filter = ('role', 'email_verified', 'mission')
    search_fields = ('user__username', 'user__email', 'full_name', 'national_id', 'phone_number')
    autocomplete_fields = ('mission',)


@admin.register(EmbassyInvitation)
class EmbassyInvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'mission', 'role', 'is_used', 'created_at')
    list_filter = ('role', 'is_used', 'mission')
    search_fields = ('email', 'mission__name')
    readonly_fields = ('token', 'created_at')


@admin.register(SecureMessage)
class SecureMessageAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'sender', 'sender_type', 'is_read', 'created_at')
    list_filter = ('sender_type', 'is_read')
    search_fields = ('complaint__tracking_code', 'sender__username', 'message')
    readonly_fields = ('created_at',)


def mark_verified(modeladmin, request, queryset):
    queryset.update(status=CommunityStatus.VERIFIED)


def mark_suspended(modeladmin, request, queryset):
    queryset.update(status=CommunityStatus.SUSPENDED)


def mark_public_moderated(modeladmin, request, queryset):
    queryset.update(is_public=True, is_moderated=True)


mark_verified.short_description = "Mark selected groups as verified"
mark_suspended.short_description = "Suspend selected groups"
mark_public_moderated.short_description = "Approve and publish selected announcements"


@admin.register(EmbassyResponse)
class EmbassyResponseAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'responder_name', 'is_public', 'created_at')
    list_filter = ('is_public',)


class RequiredDocumentInline(admin.TabularInline):
    model = RequiredDocument
    extra = 1


@admin.register(MissionService)
class MissionServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'mission', 'service_type', 'expected_processing_time', 'appointment_required', 'is_active')
    list_filter = ('service_type', 'appointment_required', 'is_active')
    search_fields = ('name', 'mission__name', 'description')
    inlines = [RequiredDocumentInline]


@admin.register(EmergencySupportContact)
class EmergencySupportContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'mission', 'contact_type', 'phone', 'is_public')
    list_filter = ('contact_type', 'is_public')
    search_fields = ('name', 'mission__name', 'phone', 'email', 'notes')


@admin.register(CommunityGroup)
class CommunityGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'city', 'status', 'emergency_support_available', 'emergency_support_verified')
    list_filter = ('status', 'country', 'emergency_support_available', 'emergency_support_verified')
    search_fields = ('name', 'country', 'city', 'description', 'contact_email')
    actions = [mark_verified, mark_suspended]


@admin.register(StudentAssociation)
class StudentAssociationAdmin(admin.ModelAdmin):
    list_display = ('name', 'university_name', 'country', 'city', 'status', 'emergency_support_available', 'emergency_support_verified')
    list_filter = ('status', 'country', 'emergency_support_available', 'emergency_support_verified')
    search_fields = ('name', 'university_name', 'country', 'city', 'description', 'contact_email')
    actions = [mark_verified, mark_suspended]


@admin.register(CommunityRepresentative)
class CommunityRepresentativeAdmin(admin.ModelAdmin):
    list_display = ('user', 'community_group', 'student_association', 'title', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('user__username', 'community_group__name', 'student_association__name', 'title')


@admin.register(CommunityEvent)
class CommunityEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'community_group', 'student_association', 'event_type', 'starts_at', 'is_public')
    list_filter = ('event_type', 'is_public', 'starts_at')
    search_fields = ('title', 'description', 'community_group__name', 'student_association__name')


@admin.register(CommunityAnnouncement)
class CommunityAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'community_group', 'student_association', 'announcement_type', 'is_public', 'is_moderated', 'created_at')
    list_filter = ('announcement_type', 'is_public', 'is_moderated')
    search_fields = ('title', 'body', 'community_group__name', 'student_association__name')
    actions = [mark_public_moderated]


@admin.register(CommunityVerificationRequest)
class CommunityVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('community_group', 'student_association', 'requested_by', 'decision', 'reviewed_by', 'created_at')
    list_filter = ('decision',)
    search_fields = ('community_group__name', 'student_association__name', 'notes', 'requested_by__username')


@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):
    list_display = ('sender_name', 'community_group', 'student_association', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender_name', 'sender_email', 'sender_phone', 'message', 'community_group__name', 'student_association__name')


@admin.register(EmergencySupportOffer)
class EmergencySupportOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'offer_type', 'community_group', 'student_association', 'is_active', 'is_verified')
    list_filter = ('offer_type', 'is_active', 'is_verified')
    search_fields = ('title', 'description', 'community_group__name', 'student_association__name')


@admin.register(ComplaintEvidence)
class ComplaintEvidenceAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'file_name', 'file_type', 'file_size', 'uploaded_at')
    search_fields = ('complaint__tracking_code', 'file_name', 'file_type')
    readonly_fields = ('uploaded_at',)


@admin.register(ComplaintStatusHistory)
class ComplaintStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status',)
    search_fields = ('complaint__tracking_code', 'note')
    readonly_fields = ('created_at',)


@admin.register(EscalationRule)
class EscalationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'after_hours', 'target_role', 'is_active')
    list_filter = ('target_role', 'is_active')


@admin.register(EscalationLog)
class EscalationLogAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'target_role', 'channel', 'handled', 'created_at')
    list_filter = ('target_role', 'channel', 'handled')
    search_fields = ('complaint__tracking_code', 'message')
    readonly_fields = ('created_at',)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'recipient', 'notification_type', 'subject', 'sent_at', 'status')
    list_filter = ('notification_type', 'status')
    search_fields = ('recipient', 'subject', 'message', 'complaint__tracking_code')
    readonly_fields = ('sent_at',)


@admin.register(MissionPerformanceScore)
class MissionPerformanceScoreAdmin(admin.ModelAdmin):
    list_display = ('mission', 'month', 'total_complaints', 'critical_complaints', 'satisfaction_score', 'risk_score')
    list_filter = ('month',)
    search_fields = ('mission__name', 'ai_summary')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'user', 'action', 'timestamp')
    search_fields = ('complaint__tracking_code', 'action', 'details', 'user__username')
    readonly_fields = ('timestamp',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'created_at')
    search_fields = ('subject', 'name', 'email', 'message')
    readonly_fields = ('created_at',)
