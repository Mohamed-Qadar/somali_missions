from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from missions.models import Mission, MissionService

from .models import Appointment, AppointmentSlot


class AppointmentBookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mission = Mission.objects.create(name='Test Embassy', country='Testland', city='Testville')
        self.service = MissionService.objects.create(
            mission=self.mission, name='Passport Renewal', service_type=MissionService.ServiceType.PASSPORT_RENEWAL,
        )
        self.tomorrow = date.today() + timedelta(days=1)
        self.slot = AppointmentSlot.objects.create(
            mission=self.mission, service=self.service, date=self.tomorrow,
            start_time=time(9, 0), end_time=time(9, 30), capacity=1,
        )

    def _book(self, full_name='Citizen'):
        return self.client.post(
            f"{reverse('book_appointment')}?mission={self.mission.pk}&service={self.service.pk}",
            {'slot': self.slot.pk, 'full_name': full_name, 'email': 'citizen@example.com', 'phone': ''},
        )

    def test_booking_page_loads(self):
        response = self.client.get(reverse('book_appointment'))
        self.assertEqual(response.status_code, 200)

    def test_required_documents_shown_before_booking(self):
        from missions.models import RequiredDocument

        RequiredDocument.objects.create(
            service=self.service, name='Original passport', is_required=True,
        )
        RequiredDocument.objects.create(
            service=self.service, name='Old photo', is_required=False,
        )
        response = self.client.get(
            f"{reverse('book_appointment')}?mission={self.mission.pk}&service={self.service.pk}"
        )
        self.assertContains(response, 'Original passport')
        self.assertContains(response, 'Old photo')
        self.assertContains(response, 'Documents to bring for')

    def test_first_booking_is_pending(self):
        response = self._book('First Citizen')
        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get(full_name='First Citizen')
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertEqual(len(appointment.qr_token), 10)

    def test_no_double_booking_second_request_is_waitlisted(self):
        self._book('First Citizen')
        self._book('Second Citizen')
        first = Appointment.objects.get(full_name='First Citizen')
        second = Appointment.objects.get(full_name='Second Citizen')
        self.assertEqual(first.status, Appointment.Status.PENDING)
        self.assertEqual(second.status, Appointment.Status.WAITLISTED)
        self.assertEqual(self.slot.booked_count, 1)

    def test_confirmation_page_and_qr_image(self):
        self._book()
        appointment = Appointment.objects.first()
        response = self.client.get(reverse('appointment_confirmation', args=[appointment.qr_token]))
        self.assertEqual(response.status_code, 200)
        qr_response = self.client.get(reverse('appointment_qr_image', args=[appointment.qr_token]))
        self.assertEqual(qr_response.status_code, 200)
        self.assertEqual(qr_response['Content-Type'], 'image/png')


class AppointmentStaffScopingTests(TestCase):
    """Mirrors the same mission-scoping guarantee complaints already have:
    staff of one mission must not see or act on another mission's appointments."""

    def setUp(self):
        self.mission_a = Mission.objects.create(name='Mission A', country='Country A', city='City A')
        self.mission_b = Mission.objects.create(name='Mission B', country='Country B', city='City B')
        self.service_a = MissionService.objects.create(mission=self.mission_a, name='Service A')

        self.staff_a = User.objects.create_user(username='staff_a', password='testpass123')
        self.staff_a.profile.mission = self.mission_a
        self.staff_a.profile.save()
        self.mission_a.staff_users.add(self.staff_a)

        from missions.utils.permissions import MISSION_STAFF_GROUP
        from django.contrib.auth.models import Group
        staff_group, _ = Group.objects.get_or_create(name=MISSION_STAFF_GROUP)
        self.staff_a.groups.add(staff_group)

        self.appointment_b = Appointment.objects.create(
            mission=self.mission_b, service=self.service_a, full_name='Someone Else', status=Appointment.Status.PENDING,
        )

    def test_staff_cannot_act_on_other_missions_appointment(self):
        client = Client()
        client.login(username='staff_a', password='testpass123')
        response = client.post(reverse('appointment_action', args=[self.appointment_b.pk]), {'action': 'approve'})
        self.assertEqual(response.status_code, 302)
        self.appointment_b.refresh_from_db()
        self.assertEqual(self.appointment_b.status, Appointment.Status.PENDING)

    def test_staff_can_approve_own_missions_appointment(self):
        appointment_a = Appointment.objects.create(
            mission=self.mission_a, service=self.service_a, full_name='My Citizen', status=Appointment.Status.PENDING,
        )
        client = Client()
        client.login(username='staff_a', password='testpass123')
        client.post(reverse('appointment_action', args=[appointment_a.pk]), {'action': 'approve'})
        appointment_a.refresh_from_db()
        self.assertEqual(appointment_a.status, Appointment.Status.CONFIRMED)
