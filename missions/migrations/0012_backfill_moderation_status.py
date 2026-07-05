# Backfill the new 4-state moderation_status from the legacy
# is_public/is_moderated booleans so already-approved community content
# stays publicly visible after the switch.
from django.db import migrations


def forwards(apps, schema_editor):
    CommunityAnnouncement = apps.get_model('missions', 'CommunityAnnouncement')
    CommunityEvent = apps.get_model('missions', 'CommunityEvent')

    CommunityAnnouncement.objects.filter(is_public=True, is_moderated=True).update(
        moderation_status='APPROVED')
    CommunityAnnouncement.objects.filter(is_public=False, is_moderated=True).update(
        moderation_status='REJECTED')
    # is_moderated=False rows keep the PENDING default.

    CommunityEvent.objects.filter(is_public=True).update(moderation_status='APPROVED')
    # is_public=False events keep the PENDING default.


def backwards(apps, schema_editor):
    # The booleans were never removed, so nothing to restore.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('missions', '0011_communityannouncement_moderation_status_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
