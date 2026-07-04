from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .utils.audit import log_audit_action


@receiver(user_logged_in)
def _log_login(sender, request, user, **kwargs):
    log_audit_action(user, None, 'Login', f'User {user.username} logged in.', request=request)


@receiver(user_logged_out)
def _log_logout(sender, request, user, **kwargs):
    log_audit_action(user, None, 'Logout', f'User {user.username if user else "unknown"} logged out.', request=request)


@receiver(user_login_failed)
def _log_login_failed(sender, credentials, request=None, **kwargs):
    username = credentials.get('username', 'unknown')
    log_audit_action(None, None, 'Login Failed', f'Failed login attempt for username: {username}', request=request)
