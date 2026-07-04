from typing import Optional

from rest_framework import serializers

from appointments.models import Appointment, AppointmentSlot
from missions.models import Complaint, Mission
from notifications.models import Notification
from queue_management.models import QueueTicket


class MissionSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            'id', 'name', 'country', 'city', 'address', 'phone', 'email', 'website',
            'working_hours', 'mission_type', 'latitude', 'longitude', 'average_rating',
        ]

    def get_average_rating(self, obj) -> Optional[float]:
        from django.db.models import Avg
        return obj.complaints.aggregate(avg=Avg('rating'))['avg']


class ComplaintSerializer(serializers.ModelSerializer):
    mission_name = serializers.CharField(source='mission.name', read_only=True)

    class Meta:
        model = Complaint
        fields = [
            'id', 'tracking_code', 'mission', 'mission_name', 'subject', 'category',
            'rating', 'status', 'priority', 'created_at', 'updated_at', 'is_anonymous',
        ]
        read_only_fields = fields


class AppointmentSlotSerializer(serializers.ModelSerializer):
    booked_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()

    class Meta:
        model = AppointmentSlot
        fields = ['id', 'mission', 'service', 'date', 'start_time', 'end_time', 'capacity', 'booked_count', 'is_full']


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id', 'qr_token', 'mission', 'service', 'slot', 'full_name', 'email', 'phone',
            'status', 'created_at',
        ]
        read_only_fields = ['id', 'qr_token', 'status', 'created_at']


class QueueTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueTicket
        fields = ['id', 'mission', 'service', 'ticket_number', 'date', 'full_name', 'status', 'created_at']
        read_only_fields = ['id', 'ticket_number', 'date', 'status', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'category', 'priority', 'link_url', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'body', 'category', 'priority', 'link_url', 'created_at']


class AssistantAskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000)


class AssistantAskResponseSerializer(serializers.Serializer):
    topic_key = serializers.CharField(allow_null=True)
    title = serializers.CharField()
    answer_text = serializers.CharField()
    suggested_action = serializers.CharField()
    confidence = serializers.FloatField()


class KPISummarySerializer(serializers.Serializer):
    mission_count = serializers.IntegerField()
    total_complaints = serializers.IntegerField()
    open_complaints = serializers.IntegerField()
    closed_complaints = serializers.IntegerField()
    average_rating = serializers.FloatField(allow_null=True)
    appointments_today = serializers.IntegerField()
    queue_tickets_today = serializers.IntegerField()
