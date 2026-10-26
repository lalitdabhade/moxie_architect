from tests.conftest import TEST_UPLOAD_DIR
from tests.test_projects import JPEG, PNG

PDF = b"%PDF-1.4\n" + b"0" * 200

BASE = {
    "name": "Asha Kulkarni",
    "mobile": "9876543210",
    "email": "asha@Example.COM",
    "address": "Flat 4, Padma Madhav, Kothrud, Pune",
}


def interior(**overrides):
    return {**BASE, "service_type": "interior", "house_type": "2bhk", "budget_range": "10_20l", **overrides}


def bungalow(**overrides):
    return {**BASE, "service_type": "bungalow_apartment", "area_sqft": "2400", "budget_range": "above_50l",
            **overrides}


def layout_files():
    return sorted(p.name for p in (TEST_UPLOAD_DIR / "layouts").iterdir())


def submit(client, data, layout=None):
    files = {"layout": layout} if layout else None
    return client.post("/api/inquiries", data=data, files=files)


# ---------- public submission ----------

def test_interior_inquiry_saved(admin_client):
    res = submit(admin_client, interior())
    assert res.status_code == 201, res.text
    assert "Thank you" in res.json()["message"]
    q = admin_client.get(f"/api/admin/inquiries/{res.json()['inquiry']['id']}").json()["inquiry"]
    assert q["email"] == "asha@example.com"  # domain normalised
    assert q["house_type_label"] == "2 BHK"
    assert q["area_sqft"] is None and q["layout"] is None


def test_interior_other_requires_text(client):
    res = submit(client, interior(house_type="other"))
    assert res.status_code == 422
    assert set(res.json()["error"]["fields"]) == {"house_type_other"}
    assert submit(client, interior(house_type="other", house_type_other="Penthouse")).status_code == 201


def test_bungalow_inquiry_with_pdf_layout(admin_client):
    res = submit(admin_client, bungalow(), ("site plan.pdf", PDF, "application/pdf"))
    assert res.status_code == 201, res.text
    q = admin_client.get(f"/api/admin/inquiries/{res.json()['inquiry']['id']}").json()["inquiry"]
    assert q["area_sqft"] == 2400 and q["house_type"] is None
    assert q["layout"]["filename"] == "site plan.pdf"
    stored = layout_files()
    assert len(stored) == 1 and stored[0].endswith(".pdf") and "site" not in stored[0]  # randomized


def test_bungalow_accepts_jpg_and_png(client):
    assert submit(client, bungalow(), ("plan.jpg", JPEG, "image/jpeg")).status_code == 201
    assert submit(client, bungalow(), ("plan.png", PNG, "image/png")).status_code == 201


def test_bungalow_requires_area_and_layout(client):
    res = submit(client, bungalow(area_sqft=""))
    assert res.status_code == 422
    assert set(res.json()["error"]["fields"]) == {"area_sqft", "layout"}


def test_layout_type_checked_by_content(client):
    res = submit(client, bungalow(), ("plan.pdf", JPEG, "application/pdf"))
    assert res.status_code == 415
    res = submit(client, bungalow(), ("plan.webp", b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 50, "image/webp"))
    assert res.status_code == 415
    res = submit(client, bungalow(), ("evil.pdf", b"MZ\x90\x00" + b"0" * 50, "application/pdf"))
    assert res.status_code == 415
    assert layout_files() == []


def test_layout_size_limit(client):
    big = PDF + b"0" * (10 * 1024 * 1024)
    res = submit(client, bungalow(), ("big.pdf", big, "application/pdf"))
    assert res.status_code == 413
    assert layout_files() == []


def test_other_branch_fields_are_ignored(admin_client):
    # Interior submission carrying bungalow fields and a file: they must not be stored.
    res = submit(admin_client, interior(area_sqft="999"), ("plan.pdf", PDF, "application/pdf"))
    assert res.status_code == 201
    q = admin_client.get(f"/api/admin/inquiries/{res.json()['inquiry']['id']}").json()["inquiry"]
    assert q["area_sqft"] is None and q["layout"] is None
    assert layout_files() == []


def test_common_field_validation(client):
    res = submit(client, {"name": "A", "mobile": "12345", "email": "not-an-email", "address": "x",
                          "service_type": "plumbing", "budget_range": "free"})
    assert res.status_code == 422
    fields = res.json()["error"]["fields"]
    assert set(fields) == {"name", "mobile", "email", "address", "service_type", "budget_range"}
    assert "10-digit" in fields["mobile"]


def test_mobile_must_be_exactly_ten_digits(client):
    assert submit(client, interior(mobile="98765 43210")).status_code == 201  # spaces stripped
    for bad in ("98765432101", "98765abc10", "+919876543210"):
        assert submit(client, interior(mobile=bad)).status_code == 422


def test_area_bounds(client):
    for bad in ("10", "abc", "2400.5", "-5", "99999999"):
        res = submit(client, bungalow(area_sqft=bad), ("p.pdf", PDF, "application/pdf"))
        assert res.status_code == 422, bad


def test_honeypot_discards_silently(admin_client):
    res = submit(admin_client, interior(website="http://spam.example"))
    assert res.status_code == 201
    assert admin_client.get("/api/admin/inquiries").json()["total"] == 0


def test_inquiry_rate_limit(client):
    for _ in range(10):
        assert submit(client, interior()).status_code == 201
    res = submit(client, interior())
    assert res.status_code == 429
    assert "Retry-After" in res.headers


def test_inquiry_options(client):
    data = client.get("/api/inquiry-options").json()
    assert [o["value"] for o in data["service_types"]] == ["interior", "bungalow_apartment"]
    assert [o["label"] for o in data["budget_ranges"]] == ["Under 5L", "5-10L", "10-20L", "20-50L", "Above 50L"]


def test_inquiry_page_renders(client):
    html = client.get("/inquiry").text
    assert 'id="inquiry-form"' in html and "/static/js/inquiry.js" in html
    assert 'href="/inquiry" aria-current="page"' in html


# ---------- admin ----------

def test_admin_inquiry_api_requires_login(client):
    assert client.get("/api/admin/inquiries").status_code == 401
    res = submit(client, bungalow(), ("plan.pdf", PDF, "application/pdf"))
    assert client.get(f"/api/admin/inquiries/{res.json()['inquiry']['id']}/layout").status_code == 401


def test_layouts_never_served_publicly(client):
    submit(client, bungalow(), ("plan.pdf", PDF, "application/pdf"))
    stored = layout_files()[0]
    assert client.get(f"/uploads/layouts/{stored}").status_code == 404
    assert client.get(f"/uploads/projects/../layouts/{stored}").status_code == 404


def test_admin_list_newest_first_and_filter(admin_client):
    submit(admin_client, interior(name="First Person"))
    submit(admin_client, bungalow(name="Second Person"), ("p.pdf", PDF, "application/pdf"))
    submit(admin_client, interior(name="Third Person"))
    data = admin_client.get("/api/admin/inquiries").json()
    assert [q["name"] for q in data["inquiries"]] == ["Third Person", "Second Person", "First Person"]
    assert data["counts"] == {"interior": 2, "bungalow_apartment": 1}
    only = admin_client.get("/api/admin/inquiries?service_type=bungalow_apartment").json()
    assert [q["name"] for q in only["inquiries"]] == ["Second Person"]
    assert admin_client.get("/api/admin/inquiries?service_type=nope").status_code == 422


def test_admin_download_layout(admin_client):
    res = submit(admin_client, bungalow(), ("My Plan.pdf", PDF, "application/pdf"))
    qid = res.json()["inquiry"]["id"]
    dl = admin_client.get(f"/api/admin/inquiries/{qid}/layout")
    assert dl.status_code == 200
    assert dl.content == PDF
    assert dl.headers["content-type"] == "application/pdf"
    assert "attachment" in dl.headers["content-disposition"] and "My%20Plan.pdf" in dl.headers["content-disposition"]


def test_admin_download_404_without_layout(admin_client):
    qid = submit(admin_client, interior()).json()["inquiry"]["id"]
    assert admin_client.get(f"/api/admin/inquiries/{qid}/layout").status_code == 404


def test_admin_delete_inquiry_removes_layout(admin_client):
    qid = submit(admin_client, bungalow(), ("p.pdf", PDF, "application/pdf")).json()["inquiry"]["id"]
    assert len(layout_files()) == 1
    token = admin_client.headers.pop("X-CSRF-Token")
    assert admin_client.delete(f"/api/admin/inquiries/{qid}").status_code == 403  # CSRF required
    admin_client.headers["X-CSRF-Token"] = token
    assert admin_client.delete(f"/api/admin/inquiries/{qid}").status_code == 200
    assert layout_files() == []
    assert admin_client.get(f"/api/admin/inquiries/{qid}").status_code == 404


def test_admin_inquiry_pages_render_and_escape(admin_client):
    qid = submit(admin_client, interior(name="<b>Bold</b> Name", house_type="other",
                                        house_type_other="<script>x</script>")).json()["inquiry"]["id"]
    listing = admin_client.get("/admin/inquiries")
    assert listing.status_code == 200
    assert "<b>Bold</b>" not in listing.text and "&lt;b&gt;Bold&lt;/b&gt;" in listing.text
    detail = admin_client.get(f"/admin/inquiries/{qid}")
    assert detail.status_code == 200 and "<script>x</script>" not in detail.text
    assert admin_client.get("/admin/inquiries?service_type=interior").status_code == 200
    assert admin_client.get("/admin/inquiries/99999").status_code == 404


def test_admin_pagination(admin_client):
    from app.security import inquiry_limiter
    for i in range(27):
        inquiry_limiter.clear()
        submit(admin_client, interior(name=f"Person {i:02d}"))
    page1 = admin_client.get("/api/admin/inquiries").json()
    assert page1["pages"] == 2 and len(page1["inquiries"]) == 25
    page2 = admin_client.get("/api/admin/inquiries?page=2").json()
    assert [q["name"] for q in page2["inquiries"]] == ["Person 01", "Person 00"]
