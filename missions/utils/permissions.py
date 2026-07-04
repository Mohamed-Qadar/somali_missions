MINISTRY_ADMIN_GROUP = 'MinistryAdmin'
MISSION_STAFF_GROUP = 'MissionStaff'


def _profile_role(user):
    """UserProfile.role if the user has a profile, else None.

    UserProfile.role/mission is the single source of truth for authorization.
    Django auth Groups (MinistryAdmin/MissionStaff) and Mission.staff_users are
    kept as an automatic projection of the role via sync_user_permissions()
    (wired to a post_save signal on UserProfile), so the two representations
    can never drift. The permission helpers below still read both as
    belt-and-braces, but the signal guarantees they agree."""
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


def sync_user_permissions(profile):
    """Project a UserProfile's role/mission onto Django Groups and
    Mission.staff_users so legacy/Group-based checks (and Django admin) stay
    consistent with the role. Idempotent; safe to call repeatedly. Called from
    the UserProfile post_save signal and the sync_permissions command."""
    from django.contrib.auth.models import Group
    from missions.models import UserProfile

    user = profile.user
    ministry_group, _ = Group.objects.get_or_create(name=MINISTRY_ADMIN_GROUP)
    staff_group, _ = Group.objects.get_or_create(name=MISSION_STAFF_GROUP)

    role = profile.role
    ministry_roles = (UserProfile.Role.MINISTRY_ADMIN, UserProfile.Role.MINISTRY_REVIEWER)
    staff_roles = (UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER, UserProfile.Role.EMBASSY_STAFF)

    # Superusers keep the ministry group regardless of their (often unset) role.
    if role in ministry_roles or user.is_superuser:
        user.groups.add(ministry_group)
    else:
        user.groups.remove(ministry_group)

    if role in staff_roles:
        user.groups.add(staff_group)
        if profile.mission_id:
            profile.mission.staff_users.add(user)
    else:
        user.groups.remove(staff_group)


def user_is_ministry_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.groups.filter(name=MINISTRY_ADMIN_GROUP).exists():
        return True
    from missions.models import UserProfile
    return _profile_role(user) in (UserProfile.Role.MINISTRY_ADMIN, UserProfile.Role.MINISTRY_REVIEWER)


def user_can_manage_mission(user, mission):
    if not user.is_authenticated:
        return False
    if user_is_ministry_admin(user):
        return True
    if user.groups.filter(name=MISSION_STAFF_GROUP).exists() and mission.staff_users.filter(pk=user.pk).exists():
        return True
    from missions.models import UserProfile
    profile = getattr(user, 'profile', None)
    if profile and profile.role in (UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER):
        return profile.mission_id == mission.pk
    return False


def missions_for_user(user):
    from missions.models import Mission, UserProfile

    if user_is_ministry_admin(user):
        return Mission.objects.all()

    mission_ids = set(
        Mission.objects.filter(staff_users=user).values_list('pk', flat=True)
    ) if user.groups.filter(name=MISSION_STAFF_GROUP).exists() else set()

    profile = getattr(user, 'profile', None)
    if profile and profile.role in (UserProfile.Role.EMBASSY_OFFICER, UserProfile.Role.EMBASSY_MANAGER) and profile.mission_id:
        mission_ids.add(profile.mission_id)

    return Mission.objects.filter(pk__in=mission_ids)
