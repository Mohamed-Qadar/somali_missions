MINISTRY_ADMIN_GROUP = 'MinistryAdmin'
MISSION_STAFF_GROUP = 'MissionStaff'


def user_is_ministry_admin(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=MINISTRY_ADMIN_GROUP).exists()


def user_can_manage_mission(user, mission):
    if not user.is_authenticated:
        return False
    if user_is_ministry_admin(user):
        return True
    if user.groups.filter(name=MISSION_STAFF_GROUP).exists():
        return mission.staff_users.filter(pk=user.pk).exists()
    return False


def missions_for_user(user):
    from missions.models import Mission

    if user_is_ministry_admin(user):
        return Mission.objects.all()
    if user.groups.filter(name=MISSION_STAFF_GROUP).exists():
        return Mission.objects.filter(staff_users=user)
    return Mission.objects.none()
