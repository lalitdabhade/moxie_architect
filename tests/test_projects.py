from app.config import settings
from tests.conftest import TEST_UPLOAD_DIR

# Minimal byte strings that start with the right file signatures (server sniffs content).
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 200
GIF = b"GIF89a" + b"\x00" * 200


def project_files():
    return sorted(p.name for p in (TEST_UPLOAD_DIR / "projects").iterdir())


def create(client, section="1", title="Padma Madhav, Kothrud (2 BHK)", files=None):
    files = files if files is not None else [("images", ("a.jpg", JPEG, "image/jpeg")),
                                             ("images", ("b.png", PNG, "image/png"))]
    return client.post("/api/admin/projects", data={"section_id": section, "title": title}, files=files)


def test_uses_temp_upload_dir():
    assert settings.upload_dir == TEST_UPLOAD_DIR


def test_create_project_requires_login(client):
    res = create(client)
    assert res.status_code == 401
    assert project_files() == []


def test_create_project_requires_csrf(admin_client):
    token = admin_client.headers.pop("X-CSRF-Token")
    assert create(admin_client).status_code == 403
    admin_client.headers["X-CSRF-Token"] = token


def test_create_project_with_images(admin_client):
    res = create(admin_client)
    assert res.status_code == 201, res.text
    project = res.json()["project"]
    assert project["title"] == "Padma Madhav, Kothrud (2 BHK)"
    assert project["section"]["slug"] == "residential-interior"
    assert [img["sort_order"] for img in project["images"]] == [0, 1]
    names = project_files()
    assert len(names) == 2
    assert all(n.startswith(f"residential-padma-madhav-kothrud-2-bhk-{project['id']}-") for n in names)
    # Images are publicly served.
    url = project["images"][0]["url"]
    assert admin_client.get(url).content == JPEG


def test_create_validation_errors(admin_client):
    res = create(admin_client, section="9", title=" ", files=[])
    assert res.status_code == 422
    fields = res.json()["error"]["fields"]
    assert set(fields) == {"section_id", "title", "images"}


def test_rejects_wrong_content_even_with_image_extension(admin_client):
    res = create(admin_client, files=[("images", ("fake.jpg", GIF, "image/jpeg"))])
    assert res.status_code == 415
    assert project_files() == []


def test_rejects_extension_mismatch(admin_client):
    res = create(admin_client, files=[("images", ("photo.png", JPEG, "image/png"))])
    assert res.status_code == 415


def test_rejects_disallowed_extension(admin_client):
    res = create(admin_client, files=[("images", ("doc.pdf", b"%PDF-1.4", "application/pdf"))])
    assert res.status_code == 415


def test_rejects_oversized_image_and_rolls_back(admin_client):
    big = JPEG + b"\x00" * (5 * 1024 * 1024)
    res = create(admin_client, files=[("images", ("ok.png", PNG, "image/png")),
                                      ("images", ("big.jpg", big, "image/jpeg"))])
    assert res.status_code == 413
    assert project_files() == []  # the first, valid file was cleaned up too
    assert admin_client.get("/api/admin/projects").json()["projects"] == []


def test_list_filter_by_section(admin_client):
    create(admin_client, section="1", title="Home One")
    create(admin_client, section="2", title="XYZ Park, Kothrud (Office)")
    all_projects = admin_client.get("/api/admin/projects").json()["projects"]
    assert len(all_projects) == 2
    commercial = admin_client.get("/api/admin/projects?section=commercial-interior").json()["projects"]
    assert [p["title"] for p in commercial] == ["XYZ Park, Kothrud (Office)"]
    assert admin_client.get("/api/admin/projects?section=nope").status_code == 422


def test_edit_title_and_section(admin_client):
    pid = create(admin_client).json()["project"]["id"]
    res = admin_client.patch(f"/api/admin/projects/{pid}", json={"title": "Sai Bungalow, Kothrud (Bungalow)",
                                                                  "section_id": 3})
    assert res.status_code == 200
    assert res.json()["project"]["section"]["id"] == 3
    assert admin_client.patch(f"/api/admin/projects/{pid}", json={"title": ""}).status_code == 422


def test_add_remove_reorder_images(admin_client):
    project = create(admin_client).json()["project"]
    pid = project["id"]
    res = admin_client.post(f"/api/admin/projects/{pid}/images",
                            files=[("images", ("c.webp", WEBP, "image/webp"))])
    assert res.status_code == 201
    images = res.json()["project"]["images"]
    assert len(images) == 3 and images[2]["url"].endswith(".webp")

    ids = [img["id"] for img in images]
    res = admin_client.put(f"/api/admin/projects/{pid}/images/order", json={"image_ids": ids[::-1]})
    assert res.status_code == 200
    assert [img["id"] for img in res.json()["project"]["images"]] == ids[::-1]

    # Order must list every image exactly once.
    bad = admin_client.put(f"/api/admin/projects/{pid}/images/order", json={"image_ids": ids[:2]})
    assert bad.status_code == 422

    res = admin_client.delete(f"/api/admin/projects/{pid}/images/{ids[0]}")
    assert res.status_code == 200
    assert len(res.json()["project"]["images"]) == 2
    assert len(project_files()) == 2


def test_image_from_other_project_cannot_be_deleted(admin_client):
    a = create(admin_client, title="Project A").json()["project"]
    b = create(admin_client, title="Project B").json()["project"]
    res = admin_client.delete(f"/api/admin/projects/{a['id']}/images/{b['images'][0]['id']}")
    assert res.status_code == 404


def test_delete_project_removes_files(admin_client):
    pid = create(admin_client).json()["project"]["id"]
    assert len(project_files()) == 2
    assert admin_client.delete(f"/api/admin/projects/{pid}").status_code == 200
    assert project_files() == []
    assert admin_client.get(f"/api/admin/projects/{pid}").status_code == 404


def test_admin_pages_render(admin_client):
    pid = create(admin_client).json()["project"]["id"]
    assert admin_client.get("/admin/projects").status_code == 200
    assert admin_client.get("/admin/projects?section=residential-interior").status_code == 200
    assert admin_client.get("/admin/projects/new").status_code == 200
    page = admin_client.get(f"/admin/projects/{pid}")
    assert page.status_code == 200 and "project-data" in page.text
    assert admin_client.get("/admin/projects/99999").status_code == 404


def test_title_is_escaped_in_admin_page(admin_client):
    pid = create(admin_client, title="<script>alert(1)</script>").json()["project"]["id"]
    html = admin_client.get(f"/admin/projects/{pid}").text
    assert "<script>alert(1)</script>" not in html
