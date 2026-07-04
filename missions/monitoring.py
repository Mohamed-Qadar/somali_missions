from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.http import HttpResponse, JsonResponse


def health_check_view(request):
    """Liveness/readiness probe for load balancers and container orchestrators.
    Checks DB and cache connectivity - returns 503 if either is unreachable."""
    checks = {}

    try:
        connections['default'].cursor()
        checks['database'] = True
    except Exception:
        checks['database'] = False

    try:
        cache.set('health_check_probe', 'ok', 5)
        checks['cache'] = cache.get('health_check_probe') == 'ok'
    except Exception:
        checks['cache'] = False

    healthy = all(checks.values())
    return JsonResponse({'status': 'ok' if healthy else 'unhealthy', 'checks': checks}, status=200 if healthy else 503)


def metrics_view(request):
    """Prometheus-format metrics. No-op (404) if METRICS_ENABLED=False or
    prometheus_client isn't installed - Prometheus/Grafana are optional
    infrastructure, not a hard requirement to run the site."""
    if not getattr(settings, 'METRICS_ENABLED', True):
        return HttpResponse(status=404)

    try:
        from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest
    except ImportError:
        return HttpResponse('prometheus_client is not installed', status=503, content_type='text/plain')

    from missions.models import Complaint, Mission

    resolved_statuses = [Complaint.Status.RESOLVED, Complaint.Status.CLOSED, Complaint.Status.RES, Complaint.Status.CLO]

    registry = CollectorRegistry()
    Gauge('somali_missions_total_missions', 'Total missions in the directory', registry=registry).set(
        Mission.objects.count()
    )
    Gauge('somali_missions_total_complaints', 'Total complaints ever submitted', registry=registry).set(
        Complaint.objects.count()
    )
    Gauge('somali_missions_open_complaints', 'Complaints not yet resolved or closed', registry=registry).set(
        Complaint.objects.exclude(status__in=resolved_statuses).count()
    )

    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
