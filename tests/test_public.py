from tests.test_projects import JPEG, PNG, create


def test_sections_api(admin_client):
    create(admin_client, section="2", title="XYZ Park, Kothrud (Office)")
    sections = admin_client.get("/api/sections").json()["sections"]
    assert [s["slug"] for s in sections] == [
        "residential-interior", "commercial-interior", "bungalow-design", "apartment-commercial-complex",
    ]
    assert {s["slug"]: s["project_count"] for s in sections}["commercial-interior"] == 1


def test_section_projects_api_is_public(admin_client, client):
    project = create(admin_client, section="3", title="Sai Bungalow, Kothrud (Bungalow)").json()["project"]
    admin_client.cookies.clear()  # same TestClient: drop the session to act as a visitor
    res = client.get("/api/sections/bungalow-design/projects")
    assert res.status_code == 200
    data = res.json()
    assert data["section"]["name"] == "Bungalow Design"
    assert [p["id"] for p in data["projects"]] == [project["id"]]
    assert len(data["projects"][0]["images"]) == 2
    assert client.get(f"/api/projects/{project['id']}").status_code == 200


def test_unknown_section_api_404(client):
    res = client.get("/api/sections/nope/projects")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_projects_without_images_are_hidden(admin_client):
    project = create(admin_client, section="1", title="Soon").json()["project"]
    for img in project["images"]:
        admin_client.delete(f"/api/admin/projects/{project['id']}/images/{img['id']}")
    assert admin_client.get("/api/sections/residential-interior/projects").json()["projects"] == []
    assert admin_client.get(f"/api/projects/{project['id']}").status_code == 404
    assert "Projects coming soon" in admin_client.get("/residential-interior").text


def test_section_page_renders_carousel(admin_client):
    create(admin_client, section="4", title="Sai Complex, Kothrud (Complex)",
           files=[("images", (f"{i}.jpg", JPEG, "image/jpeg")) for i in range(3)])
    html = admin_client.get("/apartment-commercial-complex").text
    assert "Sai Complex, Kothrud (Complex)" in html
    assert html.count('class="carousel-slide') == 3
    # The first project's cover loads immediately; the other slides are deferred to JS (data-src).
    assert html.count('fetchpriority="high"') == 1
    assert html.count("data-src=") == 2
    assert "/static/js/carousel.js" in html and "/static/js/lightbox.js" in html


def test_only_first_project_cover_is_eager(admin_client):
    for title in ("First", "Second", "Third"):
        create(admin_client, section="1", title=title)
    html = admin_client.get("/residential-interior").text
    assert html.count('fetchpriority="high"') == 1
    assert html.count('loading="lazy"') == 2


def test_single_image_has_no_controls(admin_client):
    create(admin_client, section="1", title="One Photo", files=[("images", ("a.png", PNG, "image/png"))])
    html = admin_client.get("/residential-interior").text
    assert "is-single" in html
    assert "carousel-arrow" not in html


def test_empty_section_page(client):
    for slug in ("residential-interior", "commercial-interior", "bungalow-design", "apartment-commercial-complex"):
        res = client.get(f"/{slug}")
        assert res.status_code == 200
        assert "Projects coming soon" in res.text
        assert "/static/js/carousel.js" not in res.text


def test_project_title_escaped_on_public_page(admin_client):
    create(admin_client, section="2", title='<img src=x onerror="alert(1)">')
    html = admin_client.get("/commercial-interior").text
    assert '<img src=x onerror="alert(1)">' not in html
    assert "&lt;img src=x" in html


def test_nav_marks_current_section(client):
    html = client.get("/bungalow-design").text
    assert 'href="/bungalow-design" aria-current="page"' in html
