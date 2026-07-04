from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from missions.models import CommunityGroup, CommunityStatus, Mission, Complaint, StudentAssociation


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.mission = Mission.objects.create(name='Test Embassy', country='Turkey', city='Ankara')
        self.user = User.objects.create_user(username='testadmin', password='testpass123')

    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_complaint_submission_with_captcha(self):
        session = self.client.session
        session['captcha_num1'] = 2
        session['captcha_num2'] = 3
        session.save()
        response = self.client.post(reverse('mission_detail', args=[self.mission.pk]), {
            'subject': 'Visa delay',
            'message': 'Long wait time at consulate',
            'rating': 2,
            'category': 'DELAY',
            'captcha_answer': 5,
            'website': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Complaint.objects.count(), 1)
        self.assertEqual(len(Complaint.objects.first().tracking_code), 8)

    def test_track_complaint(self):
        complaint = Complaint.objects.create(
            mission=self.mission,
            subject='Track me',
            message='Testing track page',
            rating=3,
        )
        response = self.client.get(reverse('track'), {'tracking_code': complaint.tracking_code})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, complaint.tracking_code)

    def test_reports_requires_login(self):
        response = self.client.get(reverse('report_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.client.login(username='testadmin', password='testpass123')
        response = self.client.get(reverse('report_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_community_directory_only_shows_verified_groups(self):
        CommunityGroup.objects.create(
            name='Verified Somali Community',
            country='Turkey',
            city='Ankara',
            status=CommunityStatus.VERIFIED,
        )
        CommunityGroup.objects.create(
            name='Pending Somali Community',
            country='Turkey',
            city='Ankara',
            status=CommunityStatus.PENDING,
        )

        response = self.client.get(reverse('community_directory'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verified Somali Community')
        self.assertNotContains(response, 'Pending Somali Community')

    def test_mission_detail_links_nearby_student_association(self):
        StudentAssociation.objects.create(
            name='Ankara Somali Students',
            country='Turkey',
            city='Ankara',
            university_name='Ankara University',
            status=CommunityStatus.VERIFIED,
        )

        response = self.client.get(reverse('mission_detail', args=[self.mission.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ankara Somali Students')
