"""Consistent JSON error shape for /api: {"error": {"code", "message", "fields"?}}."""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_DEFAULT_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "too_many_requests",
}


class ApiError(Exception):
    def __init__(self, status: int, message: str, code: str | None = None,
                 fields: dict[str, str] | None = None, headers: dict[str, str] | None = None):
        self.status = status
        self.message = message
        self.code = code or _DEFAULT_CODES.get(status, "error")
        self.fields = fields
        self.headers = headers


def error_body(code: str, message: str, fields: dict | None = None) -> dict:
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return {"error": body}


def _is_api(request: Request) -> bool:
    return request.url.path.startswith("/api/") or request.url.path == "/api"


def register_error_handlers(app, templates) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return JSONResponse(error_body(exc.code, exc.message, exc.fields),
                            status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        fields = {}
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path", "form")]
            fields[".".join(loc) or "request"] = err.get("msg", "Invalid value")
        return JSONResponse(error_body("validation_error", "Please correct the highlighted fields.", fields),
                            status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if _is_api(request):
            message = exc.detail if isinstance(exc.detail, str) else "Request failed."
            return JSONResponse(error_body(_DEFAULT_CODES.get(exc.status_code, "error"), message),
                                status_code=exc.status_code, headers=getattr(exc, "headers", None))
        template = "public/404.html" if exc.status_code == 404 else "public/error.html"
        return templates.TemplateResponse(
            request, template, {"status": exc.status_code, "message": exc.detail},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        if _is_api(request):
            return JSONResponse(error_body("server_error", "Something went wrong."), status_code=500)
        return HTMLResponse("<h1>Something went wrong.</h1>", status_code=500)
