"""Pre-launch access-control sweep: anonymous users stay out of every
dashboard, citizens see only their own cases, and staff stay inside their
own mission - asserted at the HTTP level, not just the helper level."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from missions.models import Complaint, Mission, UserProfile


def _role_user(username, role, mission=None):
    user = User.objects.create_user(username=username, password='pass12345')
    profile = user.profile
    profile.role = role
    profile.mission = mission
    profile.save()
    return user


class AnonymousAccessTests(TestCase):
    PROTECTED_URLS = [
        'citizen_dashboard', 'embassy_officer_dashboard', 'embassy_manager_dashboard',
        'ministry_reviewer_dashboard', 'ministry_admin_dashboard',
        'community_admin_dashboard', 'mission_events_manage', 'community_moderation',
        'ministry_operations', 'ministry_analytics', 'report_dashboard',
        'notification_history', 'invite_embassy_user',
    ]

    def test_anonymous_is_redirected_from_every_dashboard(self):
        for name in self.PROTECTED_URLS:
            response = self.client.get(reverse(name))
            self.assertEqual(
                response.status_code, 302,
                f"{name} answered {response.status_code} for an anonymous user",
            )
            self.assertNotEqual(response.status_code, 200)


class CitizenIsolationTests(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Embassy T', country='T', city='T')
        self.citizen_a = _role_user('citizen_a', UserProfile.Role.CITIZEN)
        self.citizen_b = _role_user('citizen_b', UserProfile.Role.CITIZEN)
        self.b_complaint = Complaint.objects.create(
            mission=self.mission, subject='Citizen B private case',
            message='Private content of B', rating=3, citizen_user=self.citizen_b,
        )

    def test_citizen_dashboard_shows_only_own_cases(self):
        self.client.login(username='citizen_a', password='pass12345')
        response = self.client.get(reverse('citizen_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Citizen B private case')

    def test_citizen_cannot_open_staff_case_workspace(self):
        self.client.login(username='citizen_a', password='pass12345')
        response = self.client.get(reverse('embassy_case_detail', args=[self.b_complaint.pk]))
        self.assertEqual(response.status_code, 302)


class StaffMissionScopingTests(TestCase):
    def setUp(self):
        self.mission_a = Mission.objects.create(name='Embassy A', country='A', city='A')
        self.mission_b = Mission.objects.create(name='Embassy B', country='B', city='B')
        self.officer_a = _role_user('officer_a', UserProfile.Role.EMBASSY_OFFICER, self.mission_a)
        self.b_case = Complaint.objects.create(
            mission=self.mission_b, subject='Mission B case', message='x', rating=3,
        )

    def test_staff_cannot_open_other_missions_case(self):
        self.client.login(username='officer_a', password='pass12345')
        response = self.client.get(reverse('embassy_case_detail', args=[self.b_case.pk]))
        self.assertEqual(response.status_code, 302)

    def test_staff_dashboard_never_lists_other_missions_case(self):
        self.client.login(username='officer_a', password='pass12345')
        response = self.client.get(reverse('embassy_officer_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Mission B case')
