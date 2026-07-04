import os
import tarfile
from datetime import datetime

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Back up the database (portable JSON fixture via dumpdata, works for '
        'both the SQLite dev database and Postgres in production) plus the '
        'media directory into one timestamped .tar.gz under backups/. '
        'Restore with restore_db. Intended to run on a daily cron/Celery Beat '
        'schedule in production.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', default=str(settings.BASE_DIR / 'backups'))

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dump_path = os.path.join(output_dir, f'db_dump_{timestamp}.json')

        with open(dump_path, 'w', encoding='utf-8') as f:
            call_command(
                'dumpdata',
                exclude=['contenttypes', 'auth.permission', 'sessions.session', 'admin.logentry'],
                indent=2,
                stdout=f,
            )

        archive_path = os.path.join(output_dir, f'backup_{timestamp}.tar.gz')
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(dump_path, arcname=os.path.basename(dump_path))
            media_root = str(settings.MEDIA_ROOT)
            if os.path.isdir(media_root) and os.listdir(media_root):
                tar.add(media_root, arcname='media')

        os.remove(dump_path)
        self.stdout.write(self.style.SUCCESS(f'Backup created: {archive_path}'))
