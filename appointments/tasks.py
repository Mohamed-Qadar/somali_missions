from celery import shared_task
from django.core.management import call_command


@shared_task
def send_appointment_reminders_task():
    """Celery wrapper around the send_appointment_reminders management command,
    so it can be scheduled via Celery Beat (django_celery_beat's admin UI lets
    an operator add a daily periodic task pointing at this) instead of relying
    on host-level cron."""
    call_command('send_appointment_reminders')
