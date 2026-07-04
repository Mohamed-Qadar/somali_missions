from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from missions.models import UserProfile

from .channels import notify
from .models import Notification, NotificationDeliveryLog


class NotifyHelperTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='citizen', password='testpass123', email='citizen@example.com')

    def test_notify_creates_in_app_notification(self):
        notify(self.user, 'Test Title', 'Test body')
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()
        self.assertEqual(notification.title, 'Test Title')
        self.assertFalse(notification.is_read)

    def test_notify_with_email_channel_sends_real_email(self):
        mail.outbox = []
        notify(self.user, 'Email Test', 'Body', channels=['email'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['citizen@example.com'])
        delivery = NotificationDeliveryLog.objects.get(channel=NotificationDeliveryLog.Channel.EMAIL)
        self.assertTrue(delivery.delivered)

    def test_notify_with_sms_channel_is_honest_about_no_provider(self):
        notify(self.user, 'SMS Test', 'Body', channels=['sms'])
        delivery = NotificationDeliveryLog.objects.get(channel=NotificationDeliveryLog.Channel.SMS)
        self.assertFalse(delivery.delivered)


class NotificationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='citizen', password='testpass123')

    def test_history_requires_login(self):
        response = self.client.get(reverse('notification_history'))
        self.assertEqual(response.status_code, 302)

    def test_mark_read(self):
        notification = notify(self.user, 'Title', 'Body')
        self.client.login(username='citizen', password='testpass123')
        self.client.post(reverse('mark_notification_read', args=[notification.pk]))
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_cannot_mark_another_users_notification_read(self):
        other_user = User.objects.create_user(username='other', password='testpass123')
        notification = notify(other_user, 'Title', 'Body')
        self.client.login(username='citizen', password='testpass123')
        response = self.client.post(reverse('mark_notification_read', args=[notification.pk]))
        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)


class EmergencyBroadcastTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ministry_admin = User.objects.create_user(username='ministry_admin', password='testpass123')
        self.ministry_admin.profile.role = UserProfile.Role.MINISTRY_ADMIN
        self.ministry_admin.profile.save()

        self.citizen = User.objects.create_user(username='citizen', password='testpass123')
        self.citizen.profile.role = UserProfile.Role.CITIZEN
        self.citizen.profile.save()

    def test_non_ministry_user_is_denied(self):
        self.client.login(username='citizen', password='testpass123')
        response = self.client.get(reverse('emergency_broadcast'))
        self.assertEqual(response.status_code, 302)

    def test_ministry_admin_can_broadcast_to_all_citizens(self):
        self.client.login(username='ministry_admin', password='testpass123')
        response = self.client.post(reverse('emergency_broadcast'), {
            'audience': 'all_citizens', 'title': 'Alert', 'body': 'Test alert body',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(recipient=self.citizen).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.ministry_admin).count(), 0)
