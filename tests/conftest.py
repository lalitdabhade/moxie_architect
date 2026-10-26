"""Test fixtures. Everything runs against DB_NAME_TEST, which is wiped between tests."""
import re
import shutil

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings

assert settings.db_name_test != settings.db_name, "DB_NAME_TEST must differ from DB_NAME"
db.use_database(settings.db_name_test)

from app.main import app  # noqa: E402  (import after switching databases)
from app.repositories import admins as admins_repo  # noqa: E402
from app.security import hash_password, login_limiter  # noqa: E402

TEST_USER = "tester"
TEST_PASSWORD = "correct-horse-battery"
_HASH = hash_password(TEST_PASSWORD)
TABLES = ["admin_sessions", "project_images", "projects", "inquiries", "admins"]


@pytest.fixture(scope="session", autouse=True)
def _schema():
    db.ensure_database()
    db.init_schema()


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in TABLES:
                cur.execute(f"TRUNCATE TABLE {table}")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        admins_repo.upsert(conn, TEST_USER, _HASH)
    finally:
        conn.close()
    login_limiter.clear()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def login_csrf(client: TestClient) -> str:
    html = client.get("/admin/login").text
    return re.search(r'data-csrf="([0-9a-f]+)"', html).group(1)


def do_login(client: TestClient, username=TEST_USER, password=TEST_PASSWORD):
    token = login_csrf(client)
    return client.post("/api/admin/login", json={"username": username, "password": password},
                       headers={"X-CSRF-Token": token})


@pytest.fixture
def admin_client(client):
    """A logged-in client; client.headers carries the session CSRF token."""
    res = do_login(client)
    assert res.status_code == 200, res.text
    client.headers["X-CSRF-Token"] = res.json()["csrf_token"]
    return client
