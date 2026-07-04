from django.urls import path

from . import views

urlpatterns = [
    path('', views.notification_history_view, name='notification_history'),
    path('<int:pk>/read/', views.mark_read_view, name='mark_notification_read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_notifications_read'),
    path('emergency-broadcast/', views.emergency_broadcast_view, name='emergency_broadcast'),
]
