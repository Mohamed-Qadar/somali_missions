from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile
from .utils.audit import log_audit_action
from .utils.permissions import sync_user_permissions


@receiver(post_save, sender=UserProfile)
def _sync_permissions_from_profile(sender, instance, raw=False, **kwargs):
    # raw=True during loaddata (restore_db) - the fixture carries its own group
    # / M2M data, so don't fight it here.
    if raw:
        return
    sync_user_permissions(instance)


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
