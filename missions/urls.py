from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.mission_list, name='home'),
    path('mission/<int:pk>/', views.mission_detail, name='mission_detail'),
    path('complaint-success/', views.complaint_success, name='complaint_success'),
    path('track/', views.track_complaint, name='track'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('faq/', views.faq_view, name='faq'),
    path('analysis/', views.analysis_view, name='analysis'),
    path('reports/', views.report_dashboard, name='report_dashboard'),
    path('reports/export.csv', views.export_complaints_csv, name='export_complaints_csv'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email_view, name='verify_email'),
    path('dashboard/', views.dashboard_router_view, name='dashboard_router'),
    path('dashboard/citizen/', views.citizen_dashboard, name='citizen_dashboard'),
    path('dashboard/embassy/', views.embassy_officer_dashboard_view, name='embassy_officer_dashboard'),
    path('dashboard/embassy-management/', views.embassy_manager_dashboard_view, name='embassy_manager_dashboard'),
    path('dashboard/reviewer/', views.ministry_reviewer_dashboard_view, name='ministry_reviewer_dashboard'),
    path('dashboard/admin/', views.ministry_admin_dashboard_view, name='ministry_admin_dashboard'),
    
    path('track/feedback/<str:tracking_code>/', views.submit_satisfaction, name='submit_satisfaction'),
    path('complaint/submit/', views.submit_complaint_wizard, name='submit_complaint_wizard'),
    path('emergency/', views.emergency_hotline_view, name='emergency_hotline'),
    path('emergency/submit/', views.submit_emergency_view, name='submit_emergency'),
    path('ministry/operations/', views.ministry_operations_view, name='ministry_operations'),
    path('ministry/analytics/', views.ministry_analytics_view, name='ministry_analytics'),
    path('api/translate/<int:pk>/', views.ai_translation_api, name='ai_translation_api'),
    path('transparency/', views.transparency_portal_view, name='transparency'),
    path('directory/', views.directory_view, name='directory'),
    path('before-you-travel/', views.before_you_travel_view, name='before_you_travel'),
    path('communities/', views.community_directory_view, name='community_directory'),
    path('communities/students/', views.student_association_directory_view, name='student_association_directory'),
    path('communities/group/<int:pk>/', views.community_group_detail_view, name='community_group_detail'),
    path('communities/student/<int:pk>/', views.student_association_detail_view, name='student_association_detail'),
    path('communities/admin/', views.community_admin_dashboard_view, name='community_admin_dashboard'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/mission/<int:pk>/', views.staff_mission_manage, name='staff_mission_manage'),
    
    # Embassy portal urls
    path('ministry/invite/', views.invite_embassy_user_view, name='invite_embassy_user'),
    path('embassy/activate/<str:token>/', views.activate_embassy_account_view, name='activate_embassy_account'),
    path('embassy/case/<int:pk>/', views.embassy_case_detail_view, name='embassy_case_detail'),
    path('embassy/case/<int:pk>/message/', views.post_secure_message_view, name='post_secure_message'),

    # Password resets
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]

