from io import StringIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from appointments.models import Appointment
from missions.models import Mission, MissionService, RequiredDocument, UserProfile

from .models import ConsularApplication


def _citizen(username):
    user = User.objects.create_user(username=username, password='pass12345')
    # profile is auto-created as CITIZEN by the missions post_save signal.
    return user


def _staff(username, mission, role=UserProfile.Role.EMBASSY_OFFICER):
    user = User.objects.create_user(username=username, password='pass12345')
    profile = user.profile
    profile.role = role
    profile.mission = mission
    profile.save()  # sync_user_permissions runs on save
    return user


def _pdf(name='doc.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type='application/pdf')


class ConsularSetup(TestCase):
    def setUp(self):
        self.mission_a = Mission.objects.create(name='Embassy A', country='Aland', city='Aville')
        self.mission_b = Mission.objects.create(name='Embassy B', country='Bland', city='Bville')
        self.service_a = MissionService.objects.create(
            mission=self.mission_a, name='Passport Renewal',
            service_type=MissionService.ServiceType.PASSPORT_RENEWAL,
            appointment_required=True, is_active=True,
        )
        RequiredDocument.objects.create(service=self.service_a, name='Old passport', sort_order=1)
        self.service_b = MissionService.objects.create(
            mission=self.mission_b, name='Birth Certificate',
            service_type=MissionService.ServiceType.BIRTH_REGISTRATION, is_active=True,
        )
        self.citizen = _citizen('citizen1')
        self.officer_a = _staff('officer_a', self.mission_a)
        self.officer_b = _staff('officer_b', self.mission_b)


class LandingAndCatalogTests(ConsularSetup):
    def test_services_landing_is_public(self):
        resp = self.client.get(reverse('consular_services'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Passport Services')

    def test_apply_requires_login(self):
        resp = self.client.get(reverse('consular_apply'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.url)

    def test_service_list_scoped_to_selected_mission(self):
        self.client.login(username='citizen1', password='pass12345')
        resp = self.client.get(reverse('consular_apply'), {'mission': self.mission_a.pk})
        self.assertContains(resp, 'Passport Renewal')
        self.assertNotContains(resp, 'Birth Certificate')

    def test_category_filters_service_list(self):
        self.client.login(username='citizen1', password='pass12345')
        # civil category should not include the passport service of mission A
        resp = self.client.get(reverse('consular_apply'),
                               {'mission': self.mission_a.pk, 'category': 'civil'})
        self.assertNotContains(resp, 'Passport Renewal')

    def test_apply_form_returns_services_for_mission_with_seeded_services(self):
        """A mission that has active services must expose them in the apply
        form's service dropdown (the exact end-to-end guarantee that was broken)."""
        self.client.login(username='citizen1', password='pass12345')
        resp = self.client.get(reverse('consular_apply'), {'mission': self.mission_a.pk})
        self.assertEqual(resp.status_code, 200)
        # The service is rendered as a selectable <option value="pk"> in the dropdown.
        self.assertContains(resp, f'<option value="{self.service_a.pk}"')
        self.assertContains(resp, 'Passport Renewal')
        self.assertNotContains(resp, 'This service is currently unavailable')

    def test_apply_page_has_no_csp_blocked_inline_handlers(self):
        """Regression guard for the empty-dropdown bug: inline event-handler
        attributes are blocked by the site CSP, so the selects must drive their
        auto-submit through data-autosubmit + a nonced script instead."""
        self.client.login(username='citizen1', password='pass12345')
        resp = self.client.get(reverse('consular_apply'), {'mission': self.mission_a.pk})
        content = resp.content.decode()
        self.assertNotIn('onchange=', content)
        self.assertIn('data-autosubmit', content)
        # A no-JS fallback submit control must exist so the form is never a dead end.
        self.assertIn('type="submit"', content)

    def test_unavailable_message_when_mission_has_no_matching_services(self):
        """A mission with no service in the chosen category shows a professional
        message, never a silently empty dropdown."""
        self.client.login(username='citizen1', password='pass12345')
        # mission_a only has a PASSPORT service; ask for the 'civil' category.
        resp = self.client.get(reverse('consular_apply'),
                               {'mission': self.mission_a.pk, 'category': 'civil'})
        self.assertContains(resp, 'This service is currently unavailable')


class ApplicationCreationTests(ConsularSetup):
    def _submit(self, service):
        self.client.login(username='citizen1', password='pass12345')
        return self.client.post(reverse('consular_apply'), {
            'mission': service.mission_id,
            'service': service.pk,
            'submit_application': '1',
            'full_name': 'Ayaan Ali',
            'email': 'ayaan@example.com',
            'phone': '+100000',
            'notes': 'Please help.',
            'documents': _pdf(),
        })

    def test_citizen_creates_application_with_document(self):
        resp = self._submit(self.service_a)
        app = ConsularApplication.objects.get()
        self.assertRedirects(resp, reverse('consular_application_detail', args=[app.reference_code]))
        self.assertEqual(app.mission, self.mission_a)
        self.assertEqual(app.service, self.service_a)
        self.assertEqual(app.citizen_user, self.citizen)
        self.assertEqual(app.status, ConsularApplication.Status.SUBMITTED)
        self.assertIsNotNone(app.submitted_at)
        self.assertEqual(app.documents.count(), 1)
        # status history recorded
        self.assertEqual(app.status_history.count(), 1)

    def test_reference_code_is_unique_and_prefixed(self):
        self._submit(self.service_a)
        self.client.post(reverse('consular_apply'), {
            'mission': self.service_a.mission_id, 'service': self.service_a.pk,
            'submit_application': '1', 'full_name': 'B', 'email': 'b@example.com',
        })
        codes = list(ConsularApplication.objects.values_list('reference_code', flat=True))
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(c.startswith('CS-') for c in codes))

    def test_contact_required(self):
        self.client.login(username='citizen1', password='pass12345')
        resp = self.client.post(reverse('consular_apply'), {
            'mission': self.service_a.mission_id, 'service': self.service_a.pk,
            'submit_application': '1', 'full_name': 'No Contact',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ConsularApplication.objects.count(), 0)


class CitizenTrackingTests(ConsularSetup):
    def setUp(self):
        super().setUp()
        self.app = ConsularApplication.objects.create(
            mission=self.mission_a, service=self.service_a, citizen_user=self.citizen,
            full_name='Ayaan', email='a@example.com',
        )

    def test_my_applications_lists_only_own(self):
        other = _citizen('citizen2')
        ConsularApplication.objects.create(
            mission=self.mission_b, service=self.service_b, citizen_user=other,
            full_name='Other', email='o@example.com',
        )
        self.client.login(username='citizen1', password='pass12345')
        resp = self.client.get(reverse('my_consular_applications'))
        self.assertContains(resp, self.app.reference_code)
        self.assertNotContains(resp, 'Birth Certificate')

    def test_citizen_cannot_view_another_citizens_application(self):
        _citizen('citizen2')
        self.client.login(username='citizen2', password='pass12345')
        resp = self.client.get(reverse('consular_application_detail', args=[self.app.reference_code]))
        self.assertEqual(resp.status_code, 302)

    def test_citizen_can_cancel_open_application(self):
        self.client.login(username='citizen1', password='pass12345')
        self.client.post(reverse('consular_application_detail', args=[self.app.reference_code]),
                         {'cancel_application': '1'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ConsularApplication.Status.CANCELLED)


class StaffWorkflowTests(ConsularSetup):
    def setUp(self):
        super().setUp()
        self.app = ConsularApplication.objects.create(
            mission=self.mission_a, service=self.service_a, citizen_user=self.citizen,
            full_name='Ayaan', email='a@example.com',
        )

    def test_staff_sees_only_own_mission_applications(self):
        self.client.login(username='officer_b', password='pass12345')
        resp = self.client.get(reverse('consular_staff_applications'))
        self.assertNotContains(resp, self.app.reference_code)

        self.client.login(username='officer_a', password='pass12345')
        resp = self.client.get(reverse('consular_staff_applications'))
        self.assertContains(resp, self.app.reference_code)

    def test_staff_cannot_open_other_missions_application(self):
        self.client.login(username='officer_b', password='pass12345')
        resp = self.client.get(reverse('consular_staff_application_detail', args=[self.app.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_staff_request_documents_then_citizen_reupload_returns_to_review(self):
        self.client.login(username='officer_a', password='pass12345')
        self.client.post(reverse('consular_staff_application_detail', args=[self.app.pk]), {
            'action': 'request_documents',
            'citizen_message': 'Please add your photo.',
            'staff_notes': 'blurry scan',
        })
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ConsularApplication.Status.DOCS_REQUIRED)
        self.assertEqual(self.app.citizen_message, 'Please add your photo.')
        self.assertIn('blurry scan', self.app.staff_notes)

        # Citizen uploads -> back to under review
        self.client.login(username='citizen1', password='pass12345')
        self.client.post(reverse('consular_application_detail', args=[self.app.reference_code]),
                         {'upload_documents': '1', 'documents': _pdf('photo.pdf')})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ConsularApplication.Status.UNDER_REVIEW)
        self.assertEqual(self.app.documents.count(), 1)

    def test_full_lifecycle_to_completed(self):
        self.client.login(username='officer_a', password='pass12345')
        url = reverse('consular_staff_application_detail', args=[self.app.pk])
        for action, status in [
            ('under_review', ConsularApplication.Status.UNDER_REVIEW),
            ('approve', ConsularApplication.Status.APPROVED),
            ('require_appointment', ConsularApplication.Status.APPOINTMENT_REQUIRED),
            ('complete', ConsularApplication.Status.COMPLETED),
        ]:
            self.client.post(url, {'action': action})
            self.app.refresh_from_db()
            self.assertEqual(self.app.status, status)


class AppointmentIntegrationTests(ConsularSetup):
    def setUp(self):
        super().setUp()
        self.app = ConsularApplication.objects.create(
            mission=self.mission_a, service=self.service_a, citizen_user=self.citizen,
            full_name='Ayaan', email='a@example.com',
            status=ConsularApplication.Status.APPOINTMENT_REQUIRED,
        )
        self.appointment = Appointment.objects.create(
            mission=self.mission_a, service=self.service_a, citizen_user=self.citizen,
            full_name='Ayaan',
        )

    def test_citizen_links_appointment(self):
        self.client.login(username='citizen1', password='pass12345')
        self.client.post(reverse('consular_application_detail', args=[self.app.reference_code]),
                         {'link_appointment': '1', 'qr_token': self.appointment.qr_token})
        self.app.refresh_from_db()
        self.assertEqual(self.app.appointment, self.appointment)

    def test_cannot_link_other_missions_appointment(self):
        wrong = Appointment.objects.create(
            mission=self.mission_b, service=self.service_b, citizen_user=self.citizen,
            full_name='Ayaan',
        )
        self.client.login(username='citizen1', password='pass12345')
        self.client.post(reverse('consular_application_detail', args=[self.app.reference_code]),
                         {'link_appointment': '1', 'qr_token': wrong.qr_token})
        self.app.refresh_from_db()
        self.assertIsNone(self.app.appointment_id)


class SeedConsularServicesTests(TestCase):
    def setUp(self):
        self.m1 = Mission.objects.create(name='Embassy One', country='One', city='Onecity')
        self.m2 = Mission.objects.create(name='Consulate Two', country='Two', city='Twocity')

    def test_seed_populates_every_mission_and_is_idempotent(self):
        call_command('seed_consular_services', stdout=StringIO())
        # Every mission gets the full catalogue, and each of the four citizen
        # categories is represented, for every mission.
        from consular.services import SERVICE_CATEGORIES, types_for_category
        for mission in (self.m1, self.m2):
            self.assertTrue(MissionService.objects.filter(mission=mission, is_active=True).exists())
            for category in SERVICE_CATEGORIES:
                self.assertTrue(
                    MissionService.objects.filter(
                        mission=mission, is_active=True,
                        service_type__in=types_for_category(category['key']),
                    ).exists(),
                    f"{mission.name} has no service in category {category['key']}",
                )

        count_after_first = MissionService.objects.count()
        # Running again must not create duplicates.
        call_command('seed_consular_services', stdout=StringIO())
        self.assertEqual(MissionService.objects.count(), count_after_first)


class AnonymousAccessTests(ConsularSetup):
    def test_anonymous_redirected_from_protected_views(self):
        for name, args in [
            ('consular_apply', []),
            ('my_consular_applications', []),
            ('consular_staff_applications', []),
        ]:
            resp = self.client.get(reverse(name, args=args))
            self.assertEqual(resp.status_code, 302, f'{name} did not redirect anonymous user')
