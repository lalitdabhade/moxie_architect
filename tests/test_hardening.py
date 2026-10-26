"""Request size limits, headers and small polish items."""
from app.middleware import DEFAULT_LIMIT, limit_for
from tests.test_inquiries import interior


def test_route_limits():
    assert limit_for("POST", "/api/inquiries") > 10 * 1024 * 1024
    assert limit_for("POST", "/api/admin/projects") > 30 * 5 * 1024 * 1024
    assert limit_for("POST", "/api/admin/projects/7/images") == limit_for("POST", "/api/admin/projects")
    assert limit_for("POST", "/api/admin/login") == DEFAULT_LIMIT
    assert limit_for("GET", "/api/inquiries") == DEFAULT_LIMIT


def test_declared_oversize_body_rejected_before_parsing(client):
    res = client.post("/api/inquiries", content=b"x",
                      headers={"Content-Length": str(50 * 1024 * 1024), "Content-Type": "multipart/form-data; boundary=x"})
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "payload_too_large"


def test_streamed_oversize_body_rejected(client):
    def chunks():
        for _ in range(3):
            yield b"0" * (DEFAULT_LIMIT // 2 + 1)
    # No Content-Length (chunked): the middleware counts bytes as they arrive.
    res = client.post("/api/admin/login", content=chunks(), headers={"Content-Type": "application/json"})
    assert res.status_code == 413


def test_streamed_oversize_multipart_rejected(client):
    def chunks():
        yield b"--x\r\nContent-Disposition: form-data; name=\"layout\"; filename=\"a.pdf\"\r\n\r\n%PDF-"
        for _ in range(13):
            yield b"0" * (1024 * 1024)
    res = client.post("/api/inquiries", content=chunks(),
                      headers={"Content-Type": "multipart/form-data; boundary=x"})
    assert res.status_code == 413


def test_normal_inquiry_still_works(client):
    assert client.post("/api/inquiries", data=interior()).status_code == 201


def test_security_headers(client):
    res = client.get("/")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in res.headers["Content-Security-Policy"]


def test_admin_responses_not_cached(admin_client):
    assert admin_client.get("/api/admin/me").headers["Cache-Control"] == "no-store"
    assert admin_client.get("/admin").headers["Cache-Control"] == "no-store"


def test_favicon(client):
    res = client.get("/favicon.ico", follow_redirects=False)
    assert res.status_code == 301
    assert client.get("/static/favicon.svg").status_code == 200


def test_dashboard_shows_recent_inquiries(admin_client):
    admin_client.post("/api/inquiries", data=interior(name="Recent Person"))
    html = admin_client.get("/admin").text
    assert "Latest inquiries" in html and "Recent Person" in html


def test_api_method_not_allowed_is_json(client):
    res = client.delete("/api/sections")
    assert res.status_code == 405
    assert res.json()["error"]["code"] == "method_not_allowed"
