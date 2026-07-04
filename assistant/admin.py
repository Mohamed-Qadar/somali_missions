from django.contrib import admin

from .models import AssistantConversationLog, AssistantTopic


@admin.register(AssistantTopic)
class AssistantTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic_key', 'suggested_action', 'is_active')
    list_filter = ('is_active', 'suggested_action')
    search_fields = ('title', 'keywords', 'answer')


@admin.register(AssistantConversationLog)
class AssistantConversationLogAdmin(admin.ModelAdmin):
    list_display = ('query_text_short', 'matched_topic', 'confidence', 'user', 'created_at')
    list_filter = ('matched_topic',)
    search_fields = ('query_text',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def query_text_short(self, obj):
        return obj.query_text[:60]
    query_text_short.short_description = 'Query'
