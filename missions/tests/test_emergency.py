from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from missions.models import Complaint, Mission, UserProfile


def _emergency_payload(mission, **overrides):
    payload = {
        'mission': mission.pk,
        'emergency_type': Complaint.EmergencyType.DETENTION,
        'message': 'I have been detained at the airport and need consular help.',
        'full_name': 'Test Citizen',
        'phone': '+90 555 000 0000',
        'email': 'citizen@example.com',
    }
    payload.update(overrides)
    return payload


class EmergencySubmissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mission = Mission.objects.create(name='Test Embassy', country='Turkey', city='Ankara')

    def test_valid_emergency_stores_type_and_is_critical(self):
        response = self.client.post(reverse('submit_emergency'), _emergency_payload(self.mission))
        self.assertEqual(response.status_code, 302)
        complaint = Complaint.objects.get()
        self.assertEqual(complaint.emergency_type, Complaint.EmergencyType.DETENTION)
        self.assertEqual(complaint.priority, Complaint.Priority.CRITICAL)
        self.assertEqual(complaint.category, Complaint.Category.EMERGENCY)
        self.assertIn('Arrest or Detention', complaint.subject)

    def test_lost_passport_maps_to_lost_docs_category(self):
        self.client.post(
            reverse('submit_emergency'),
            _emergency_payload(self.mission, emergency_type=Complaint.EmergencyType.LOST_PASSPORT),
        )
        complaint = Complaint.objects.get()
        self.assertEqual(complaint.category, Complaint.Category.LOST_DOCS)
        self.assertEqual(complaint.emergency_type, Complaint.EmergencyType.LOST_PASSPORT)

    def test_empty_message_is_rejected_with_errors(self):
        # The form carries novalidate, so the server must be the gatekeeper.
        response = self.client.post(
            reverse('submit_emergency'), _emergency_payload(self.mission, message='')
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 0)
        self.assertTrue(response.context['form'].errors['message'])

    def test_arbitrary_emergency_type_is_rejected(self):
        # Regression: the old view wrote request.POST['category'] straight
        # into the model without validating against the choices.
        response = self.client.post(
            reverse('submit_emergency'),
            _emergency_payload(self.mission, emergency_type='HACKED_VALUE'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 0)
        self.assertTrue(response.context['form'].errors['emergency_type'])

    def test_missing_phone_is_rejected(self):
        response = self.client.post(
            reverse('submit_emergency'), _emergency_payload(self.mission, phone='')
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 0)
        self.assertTrue(response.context['form'].errors['phone'])


class EmergencyDashboardPriorityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mission = Mission.objects.create(name='Test Embassy', country='Turkey', city='Ankara')
        self.manager = User.objects.create_user(username='manager', password='managerpass123')
        profile = self.manager.profile
        profile.role = UserProfile.Role.EMBASSY_MANAGER
        profile.mission = self.mission
        profile.save()

        # Older critical emergency vs. newer routine complaint: the critical
        # one must still be listed first.
        self.routine = Complaint.objects.create(
            mission=self.mission, subject='Routine issue', message='Slow service',
            rating=3, priority=Complaint.Priority.LOW,
        )
        self.critical = Complaint.objects.create(
            mission=self.mission, subject='EMERGENCY REPORT - Detention', message='Detained.',
            rating=5, priority=Complaint.Priority.CRITICAL,
            emergency_type=Complaint.EmergencyType.DETENTION,
        )
        Complaint.objects.filter(pk=self.critical.pk).update(
            created_at=self.routine.created_at.__class__.fromisoformat('2020-01-01T00:00:00+00:00')
        )

    def test_critical_cases_listed_before_routine_ones(self):
        self.client.login(username='manager', password='managerpass123')
        response = self.client.get(reverse('embassy_manager_dashboard'))
        self.assertEqual(response.status_code, 200)
        listed = list(response.context['complaints'])
        self.assertEqual(listed[0].pk, self.critical.pk)

    def test_critical_strip_and_emergency_type_shown(self):
        self.client.login(username='manager', password='managerpass123')
        response = self.client.get(reverse('embassy_manager_dashboard'))
        self.assertContains(response, 'Active Emergency / Critical Cases')
        self.assertContains(response, 'Arrest or Detention')
        self.assertIn(self.critical, list(response.context['critical_cases']))
