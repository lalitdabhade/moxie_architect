"""Thin PyMySQL helpers. All SQL elsewhere uses %s parameters - never string formatting."""
import re
from collections.abc import Iterator
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings
from app.constants import SECTIONS

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]{1,64}$")

# Overridden by the test suite so the app talks to DB_NAME_TEST.
_active_db_name = settings.db_name


def use_database(name: str) -> None:
    global _active_db_name
    _active_db_name = name


def active_database() -> str:
    return _active_db_name


def connect(database: str | None = "") -> pymysql.connections.Connection:
    """Open a connection. database="" means the active app DB; None means no DB selected."""
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=_active_db_name if database == "" else database,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def ensure_database(name: str | None = None) -> None:
    """Create the database if it does not exist yet (identifier is validated, not parameterizable)."""
    name = name or _active_db_name
    if not _IDENTIFIER.match(name):
        raise RuntimeError(f"Invalid database name: {name!r}")
    conn = connect(database=None)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def init_schema() -> None:
    """Create tables if missing and upsert the fixed sections."""
    statements = [s.strip() for s in SCHEMA_FILE.read_text(encoding="utf-8").split(";") if s.strip()]
    conn = connect()
    try:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
            for order, section in enumerate(SECTIONS, start=1):
                cur.execute(
                    "INSERT INTO sections (id, slug, name, sort_order) VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE slug = VALUES(slug), name = VALUES(name), "
                    "sort_order = VALUES(sort_order)",
                    (section["id"], section["slug"], section["name"], order),
                )
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[pymysql.connections.Connection]:
    """FastAPI dependency: one connection per request. Writers commit explicitly."""
    conn = connect()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
