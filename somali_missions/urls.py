from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from missions.monitoring import health_check_view, metrics_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('health/', health_check_view, name='health_check'),
    path('metrics/', metrics_view, name='metrics'),
    path('appointments/', include('appointments.urls')),
    path('queue/', include('queue_management.urls')),
    path('assistant/', include('assistant.urls')),
    path('notifications/', include('notifications.urls')),
    path('consular/', include('consular.urls')),
    path('api/v1/', include('api.urls')),
    path('', include('missions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
