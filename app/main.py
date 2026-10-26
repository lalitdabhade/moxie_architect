"""FastAPI application entry point: uvicorn app.main:app"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.api import admin as admin_api
from app.api import public as public_api
from app.config import BASE_DIR, settings
from app.errors import register_error_handlers
from app.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.templating import templates
from app.web import admin_pages, public_pages


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

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)  # added last = outermost
    register_error_handlers(app, templates)
    app.add_exception_handler(admin_pages.LoginRequired, admin_pages.login_required_handler)

    app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
    # Only project images are public. uploads/layouts is deliberately NOT mounted.
    app.mount("/uploads/projects", StaticFiles(directory=settings.project_upload_dir), name="project-uploads")

    app.include_router(admin_api.router)
    app.include_router(public_api.router)
    app.include_router(admin_pages.router)
    app.include_router(public_pages.router)
    return app


app = create_app()
