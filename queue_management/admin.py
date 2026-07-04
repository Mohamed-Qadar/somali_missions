from django.contrib import admin

from .models import QueueTicket


@admin.register(QueueTicket)
class QueueTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'mission', 'date', 'status', 'priority', 'called_at', 'completed_at')
    list_filter = ('status', 'mission', 'date')
    search_fields = ('mission__name', 'full_name')
    date_hierarchy = 'date'
