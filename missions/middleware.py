class SecurityHeadersMiddleware:
    """Adds a Content-Security-Policy tailored to the third-party resources
    this project actually loads (Tailwind CDN, Google Fonts, Leaflet/
    OpenStreetMap tiles, Chart.js CDN) plus a few headers Django's
    SecurityMiddleware doesn't set by default."""

    CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.tailwindcss.com cdn.jsdelivr.net unpkg.com; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com unpkg.com; "
        "font-src 'self' fonts.gstatic.com; "
        "img-src 'self' data: *.tile.openstreetmap.org unpkg.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('Content-Security-Policy', self.CSP)
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Referrer-Policy', 'same-origin')
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        return response
