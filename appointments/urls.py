from django.urls import path

from . import views

urlpatterns = [
    path('book/', views.book_appointment_view, name='book_appointment'),
    path('confirmation/<str:qr_token>/', views.appointment_confirmation_view, name='appointment_confirmation'),
    path('confirmation/<str:qr_token>/qr.png', views.appointment_qr_image_view, name='appointment_qr_image'),
    path('staff/', views.staff_appointments_view, name='staff_appointments'),
    path('staff/<int:pk>/action/', views.appointment_action_view, name='appointment_action'),
    path('staff/mission/<int:mission_pk>/slots/', views.manage_slots_view, name='manage_appointment_slots'),
    path('staff/waitlist/', views.appointment_waitlist_view, name='appointment_waitlist'),
    path('staff/stats/', views.appointment_stats_view, name='appointment_stats'),
]
