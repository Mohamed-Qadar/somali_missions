from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from missions.models import Mission
from missions.utils.permissions import MISSION_STAFF_GROUP

from .models import QueueTicket


class QueueJoinTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mission = Mission.objects.create(name='Test Embassy', country='Testland', city='Testville')

    def test_sequential_ticket_numbers(self):
        for i in range(3):
            self.client.post(reverse('join_queue'), {'mission': self.mission.pk, 'full_name': f'Citizen {i}'})
        numbers = list(QueueTicket.objects.order_by('ticket_number').values_list('ticket_number', flat=True))
        self.assertEqual(numbers, [1, 2, 3])

    def test_ticket_status_page(self):
        self.client.post(reverse('join_queue'), {'mission': self.mission.pk, 'full_name': 'Citizen'})
        ticket = QueueTicket.objects.first()
        response = self.client.get(reverse('queue_ticket_status', args=[ticket.pk]))
        self.assertEqual(response.status_code, 200)

    def test_display_screen_loads(self):
        response = self.client.get(reverse('queue_display', args=[self.mission.pk]))
        self.assertEqual(response.status_code, 200)


class QueueStaffActionTests(TestCase):
    def setUp(self):
        self.mission_a = Mission.objects.create(name='Mission A', country='Country A', city='City A')
        self.mission_b = Mission.objects.create(name='Mission B', country='Country B', city='City B')

        self.staff_a = User.objects.create_user(username='staff_a', password='testpass123')
        self.mission_a.staff_users.add(self.staff_a)
        staff_group, _ = Group.objects.get_or_create(name=MISSION_STAFF_GROUP)
        self.staff_a.groups.add(staff_group)

        today = timezone.now().date()
        self.ticket_a = QueueTicket.objects.create(mission=self.mission_a, date=today, ticket_number=1)
        self.ticket_b = QueueTicket.objects.create(mission=self.mission_b, date=today, ticket_number=1)

    def test_call_next_serves_own_missions_ticket(self):
        client = Client()
        client.login(username='staff_a', password='testpass123')
        client.post(reverse('queue_call_next', args=[self.mission_a.pk]))
        self.ticket_a.refresh_from_db()
        self.assertEqual(self.ticket_a.status, QueueTicket.Status.SERVING)

    def test_staff_cannot_call_next_for_other_mission(self):
        client = Client()
        client.login(username='staff_a', password='testpass123')
        response = client.post(reverse('queue_call_next', args=[self.mission_b.pk]))
        self.assertEqual(response.status_code, 302)
        self.ticket_b.refresh_from_db()
        self.assertEqual(self.ticket_b.status, QueueTicket.Status.WAITING)

    def test_staff_cannot_skip_other_missions_ticket(self):
        client = Client()
        client.login(username='staff_a', password='testpass123')
        client.post(reverse('queue_ticket_action', args=[self.ticket_b.pk, 'skip']))
        self.ticket_b.refresh_from_db()
        self.assertEqual(self.ticket_b.status, QueueTicket.Status.WAITING)

    def test_staff_can_skip_own_missions_ticket(self):
        client = Client()
        client.login(username='staff_a', password='testpass123')
        client.post(reverse('queue_ticket_action', args=[self.ticket_a.pk, 'skip']))
        self.ticket_a.refresh_from_db()
        self.assertEqual(self.ticket_a.status, QueueTicket.Status.SKIPPED)
