from django.core.cache import cache


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def is_rate_limited(request, key_prefix, limit=3, window_seconds=86400):
    ip = _client_ip(request)
    cache_key = f'ratelimit:{key_prefix}:{ip}'
    count = cache.get(cache_key, 0)
    return count >= limit


def increment_rate_limit(request, key_prefix, window_seconds=86400):
    ip = _client_ip(request)
    cache_key = f'ratelimit:{key_prefix}:{ip}'
    count = cache.get(cache_key, 0)
    cache.set(cache_key, count + 1, window_seconds)
