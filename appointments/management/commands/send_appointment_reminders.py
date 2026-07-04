from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.translation import gettext as _

from appointments.models import Appointment


class Command(BaseCommand):
    help = (
        'Send a reminder email for every confirmed appointment scheduled for tomorrow '
        'that has not already been reminded. Intended to run once a day via cron or '
        'Celery Beat (django-celery-beat is installed and can schedule this).'
    )

    def handle(self, *args, **options):
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        due = Appointment.objects.filter(
            slot__date=tomorrow,
            status=Appointment.Status.CONFIRMED,
            reminder_sent=False,
        ).exclude(email='').select_related('mission', 'service', 'slot')

        sent = 0
        for appointment in due:
            send_mail(
                subject=_('Reminder: your appointment tomorrow at %(mission)s') % {'mission': appointment.mission.name},
                message=_(
                    'Dear %(name)s,\n\n'
                    'This is a reminder that you have an appointment tomorrow, %(date)s at %(time)s, '
                    'for %(service)s at %(mission)s.\n'
                    'Reference code: %(code)s\n\n'
                    'Please arrive 15 minutes early with your required documents.'
                ) % {
                    'name': appointment.full_name,
                    'date': appointment.slot.date,
                    'time': appointment.slot.start_time.strftime('%H:%M'),
                    'service': appointment.service.name,
                    'mission': appointment.mission.name,
                    'code': appointment.qr_token,
                },
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[appointment.email],
                fail_silently=True,
            )
            appointment.reminder_sent = True
            appointment.save(update_fields=['reminder_sent'])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f'Sent {sent} appointment reminder(s) for {tomorrow}.'))
