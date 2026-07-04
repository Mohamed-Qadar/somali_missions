from datetime import date, time, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from appointments.models import AppointmentSlot
from missions.models import Complaint, Mission, MissionService, UserProfile
from missions.utils.permissions import MISSION_STAFF_GROUP


class PublicEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Mission.objects.create(name='Test Embassy', country='Testland', city='Testville')

    def test_mission_list_is_public(self):
        response = self.client.get('/api/v1/missions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_assistant_ask_is_public(self):
        response = self.client.post('/api/v1/assistant/ask/', {'question': 'test question'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('answer_text', response.data)

    def test_swagger_docs_available(self):
        response = self.client.get('/api/v1/docs/')
        self.assertEqual(response.status_code, 200)


class JWTAuthAndScopingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.mission_a = Mission.objects.create(name='Mission A', country='Country A', city='City A')
        self.mission_b = Mission.objects.create(name='Mission B', country='Country B', city='City B')

        self.staff_a = User.objects.create_user(username='staff_a', password='testpass123')
        self.mission_a.staff_users.add(self.staff_a)
        staff_group, _ = Group.objects.get_or_create(name=MISSION_STAFF_GROUP)
        self.staff_a.groups.add(staff_group)

        Complaint.objects.create(mission=self.mission_a, subject='A issue', message='msg', rating=3)
        Complaint.objects.create(mission=self.mission_b, subject='B issue', message='msg', rating=3)

    def _get_token(self, username, password):
        response = self.client.post('/api/v1/auth/token/', {'username': username, 'password': password})
        return response.data['access']

    def test_complaints_require_authentication(self):
        response = self.client.get('/api/v1/complaints/')
        self.assertEqual(response.status_code, 401)

    def test_jwt_token_obtain_and_use(self):
        token = self._get_token('staff_a', 'testpass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/complaints/')
        self.assertEqual(response.status_code, 200)

    def test_staff_only_sees_own_missions_complaints(self):
        token = self._get_token('staff_a', 'testpass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/complaints/')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['subject'], 'A issue')

    def test_ministry_admin_sees_all_complaints(self):
        ministry_admin = User.objects.create_user(username='ministry_admin', password='testpass123')
        ministry_admin.profile.role = UserProfile.Role.MINISTRY_ADMIN
        ministry_admin.profile.save()
        token = self._get_token('ministry_admin', 'testpass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/complaints/')
        self.assertEqual(response.data['count'], 2)


class AppointmentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.mission = Mission.objects.create(name='Test Embassy', country='Testland', city='Testville')
        self.service = MissionService.objects.create(mission=self.mission, name='Passport Renewal')
        self.slot = AppointmentSlot.objects.create(
            mission=self.mission, service=self.service, date=date.today() + timedelta(days=1),
            start_time=time(9, 0), end_time=time(9, 30), capacity=1,
        )

    def test_book_appointment_via_api_anonymous(self):
        response = self.client.post('/api/v1/appointments/', {
            'mission': self.mission.pk, 'service': self.service.pk, 'slot': self.slot.pk,
            'full_name': 'API Citizen', 'email': 'api@example.com', 'phone': '',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertTrue(response.data['qr_token'])
