from django.urls import path

from . import views

urlpatterns = [
    path('join/', views.join_queue_view, name='join_queue'),
    path('ticket/<int:pk>/', views.queue_ticket_status_view, name='queue_ticket_status'),
    path('display/<int:mission_pk>/', views.queue_display_view, name='queue_display'),
    path('staff/', views.staff_queue_dashboard, name='staff_queue_dashboard'),
    path('staff/mission/<int:mission_pk>/call-next/', views.queue_call_next_view, name='queue_call_next'),
    path('staff/ticket/<int:pk>/<str:action>/', views.queue_ticket_action_view, name='queue_ticket_action'),
    path('staff/analytics/', views.queue_analytics_view, name='queue_analytics'),
]
