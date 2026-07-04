from django.db import transaction
from django.db.models import Avg, Max
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from appointments.models import Appointment, AppointmentSlot
from assistant.models import AssistantConversationLog, AssistantTopic
from assistant.providers import get_answer_provider
from missions.models import Complaint, Mission
from missions.utils.permissions import missions_for_user, user_is_ministry_admin
from notifications.models import Notification
from queue_management.models import QueueTicket

from .serializers import (
    AppointmentSerializer, AppointmentSlotSerializer, AssistantAskRequestSerializer,
    AssistantAskResponseSerializer, ComplaintSerializer, KPISummarySerializer, MissionSerializer,
    NotificationSerializer, QueueTicketSerializer,
)


class MissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Public mission directory - no authentication required, matches the web directory page."""
    queryset = Mission.objects.all().order_by('country', 'name')
    serializer_class = MissionSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['country', 'mission_type']
    search_fields = ['name', 'country', 'city']
    ordering_fields = ['name', 'country']


class AppointmentSlotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AppointmentSlot.objects.filter(is_active=True, date__gte=timezone.now().date())
    serializer_class = AppointmentSlotSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['mission', 'service']


class ComplaintViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only for now: complaint *creation* stays on the web form, which has
    anti-spam captcha and rate limiting the API does not replicate yet."""
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'mission', 'category']
    search_fields = ['tracking_code', 'subject']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Complaint.objects.none()
        user = self.request.user
        if user_is_ministry_admin(user):
            return Complaint.objects.all().order_by('-created_at')
        staff_missions = missions_for_user(user)
        if staff_missions.exists():
            return Complaint.objects.filter(mission__in=staff_missions).order_by('-created_at')
        return Complaint.objects.filter(citizen_user=user).order_by('-created_at')


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Appointment.objects.none()
        if user_is_ministry_admin(user):
            return Appointment.objects.all().order_by('-created_at')
        staff_missions = missions_for_user(user)
        if staff_missions.exists():
            return Appointment.objects.filter(mission__in=staff_missions).order_by('-created_at')
        return Appointment.objects.filter(citizen_user=user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = request.data.get('slot')
        if not slot_id:
            return Response({'slot': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            slot = AppointmentSlot.objects.select_for_update().filter(pk=slot_id).first()
            if not slot:
                return Response({'slot': 'Slot not found.'}, status=status.HTTP_404_NOT_FOUND)
            appt_status = Appointment.Status.WAITLISTED if slot.is_full else Appointment.Status.PENDING
            appointment = Appointment.objects.create(
                mission=slot.mission,
                service=slot.service,
                slot=slot,
                citizen_user=request.user if request.user.is_authenticated else None,
                full_name=serializer.validated_data['full_name'],
                email=serializer.validated_data.get('email', ''),
                phone=serializer.validated_data.get('phone', ''),
                status=appt_status,
            )
        return Response(self.get_serializer(appointment).data, status=status.HTTP_201_CREATED)


class QueueTicketViewSet(viewsets.ModelViewSet):
    serializer_class = QueueTicketSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return QueueTicket.objects.none()
        if user_is_ministry_admin(user):
            return QueueTicket.objects.filter(date=timezone.now().date()).order_by('ticket_number')
        staff_missions = missions_for_user(user)
        return QueueTicket.objects.filter(mission__in=staff_missions, date=timezone.now().date()).order_by('ticket_number')

    def create(self, request, *args, **kwargs):
        mission_id = request.data.get('mission')
        mission = Mission.objects.filter(pk=mission_id).first()
        if not mission:
            return Response({'mission': 'Mission not found.'}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()
        with transaction.atomic():
            existing = QueueTicket.objects.select_for_update().filter(mission=mission, date=today)
            next_number = (existing.aggregate(m=Max('ticket_number'))['m'] or 0) + 1
            ticket = QueueTicket.objects.create(
                mission=mission,
                service_id=request.data.get('service') or None,
                date=today,
                ticket_number=next_number,
                full_name=request.data.get('full_name', ''),
            )
        return Response(self.get_serializer(ticket).data, status=status.HTTP_201_CREATED)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'marked_read': updated})


class AssistantAskThrottle(AnonRateThrottle):
    rate = '30/hour'


class AssistantAskView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AssistantAskThrottle]

    @extend_schema(request=AssistantAskRequestSerializer, responses=AssistantAskResponseSerializer)
    def post(self, request):
        request_serializer = AssistantAskRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        question = request_serializer.validated_data['question']

        provider = get_answer_provider()
        answer = provider.answer(question)
        matched_topic = (
            AssistantTopic.objects.filter(topic_key=answer.topic_key).first() if answer.topic_key else None
        )
        AssistantConversationLog.objects.create(
            session_key=request.session.session_key or '',
            user=request.user if request.user.is_authenticated else None,
            query_text=question,
            matched_topic=matched_topic,
            confidence=answer.confidence,
        )
        response_serializer = AssistantAskResponseSerializer(answer.__dict__)
        return Response(response_serializer.data)


class KPISummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=KPISummarySerializer)
    def get(self, request):
        user = request.user
        if user_is_ministry_admin(user):
            missions = Mission.objects.all()
        else:
            missions = missions_for_user(user)
            if not missions.exists():
                return Response({'detail': 'Not authorized for any mission.'}, status=status.HTTP_403_FORBIDDEN)

        complaints = Complaint.objects.filter(mission__in=missions)
        resolved_statuses = [Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO]

        data = {
            'mission_count': missions.count(),
            'total_complaints': complaints.count(),
            'open_complaints': complaints.exclude(status__in=resolved_statuses).count(),
            'closed_complaints': complaints.filter(status__in=resolved_statuses).count(),
            'average_rating': complaints.aggregate(avg=Avg('rating'))['avg'],
            'appointments_today': Appointment.objects.filter(
                mission__in=missions, slot__date=timezone.now().date()
            ).count(),
            'queue_tickets_today': QueueTicket.objects.filter(mission__in=missions, date=timezone.now().date()).count(),
        }
        return Response(KPISummarySerializer(data).data)
