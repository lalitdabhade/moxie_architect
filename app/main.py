"""FastAPI application entry point: uvicorn app.main:app"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app import db
from app.api import admin as admin_api
from app.config import BASE_DIR, settings
from app.errors import register_error_handlers
from app.templating import templates
from app.web import admin_pages, public_pages

CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


def prepare_storage() -> None:
    settings.project_upload_dir.mkdir(parents=True, exist_ok=True)
    settings.layout_upload_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    prepare_storage()
    db.ensure_database()
    db.init_schema()
    yield


def create_app() -> FastAPI:
    prepare_storage()  # StaticFiles requires the directory to exist at mount time
    app = FastAPI(title="Architect App API", lifespan=lifespan,
                  docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path != "/api/docs":  # Swagger UI loads its own CDN assets
            response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.url.path.startswith(("/api/admin", "/admin")):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    register_error_handlers(app, templates)
    app.add_exception_handler(admin_pages.LoginRequired, admin_pages.login_required_handler)

    app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
    # Only project images are public. uploads/layouts is deliberately NOT mounted.
    app.mount("/uploads/projects", StaticFiles(directory=settings.project_upload_dir), name="project-uploads")

    app.include_router(admin_api.router)
    app.include_router(admin_pages.router)
    app.include_router(public_pages.router)
    return app


app = create_app()
