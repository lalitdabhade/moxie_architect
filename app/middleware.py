"""ASGI middleware: request body size limits and security headers.

The body cap rejects oversized requests before they are parsed or spooled to disk. Per-file
limits are enforced again in app.uploads; this stops a client from streaming an arbitrarily
large body into the multipart parser.
"""
import re

# FastAPI re-raises its own HTTPException while reading a body (any other error becomes a 400).
from fastapi import HTTPException
from starlette.responses import JSONResponse

from app.constants import (
    LAYOUT_MAX_BYTES, MAX_IMAGES_PER_UPLOAD, PROJECT_IMAGE_MAX_BYTES,
)
from app.errors import error_body

MB = 1024 * 1024
DEFAULT_LIMIT = 1 * MB
# (method, path regex, max body bytes). Room is left for multipart headers and form fields.
ROUTE_LIMITS = [
    ("POST", re.compile(r"^/api/admin/projects(/\d+/images)?$"),
     MAX_IMAGES_PER_UPLOAD * PROJECT_IMAGE_MAX_BYTES + 2 * MB),
    ("POST", re.compile(r"^/api/inquiries$"), LAYOUT_MAX_BYTES + 1 * MB),
]


def limit_for(method: str, path: str) -> int:
    for m, pattern, limit in ROUTE_LIMITS:
        if method == m and pattern.match(path):
            return limit
    return DEFAULT_LIMIT


def _too_large(limit: int) -> str:
    return f"Request is too large (maximum {limit // MB} MB)."


class BodySizeLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        limit = limit_for(scope["method"], scope["path"])
        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            response = JSONResponse(error_body("payload_too_large", _too_large(limit)), status_code=413,
                                    headers={"Connection": "close"})
            return await response(scope, receive, send)

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:  # chunked or lying Content-Length
                    raise HTTPException(413, _too_large(limit))
            return message

        await self.app(scope, limited_receive, send)


CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


class SecurityHeadersMiddleware:
    """Adds security headers to every response (plain ASGI: no task groups around the body)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        extra = [
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"referrer-policy", b"same-origin"),
        ]
        if path != "/api/docs":  # Swagger UI loads its own CDN assets
            extra.append((b"content-security-policy", CSP.encode()))
        if path.startswith(("/api/admin", "/admin")):
            extra.append((b"cache-control", b"no-store"))

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                headers += [(k, v) for k, v in extra if k not in present]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
