from django.contrib import admin

from .models import Appointment, AppointmentSlot, AppointmentStatusHistory


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ('mission', 'service', 'date', 'start_time', 'end_time', 'capacity', 'is_active')
    list_filter = ('is_active', 'mission', 'date')
    search_fields = ('mission__name', 'service__name')
    date_hierarchy = 'date'


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('qr_token', 'mission', 'service', 'full_name', 'status', 'created_at')
    list_filter = ('status', 'mission')
    search_fields = ('qr_token', 'full_name', 'email', 'phone')
    readonly_fields = ('qr_token', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(AppointmentStatusHistory)
class AppointmentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'old_status', 'new_status', 'changed_by', 'created_at')
    search_fields = ('appointment__qr_token',)
    readonly_fields = ('created_at',)
