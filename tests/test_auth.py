from tests.conftest import TEST_PASSWORD, TEST_USER, do_login


def test_home_page_renders(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Residential Interior Design" in res.text
    assert "Content-Security-Policy" in res.headers


def test_dashboard_redirects_when_logged_out(client):
    res = client.get("/admin", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/admin/login"


def test_login_success_sets_httponly_cookie(client):
    res = do_login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["admin"]["username"] == TEST_USER
    assert len(body["csrf_token"]) == 64
    cookie = res.headers["set-cookie"]
    assert "admin_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert client.get("/admin").status_code == 200


def test_login_wrong_password(client):
    res = do_login(client, password="nope-nope")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_user_same_message(client):
    res = do_login(client, username="ghost")
    assert res.status_code == 401
    assert res.json()["error"]["message"] == "Invalid username or password."


def test_login_requires_csrf(client):
    client.get("/admin/login")
    res = client.post("/api/admin/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    assert res.status_code == 403
    res = client.post("/api/admin/login", json={"username": TEST_USER, "password": TEST_PASSWORD},
                      headers={"X-CSRF-Token": "0" * 64})
    assert res.status_code == 403


def test_login_rate_limited(client):
    for _ in range(5):
        assert do_login(client, password="wrong-password").status_code == 401
    res = do_login(client)  # even the right password is blocked now
    assert res.status_code == 429
    assert "Retry-After" in res.headers


def test_me_requires_session(client):
    res = client.get("/api/admin/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthorized"


def test_logout_requires_csrf_and_invalidates_session(admin_client):
    token = admin_client.headers.pop("X-CSRF-Token")
    assert admin_client.post("/api/admin/logout").status_code == 403
    assert admin_client.get("/api/admin/me").status_code == 200

    res = admin_client.post("/api/admin/logout", headers={"X-CSRF-Token": token})
    assert res.status_code == 200
    assert admin_client.get("/api/admin/me").status_code == 401


def test_api_404_is_json(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_page_404_is_html(client):
    res = client.get("/no-such-page")
    assert res.status_code == 404
    assert "text/html" in res.headers["content-type"]


def test_layouts_folder_not_public(client):
    assert client.get("/uploads/layouts/anything.pdf").status_code == 404
