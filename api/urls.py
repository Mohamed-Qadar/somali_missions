from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

router = DefaultRouter()
router.register('missions', views.MissionViewSet, basename='api-mission')
router.register('appointment-slots', views.AppointmentSlotViewSet, basename='api-appointment-slot')
router.register('appointments', views.AppointmentViewSet, basename='api-appointment')
router.register('queue-tickets', views.QueueTicketViewSet, basename='api-queue-ticket')
router.register('complaints', views.ComplaintViewSet, basename='api-complaint')
router.register('notifications', views.NotificationViewSet, basename='api-notification')

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='api_token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('assistant/ask/', views.AssistantAskView.as_view(), name='api_assistant_ask'),
    path('kpi/summary/', views.KPISummaryView.as_view(), name='api_kpi_summary'),
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    path('', include(router.urls)),
]
