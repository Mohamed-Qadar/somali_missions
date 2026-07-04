from django.contrib import admin

from .models import Notification, NotificationDeliveryLog


class NotificationDeliveryLogInline(admin.TabularInline):
    model = NotificationDeliveryLog
    extra = 0
    readonly_fields = ('channel', 'delivered', 'detail', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'category', 'priority', 'is_read', 'created_at')
    list_filter = ('category', 'priority', 'is_read')
    search_fields = ('title', 'body', 'recipient__username')
    date_hierarchy = 'created_at'
    inlines = [NotificationDeliveryLogInline]
