"""Security response headers (SECURITY.md §5, OWASP). Applied to every response.

A strict Content-Security-Policy is safe here because the SPA is served same-origin and
loads no third-party scripts, styles or fonts (fonts are self-hosted in the bundle).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "  # Vite inlines a small style attribute set
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # HSTS only matters over HTTPS; harmless over http in dev.
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    for name, value in HEADERS.items():
        response.headers.setdefault(name, value)
    return response
