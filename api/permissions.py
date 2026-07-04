from rest_framework.permissions import BasePermission

from missions.utils.permissions import user_can_manage_mission, user_is_ministry_admin


class IsMissionStaffOrMinistry(BasePermission):
    """Object-level permission mirroring the web views: a mission-scoped
    object (Complaint, Appointment, QueueTicket - anything with a `.mission`
    attribute) is only writable/readable by staff of that specific mission
    or a ministry admin/superuser. Prevents the API from being a way to
    bypass the mission-scoping the web UI already enforces."""

    def has_object_permission(self, request, view, obj):
        mission = getattr(obj, 'mission', None)
        if mission is None:
            return False
        return user_can_manage_mission(request.user, mission)


class IsMinistryAdmin(BasePermission):
    def has_permission(self, request, view):
        return user_is_ministry_admin(request.user)


class IsOwnerOrMissionStaffOrMinistry(BasePermission):
    """For citizen-owned objects (Appointment, Complaint): the citizen who
    owns it, mission staff for that object's mission, or a ministry admin."""

    def has_object_permission(self, request, view, obj):
        if getattr(obj, 'citizen_user_id', None) == request.user.id:
            return True
        mission = getattr(obj, 'mission', None)
        if mission is not None and user_can_manage_mission(request.user, mission):
            return True
        return user_is_ministry_admin(request.user)
