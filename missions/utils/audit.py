def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit_action(user, complaint, action, details="", request=None):
    from missions.models import AuditLog

    ip_address = None
    user_agent = ''
    if request is not None:
        ip_address = _client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:300]

    AuditLog.objects.create(
        user=user if (user and getattr(user, 'is_authenticated', False)) else None,
        complaint=complaint,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
