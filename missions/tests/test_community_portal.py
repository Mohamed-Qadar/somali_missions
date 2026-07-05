import io
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from missions.forms import CommunityProfileForm
from missions.models import (
    AbuseReport, CommunityAnnouncement, CommunityGroup, CommunityRepresentative,
    CommunityStatus, CommunityVerificationRequest, Mission, MissionEvent,
    ModerationStatus, UserProfile,
)


def _png_bytes(pad_to=0):
    """A real (tiny) PNG; optionally padded past `pad_to` bytes after IEND -
    still a valid image for Pillow, but oversized for the upload validator."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new('RGB', (4, 4), 'blue').save(buf, format='PNG')
    data = buf.getvalue()
    if pad_to and len(data) < pad_to:
        data += b'\x00' * (pad_to - len(data))
    return data


def _make_role_user(username, role, mission=None):
    user = User.objects.create_user(username=username, password='pass12345')
    profile = user.profile
    profile.role = role
    profile.mission = mission
    profile.save()
    return user


REGISTRATION_DATA = {
    'org_type': 'community',
    'org_name': 'Somali Community of Testville',
    'country': 'Testland',
    'city': 'Testville',
    'description': 'We support newly arrived Somali families.',
    'contact_email': 'org@example.com',
    'rep_full_name': 'Rep Person',
    'rep_title': 'Chairperson',
    'username': 'rep_test',
    'email': 'rep@example.com',
    'password': 'secret123',
    'confirm_password': 'secret123',
}


class CommunityRegistrationTests(TestCase):
    def test_registration_creates_pending_org_rep_and_verification_request(self):
        response = self.client.post(reverse('community_register'), REGISTRATION_DATA)
        self.assertEqual(response.status_code, 200)  # verify_pending page
        user = User.objects.get(username='rep_test')
        self.assertEqual(user.profile.role, UserProfile.Role.COMMUNITY_REP)
        org = CommunityGroup.objects.get(name='Somali Community of Testville')
        self.assertEqual(org.status, CommunityStatus.PENDING)
        self.assertEqual(org.created_by, user)
        rep = CommunityRepresentative.objects.get(user=user, community_group=org)
        self.assertTrue(rep.is_approved)
        self.assertTrue(CommunityVerificationRequest.objects.filter(
            community_group=org, decision=CommunityVerificationRequest.Decision.PENDING).exists())

    def test_pending_org_is_not_publicly_listed(self):
        self.client.post(reverse('community_register'), REGISTRATION_DATA)
        response = self.client.get(reverse('community_directory'))
        self.assertNotContains(response, 'Somali Community of Testville')
        org = CommunityGroup.objects.get()
        response = self.client.get(reverse('community_group_detail', args=[org.pk]))
        self.assertEqual(response.status_code, 404)

    def test_rejected_and_suspended_orgs_are_not_public(self):
        for status in (CommunityStatus.REJECTED, CommunityStatus.SUSPENDED):
            org = CommunityGroup.objects.create(
                name=f'{status} Org', country='Testland', city='Testville', status=status)
            listing = self.client.get(reverse('community_directory'))
            self.assertNotContains(listing, f'{status} Org')
            detail = self.client.get(reverse('community_group_detail', args=[org.pk]))
            self.assertEqual(detail.status_code, 404)

    def test_student_registration_requires_university(self):
        data = dict(REGISTRATION_DATA, org_type='student', university_name='')
        response = self.client.post(reverse('community_register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='rep_test').exists())
        self.assertTrue(response.context['form'].errors['university_name'])

    def test_rep_lands_on_portal_after_login(self):
        self.client.post(reverse('community_register'), REGISTRATION_DATA)
        logged_in = self.client.login(username='rep_test', password='secret123')
        self.assertTrue(logged_in)
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('community_admin_dashboard'))


class CommunityPortalTests(TestCase):
    def setUp(self):
        self.org = CommunityGroup.objects.create(
            name='Org A', country='Testland', city='Testville', status=CommunityStatus.VERIFIED)
        self.other_org = CommunityGroup.objects.create(
            name='Org B', country='Testland', city='Otherville',
            status=CommunityStatus.VERIFIED, description='untouched')
        self.rep = _make_role_user('rep_a', UserProfile.Role.COMMUNITY_REP)
        CommunityRepresentative.objects.create(
            user=self.rep, community_group=self.org, is_approved=True)
        self.client.login(username='rep_a', password='pass12345')

    def _portal(self):
        return f"{reverse('community_admin_dashboard')}?type=community&id={self.org.pk}"

    def test_rep_can_edit_own_profile(self):
        response = self.client.post(self._portal(), {
            'action': 'profile',
            'description': 'Updated description',
            'languages_spoken': 'Somali, English',
            'service_categories': ['TRANSLATION', 'LEGAL'],
            'emergency_support_available': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.org.refresh_from_db()
        self.assertEqual(self.org.description, 'Updated description')
        self.assertEqual(self.org.languages_spoken, 'Somali, English')
        self.assertEqual(self.org.service_categories, ['TRANSLATION', 'LEGAL'])
        self.assertTrue(self.org.emergency_support_available)
        self.assertEqual(self.org.updated_by, self.rep)

    def test_rep_cannot_edit_someone_elses_org(self):
        # Selecting another org's id falls back to the rep's own targets.
        url = f"{reverse('community_admin_dashboard')}?type=community&id={self.other_org.pk}"
        self.client.post(url, {'action': 'profile', 'description': 'HACKED'})
        self.other_org.refresh_from_db()
        self.assertEqual(self.other_org.description, 'untouched')

    def test_community_event_hidden_until_approved(self):
        from missions.models import CommunityEvent
        from django.utils import timezone as tz
        event = CommunityEvent.objects.create(
            community_group=self.org, title='Community Iftar Night',
            description='x', starts_at=tz.now(), created_by=self.rep)
        for status in (ModerationStatus.PENDING, ModerationStatus.REJECTED, ModerationStatus.ARCHIVED):
            event.apply_moderation(status)
            public = self.client.get(reverse('community_group_detail', args=[self.org.pk]))
            self.assertNotContains(public, 'Community Iftar Night')
        event.apply_moderation(ModerationStatus.APPROVED)
        public = self.client.get(reverse('community_group_detail', args=[self.org.pk]))
        self.assertContains(public, 'Community Iftar Night')

    def test_announcement_needs_moderation_before_public(self):
        self.client.post(self._portal(), {
            'action': 'announcement',
            'title': 'Free legal clinic',
            'announcement_type': 'GENERAL',
            'body': 'Every Saturday at the community office.',
        })
        item = CommunityAnnouncement.objects.get()
        self.assertEqual(item.moderation_status, ModerationStatus.PENDING)
        public = self.client.get(reverse('community_group_detail', args=[self.org.pk]))
        self.assertNotContains(public, 'Free legal clinic')

        item.apply_moderation(ModerationStatus.APPROVED)
        public = self.client.get(reverse('community_group_detail', args=[self.org.pk]))
        self.assertContains(public, 'Free legal clinic')


class CommunityProfileUploadTests(TestCase):
    def test_oversized_logo_rejected(self):
        big = SimpleUploadedFile('logo.png', _png_bytes(pad_to=2 * 1024 * 1024 + 1), 'image/png')
        form = CommunityProfileForm(data={}, files={'logo': big})
        self.assertFalse(form.is_valid())
        self.assertIn('logo', form.errors)

    def test_wrong_extension_rejected(self):
        gif_named = SimpleUploadedFile('logo.gif', _png_bytes(), 'image/gif')
        form = CommunityProfileForm(data={}, files={'logo': gif_named})
        self.assertFalse(form.is_valid())
        self.assertIn('logo', form.errors)

    def test_valid_logo_accepted(self):
        ok = SimpleUploadedFile('logo.png', _png_bytes(), 'image/png')
        form = CommunityProfileForm(data={}, files={'logo': ok})
        self.assertTrue(form.is_valid(), form.errors)


class ModerationTests(TestCase):
    def setUp(self):
        self.ministry = _make_role_user('ministry', UserProfile.Role.MINISTRY_ADMIN)
        self.org = CommunityGroup.objects.create(
            name='Pending Org', country='Testland', city='Testville')
        self.vr = CommunityVerificationRequest.objects.create(community_group=self.org)

    def test_non_ministry_cannot_open_moderation(self):
        _make_role_user('officer_x', UserProfile.Role.EMBASSY_OFFICER)
        self.client.login(username='officer_x', password='pass12345')
        response = self.client.get(reverse('community_moderation'))
        self.assertEqual(response.status_code, 302)

    def test_verification_approval_makes_org_public(self):
        self.client.login(username='ministry', password='pass12345')
        response = self.client.post(reverse('community_moderation'), {
            'action': 'verify_org', 'request_id': self.vr.pk, 'decision': 'approve',
        })
        self.assertEqual(response.status_code, 302)
        self.org.refresh_from_db()
        self.assertEqual(self.org.status, CommunityStatus.VERIFIED)
        listing = self.client.get(reverse('community_directory'))
        self.assertContains(listing, 'Pending Org')

    def test_announcement_moderation_approve(self):
        item = CommunityAnnouncement.objects.create(
            community_group=self.org, title='Hello', body='World')
        self.client.login(username='ministry', password='pass12345')
        self.client.post(reverse('community_moderation'), {
            'action': 'moderate_announcement', 'item_id': item.pk, 'decision': 'approve',
        })
        item.refresh_from_db()
        self.assertEqual(item.moderation_status, ModerationStatus.APPROVED)
        self.assertTrue(item.is_public)
        self.assertEqual(item.reviewed_by, self.ministry)

    def test_abuse_report_handling(self):
        report = AbuseReport.objects.create(community_group=self.org, details='Fake org details')
        self.client.login(username='ministry', password='pass12345')
        self.client.post(reverse('community_moderation'), {
            'action': 'handle_abuse', 'report_id': report.pk, 'resolution': 'DISMISSED',
        })
        report.refresh_from_db()
        self.assertEqual(report.status, AbuseReport.Status.DISMISSED)
        self.assertEqual(report.handled_by, self.ministry)


class MissionEventTests(TestCase):
    def setUp(self):
        self.mission_a = Mission.objects.create(name='Embassy A', country='Aland', city='Acity')
        self.mission_b = Mission.objects.create(name='Embassy B', country='Bland', city='Bcity')
        self.manager_a = _make_role_user('manager_a', UserProfile.Role.EMBASSY_MANAGER, self.mission_a)
        self.starts = timezone.now() + timedelta(days=5)

    def _event_data(self, mission):
        return {
            'action': 'create',
            'mission': mission.pk,
            'title': 'Passport Day',
            'event_type': MissionEvent.EventType.PASSPORT_DAY,
            'description': 'Bring your documents for same-day processing.',
            'starts_at': self.starts.strftime('%Y-%m-%dT%H:%M'),
            'capacity': 80,
        }

    def test_staff_creates_event_for_own_mission(self):
        self.client.login(username='manager_a', password='pass12345')
        response = self.client.post(reverse('mission_events_manage'), self._event_data(self.mission_a))
        self.assertEqual(response.status_code, 302)
        event = MissionEvent.objects.get()
        self.assertEqual(event.mission, self.mission_a)
        self.assertEqual(event.moderation_status, ModerationStatus.APPROVED)
        self.assertEqual(event.country, 'Aland')      # defaulted from mission
        self.assertEqual(event.organizer, 'Embassy A')
        self.assertEqual(event.created_by, self.manager_a)

    def test_staff_cannot_create_event_for_other_mission(self):
        self.client.login(username='manager_a', password='pass12345')
        self.client.post(reverse('mission_events_manage'), self._event_data(self.mission_b))
        self.assertEqual(MissionEvent.objects.count(), 0)

    def test_staff_cannot_moderate_other_missions_event(self):
        event = MissionEvent.objects.create(
            mission=self.mission_b, title='B event', event_type='PASSPORT_DAY',
            description='x', starts_at=self.starts, moderation_status=ModerationStatus.APPROVED)
        self.client.login(username='manager_a', password='pass12345')
        self.client.post(reverse('mission_events_manage'), {'action': 'archive', 'event_id': event.pk})
        event.refresh_from_db()
        self.assertEqual(event.moderation_status, ModerationStatus.APPROVED)

    def test_citizen_cannot_open_events_manage(self):
        _make_role_user('citizen_c', UserProfile.Role.CITIZEN)
        self.client.login(username='citizen_c', password='pass12345')
        response = self.client.get(reverse('mission_events_manage'))
        self.assertEqual(response.status_code, 302)

    def test_public_events_page_shows_only_approved_upcoming(self):
        approved = MissionEvent.objects.create(
            mission=self.mission_a, title='Approved Day', event_type='PASSPORT_DAY',
            description='x', starts_at=self.starts, moderation_status=ModerationStatus.APPROVED)
        for status, title in [
            (ModerationStatus.PENDING, 'Pending Day'),
            (ModerationStatus.REJECTED, 'Rejected Day'),
            (ModerationStatus.ARCHIVED, 'Archived Day'),
        ]:
            MissionEvent.objects.create(
                mission=self.mission_a, title=title, event_type='PASSPORT_DAY',
                description='x', starts_at=self.starts, moderation_status=status)
        response = self.client.get(reverse('events_public'))
        self.assertContains(response, 'Approved Day')
        self.assertNotContains(response, 'Pending Day')
        self.assertNotContains(response, 'Rejected Day')
        self.assertNotContains(response, 'Archived Day')
        # mission page shows the approved event too
        detail = self.client.get(reverse('mission_detail', args=[self.mission_a.pk]))
        self.assertContains(detail, 'Approved Day')
        self.assertEqual(approved.moderation_status, ModerationStatus.APPROVED)

    def test_events_page_country_filter(self):
        MissionEvent.objects.create(
            mission=self.mission_a, title='A-land Day', event_type='PASSPORT_DAY',
            description='x', starts_at=self.starts, moderation_status=ModerationStatus.APPROVED)
        MissionEvent.objects.create(
            mission=self.mission_b, title='B-land Day', event_type='PASSPORT_DAY',
            description='x', starts_at=self.starts, moderation_status=ModerationStatus.APPROVED)
        response = self.client.get(reverse('events_public'), {'country': 'Aland'})
        self.assertContains(response, 'A-land Day')
        self.assertNotContains(response, 'B-land Day')


class AbuseReportPublicTests(TestCase):
    def setUp(self):
        self.org = CommunityGroup.objects.create(
            name='Verified Org', country='Testland', city='Testville',
            status=CommunityStatus.VERIFIED)

    def test_public_can_report_verified_org(self):
        url = f"{reverse('report_abuse')}?type=community&id={self.org.pk}"
        response = self.client.post(url, {
            'reason': 'SCAM',
            'details': 'This organization is charging citizens for free services.',
        })
        self.assertEqual(response.status_code, 302)
        report = AbuseReport.objects.get()
        self.assertEqual(report.community_group, self.org)
        self.assertEqual(report.reason, AbuseReport.Reason.SCAM)

    def test_cannot_report_hidden_org(self):
        hidden = CommunityGroup.objects.create(
            name='Hidden Org', country='X', city='Y', status=CommunityStatus.PENDING)
        url = f"{reverse('report_abuse')}?type=community&id={hidden.pk}"
        response = self.client.get(url)
        self.assertTrue(response.context['not_found'])

    def test_short_details_rejected(self):
        url = f"{reverse('report_abuse')}?type=community&id={self.org.pk}"
        response = self.client.post(url, {'reason': 'SPAM', 'details': 'bad'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AbuseReport.objects.count(), 0)
