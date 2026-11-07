from django.contrib import admin

from .models import (
    ConsularApplication, ConsularApplicationDocument,
    ConsularApplicationStatusHistory,
)


class ConsularApplicationDocumentInline(admin.TabularInline):
    model = ConsularApplicationDocument
    extra = 0
    readonly_fields = ('file_name', 'file_size', 'file_type', 'uploaded_by', 'uploaded_at')


class ConsularApplicationStatusHistoryInline(admin.TabularInline):
    model = ConsularApplicationStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'note', 'created_at')


@admin.register(ConsularApplication)
class ConsularApplicationAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'service', 'mission', 'status', 'full_name', 'created_at')
    list_filter = ('status', 'mission', 'service__service_type')
    search_fields = ('reference_code', 'full_name', 'email', 'phone', 'passport_number')
    readonly_fields = ('reference_code', 'submitted_at', 'created_at', 'updated_at')
    inlines = [ConsularApplicationDocumentInline, ConsularApplicationStatusHistoryInline]
