"""Application settings, loaded once from environment / .env."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    db_name_test: str
    admin_username: str
    admin_password: str
    session_secret: str
    session_hours: int
    cookie_secure: bool
    upload_dir: Path

    @property
    def project_upload_dir(self) -> Path:
        return self.upload_dir / "projects"

    @property
    def layout_upload_dir(self) -> Path:
        return self.upload_dir / "layouts"


def load_settings() -> Settings:
    secret = os.getenv("SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("SESSION_SECRET must be set in .env (at least 32 characters).")
    return Settings(
        db_host=os.getenv("DB_HOST", "127.0.0.1"),
        db_port=int(os.getenv("DB_PORT", "3306")),
        db_user=os.getenv("DB_USER", ""),
        db_password=os.getenv("DB_PASSWORD", ""),
        db_name=os.getenv("DB_NAME", "architect_app"),
        db_name_test=os.getenv("DB_NAME_TEST", "architect_app_test"),
        admin_username=os.getenv("ADMIN_USERNAME", ""),
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        session_secret=secret,
        session_hours=int(os.getenv("SESSION_HOURS", "8")),
        cookie_secure=_bool(os.getenv("COOKIE_SECURE")),
        upload_dir=Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))),
    )


settings = load_settings()
