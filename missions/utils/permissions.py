MINISTRY_ADMIN_GROUP = 'MinistryAdmin'
MISSION_STAFF_GROUP = 'MissionStaff'


def _profile_role(user):
    """UserProfile.role if the user has a profile, else None. There are two
    independent ways a user ends up scoped to the ministry/a mission in this
    codebase: Django auth Groups (set by seed_missions.py) and
    UserProfile.role/mission (set by the embassy invitation flow in
    invite_embassy_user_view/activate_embassy_account_view). Both are checked
    everywhere below so it doesn't matter which path provisioned the account."""
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


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
