import secrets


class SecurityHeadersMiddleware:
    """Adds a nonce-based Content-Security-Policy tailored to the third-party
    resources this project actually loads (Google Fonts, Leaflet/OpenStreetMap
    tiles, Chart.js CDN) plus a few headers Django's SecurityMiddleware doesn't
    set by default.

    script-src does NOT allow 'unsafe-inline': every inline <script> in the
    app's own templates carries nonce="{{ request.csp_nonce }}", and the two
    external script CDNs are host-allowlisted. The Django admin uses some
    inline scripts of its own that don't carry our nonce, so /admin/ keeps
    'unsafe-inline' (admin is only reachable by trusted staff/superusers).

    style-src keeps 'unsafe-inline' because a few templates use inline style=
    attributes (e.g. the analytics heatmap's computed cell colours) and CSP
    nonces do not apply to style attributes - only to <style> elements. Style
    injection is a far lower risk than script injection.
    """

    def _csp(self, nonce, *, allow_inline_scripts=False):
        script_src = "'self' https://cdn.jsdelivr.net https://unpkg.com"
        script_src += " 'unsafe-inline'" if allow_inline_scripts else f" 'nonce-{nonce}'"
        return (
            "default-src 'self'; "
            f"script-src {script_src}; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate the nonce before the view runs so templates can read it.
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce

        response = self.get_response(request)

        allow_inline = request.path.startswith('/admin/')
        response.setdefault('Content-Security-Policy', self._csp(nonce, allow_inline_scripts=allow_inline))
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Referrer-Policy', 'same-origin')
        response.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        return response
