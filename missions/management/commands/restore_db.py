import os
import shutil
import tarfile
import tempfile

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Restore a database + media backup created by backup_db. DESTRUCTIVE: '
        'loads fixture data into the CURRENT database via loaddata, which can '
        'create duplicate/conflicting rows if run against a database that '
        'already has data. Intended for disaster recovery onto a fresh database.'
    )

    def add_arguments(self, parser):
        parser.add_argument('archive_path')
        parser.add_argument('--yes', action='store_true', help='Skip the confirmation prompt.')

    def handle(self, *args, **options):
        archive_path = options['archive_path']
        if not os.path.isfile(archive_path):
            raise CommandError(f'Archive not found: {archive_path}')

        if not options['yes']:
            confirm = input(
                'This will load fixture data into the CURRENT database, which can create '
                'duplicate/conflicting rows if it already has data. Continue? [y/N] '
            )
            if confirm.lower() != 'y':
                self.stdout.write('Aborted.')
                return

        with tempfile.TemporaryDirectory() as tmp_dir:
            # filter='data' rejects path-traversal/absolute-path/device-file
            # entries (PEP 706). Requires Python 3.11.4+, which is already
            # this project's minimum supported version - no fallback needed.
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(tmp_dir, filter='data')

            json_files = [f for f in os.listdir(tmp_dir) if f.endswith('.json')]
            if not json_files:
                raise CommandError('No database dump (.json) found inside the archive.')

            call_command('loaddata', os.path.join(tmp_dir, json_files[0]))

            media_dir = os.path.join(tmp_dir, 'media')
            if os.path.isdir(media_dir):
                shutil.copytree(media_dir, settings.MEDIA_ROOT, dirs_exist_ok=True)

        self.stdout.write(self.style.SUCCESS('Restore complete.'))
