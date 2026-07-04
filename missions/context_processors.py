from django.utils import timezone


def site_context(request):
    return {'now': timezone.now()}
