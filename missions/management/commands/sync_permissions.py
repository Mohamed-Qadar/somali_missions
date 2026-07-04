from django.core.management.base import BaseCommand

from missions.models import UserProfile
from missions.utils.permissions import sync_user_permissions


class Command(BaseCommand):
    help = (
        'Reconcile every user\'s Django Group membership and Mission.staff_users '
        'with their UserProfile.role/mission (the single source of truth). '
        'Idempotent - run once after upgrading, or any time you suspect the '
        'projections have drifted (e.g. groups edited directly in the admin).'
    )

    def handle(self, *args, **options):
        count = 0
        for profile in UserProfile.objects.select_related('user', 'mission'):
            sync_user_permissions(profile)
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Synced permissions for {count} user profile(s).'))
