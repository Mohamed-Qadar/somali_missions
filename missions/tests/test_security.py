from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=3, AXES_LOCKOUT_PARAMETERS=[['username', 'ip_address']])
class LoginLockoutTests(TestCase):
    """django-axes brute-force lockout. Disabled globally under the test runner
    (see settings.TESTING), so it's re-enabled here explicitly and axes state is
    reset around each test."""

    def setUp(self):
        from axes.utils import reset
        reset()
        cache.clear()
        User.objects.create_user(username='victim', password='Correct-Horse-9')

    def tearDown(self):
        from axes.utils import reset
        reset()
        cache.clear()

    def _attempt(self, password):
        return self.client.post(reverse('login'), {'username': 'victim', 'password': password, 'remember_me': ''})

    def test_wrong_password_below_limit_is_not_locked(self):
        resp = self._attempt('wrong')
        self.assertEqual(resp.status_code, 200)  # normal "invalid credentials" page

    def test_account_locks_after_repeated_failures(self):
        for _ in range(3):
            self._attempt('wrong')
        # Even the CORRECT password is now refused with the lockout response.
        resp = self._attempt('Correct-Horse-9')
        self.assertEqual(resp.status_code, 429)
        self.assertContains(resp, 'Too Many Login Attempts', status_code=429)

    def test_lockout_clears_after_reset(self):
        for _ in range(3):
            self._attempt('wrong')
        from axes.utils import reset
        reset()
        cache.clear()
        resp = self._attempt('Correct-Horse-9')
        self.assertEqual(resp.status_code, 302)  # successful login redirect
