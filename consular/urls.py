from django.urls import path

from . import views

urlpatterns = [
    # Citizen
    path('', views.consular_services_view, name='consular_services'),
    path('apply/', views.apply_view, name='consular_apply'),
    path('my-applications/', views.my_applications_view, name='my_consular_applications'),
    path('application/<str:reference_code>/', views.application_detail_view, name='consular_application_detail'),

    # Mission staff
    path('staff/applications/', views.staff_applications_view, name='consular_staff_applications'),
    path('staff/application/<int:pk>/', views.staff_application_detail_view, name='consular_staff_application_detail'),
]
