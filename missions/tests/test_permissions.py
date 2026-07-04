from django.contrib.auth.models import User
from django.test import TestCase

from missions.models import Mission, UserProfile
from missions.utils.permissions import (
    MINISTRY_ADMIN_GROUP, MISSION_STAFF_GROUP, missions_for_user, user_can_manage_mission,
    user_is_ministry_admin,
)


class PermissionSyncSignalTests(TestCase):
    """UserProfile.role is the single source of truth; Django Groups and
    Mission.staff_users are auto-projected from it by the post_save signal."""

    def test_ministry_role_projects_to_group(self):
        user = User.objects.create_user('m1', password='x')
        user.profile.role = UserProfile.Role.MINISTRY_ADMIN
        user.profile.save()
        self.assertTrue(user.groups.filter(name=MINISTRY_ADMIN_GROUP).exists())
        self.assertTrue(user_is_ministry_admin(user))

    def test_changing_role_removes_stale_group(self):
        user = User.objects.create_user('m2', password='x')
        user.profile.role = UserProfile.Role.MINISTRY_ADMIN
        user.profile.save()
        self.assertTrue(user.groups.filter(name=MINISTRY_ADMIN_GROUP).exists())
        # Demote to citizen - the stale group membership must be removed.
        user.profile.role = UserProfile.Role.CITIZEN
        user.profile.save()
        self.assertFalse(user.groups.filter(name=MINISTRY_ADMIN_GROUP).exists())
        self.assertFalse(user_is_ministry_admin(user))

    def test_embassy_role_projects_to_staff_group_and_mission(self):
        mission = Mission.objects.create(name='M', country='C', city='Ct')
        user = User.objects.create_user('e1', password='x')
        user.profile.role = UserProfile.Role.EMBASSY_OFFICER
        user.profile.mission = mission
        user.profile.save()
        self.assertTrue(user.groups.filter(name=MISSION_STAFF_GROUP).exists())
        self.assertTrue(mission.staff_users.filter(pk=user.pk).exists())
        self.assertTrue(user_can_manage_mission(user, mission))
        self.assertEqual(list(missions_for_user(user)), [mission])

    def test_embassy_staff_cannot_manage_other_mission(self):
        mission_a = Mission.objects.create(name='A', country='A', city='A')
        mission_b = Mission.objects.create(name='B', country='B', city='B')
        user = User.objects.create_user('e2', password='x')
        user.profile.role = UserProfile.Role.EMBASSY_OFFICER
        user.profile.mission = mission_a
        user.profile.save()
        self.assertFalse(user_can_manage_mission(user, mission_b))

    def test_sync_permissions_command_reconciles_existing(self):
        from django.core.management import call_command
        user = User.objects.create_user('m3', password='x')
        # Force a drifted state: role says ministry admin, but strip the group.
        user.profile.role = UserProfile.Role.MINISTRY_ADMIN
        user.profile.save()
        user.groups.clear()
        self.assertFalse(user.groups.filter(name=MINISTRY_ADMIN_GROUP).exists())
        call_command('sync_permissions')
        self.assertTrue(user.groups.filter(name=MINISTRY_ADMIN_GROUP).exists())
