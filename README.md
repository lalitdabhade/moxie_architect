# Moxie Architect — website & admin panel

Website for an architecture and interior design firm, with an admin panel and a JSON REST API
under `/api` that a future mobile app can reuse.

- **Public site:** four project sections with auto-sliding image carousels and a full-screen lightbox,
  plus an inquiry form whose fields change with the service chosen.
- **Admin panel** (`/admin`): manage projects and images, read and download inquiries.
- **Stack:** Python · FastAPI · PyMySQL (plain parameterized SQL, no ORM) · Jinja2 · vanilla JS/CSS
  (no frameworks, no build step) · MySQL or MariaDB.

---

## 1. Requirements

- Python 3.12+ (built and tested on 3.15)
- MySQL 8 or MariaDB 10.4+ running locally (XAMPP works)
- A MySQL user that can create a database, or an existing empty database

## 2. Setup (Windows / PowerShell)

```powershell
# from the project folder
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

copy .env.example .env      # then edit .env (see below)

# create the admin account from ADMIN_USERNAME / ADMIN_PASSWORD in .env
.\.venv\Scripts\python.exe -m scripts.seed_admin

# start the server
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

On macOS/Linux use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.

Open:

| What | URL |
|---|---|
| Website | http://127.0.0.1:8000 |
| Admin panel | http://127.0.0.1:8000/admin |
| Interactive API docs | http://127.0.0.1:8000/api/docs |

The database and all tables are created automatically on startup. To change the admin password,
update `.env` and run the seed script again.

## 3. Configuration (`.env`)

`.env` holds secrets and is git-ignored — never commit it.

| Key | Purpose | Example |
|---|---|---|
| `DB_HOST`, `DB_PORT` | MySQL server | `127.0.0.1`, `3306` |
| `DB_USER`, `DB_PASSWORD` | MySQL credentials | |
| `DB_NAME` | App database (created if missing) | `architect_app` |
| `DB_NAME_TEST` | Separate database for tests — **wiped** by the test suite | `architect_app_test` |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Admin account created by `scripts.seed_admin` (password 8–72 bytes) | |
| `SESSION_SECRET` | Random secret, ≥ 32 chars. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | |
| `SESSION_HOURS` | Admin session lifetime | `8` |
| `COOKIE_SECURE` | `true` when served over HTTPS | `false` |
| `UPLOAD_DIR` | *(optional)* where uploads are stored | defaults to `./uploads` |

## 4. Using the site

**Public pages:** `/` (home), `/residential-interior`, `/commercial-interior`, `/bungalow-design`,
`/apartment-commercial-complex`, `/inquiry`.

- A project only appears on the website once it has at least one image. Its first image is the cover.
- The carousel auto-advances every 5 s and pauses on hover, on keyboard focus, when off-screen, and
  for visitors who prefer reduced motion. Swipe on touch screens; click an image for the lightbox.

**Admin panel** (`/admin`):

- **Projects** → *Add project*: choose a section, title, drop in images (JPG/PNG/WEBP, ≤ 5 MB each,
  ≤ 30 per upload), preview, upload.
- Edit a project: change title/section, add images, remove images, reorder by drag-and-drop
  (or the ← → buttons on touch devices), delete the project.
- **Inquiries**: newest first, filter by service type, open for full details, download the
  layout file, delete.

## 5. REST API

All responses are JSON. Errors always look like:

```json
{ "error": { "code": "validation_error", "message": "Please correct the highlighted fields.",
             "fields": { "mobile": "Enter a valid 10-digit mobile number." } } }
```

Status codes used: `400`, `401` (not logged in), `403` (CSRF), `404`, `413` (too large),
`415` (wrong file type), `422` (validation), `429` (rate limited, with `Retry-After`).

### Public

| Method | Path | Notes |
|---|---|---|
| GET | `/api/sections` | The 4 sections with visible project counts |
| GET | `/api/sections/{slug}/projects` | Projects (newest first) with ordered image URLs |
| GET | `/api/projects/{id}` | One project |
| GET | `/api/inquiry-options` | Service types, house types, budget ranges, limits |
| POST | `/api/inquiries` | `multipart/form-data` → `201` (see below) |

`POST /api/inquiries` fields:

- Always: `name`, `mobile` (10 digits), `email`, `address`, `service_type` (`interior` | `bungalow_apartment`), `budget_range`
  (`under_5l`, `5_10l`, `10_20l`, `20_50l`, `above_50l`)
- `interior`: `house_type` (`1bhk`, `2bhk`, `3bhk`, `bungalow`, `other`), plus `house_type_other` when `other`
- `bungalow_apartment`: `area_sqft` (50 – 1,000,000), `layout` file (JPG/PNG/PDF, ≤ 10 MB)

Fields belonging to the other service type are ignored. Limited to 10 submissions per hour per IP.

### Admin (session cookie; send `X-CSRF-Token` on POST/PUT/PATCH/DELETE)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/admin/login` | `{username, password}` → `{admin, csrf_token}` |
| POST | `/api/admin/logout` | |
| GET | `/api/admin/me` | Current admin + CSRF token |
| GET | `/api/admin/projects?section=` | `section` = id or slug |
| POST | `/api/admin/projects` | multipart: `section_id`, `title`, `images` (repeat) |
| GET / PATCH / DELETE | `/api/admin/projects/{id}` | PATCH JSON: `{title?, section_id?}` |
| POST | `/api/admin/projects/{id}/images` | multipart: `images` |
| DELETE | `/api/admin/projects/{id}/images/{image_id}` | |
| PUT | `/api/admin/projects/{id}/images/order` | `{image_ids: [...]}` — every image exactly once |
| GET | `/api/admin/inquiries?service_type=&page=` | 25 per page, newest first |
| GET / DELETE | `/api/admin/inquiries/{id}` | |
| GET | `/api/admin/inquiries/{id}/layout` | Downloads the layout as an attachment |

> **Mobile app note:** admin endpoints currently authenticate with the browser session cookie.
> A token-based login can be added later without changing the endpoint paths.

## 6. Project structure

```
app/
  main.py            app factory, startup (DB + tables), static mounts
  config.py          settings from .env
  db.py, schema.sql  PyMySQL helpers, CREATE TABLE IF NOT EXISTS
  constants.py       sections, choices, size limits
  security.py        bcrypt, sessions, CSRF, rate limiters
  middleware.py      request-size limits, security headers
  uploads.py         content sniffing, streamed size checks, safe filenames
  validation.py      input validation shared by the API
  serializers.py     DB rows -> JSON
  errors.py          consistent JSON errors / HTML error pages
  repositories/      all SQL (admins, sessions, projects, inquiries)
  api/               JSON API (public.py, admin.py)
  web/               server-rendered pages (public_pages.py, admin_pages.py)
  templates/         Jinja2 templates (public/, admin/, partials/)
  static/            css/, js/ (carousel, lightbox, inquiry, admin/*)
scripts/seed_admin.py
tests/               pytest suite (runs against DB_NAME_TEST)
uploads/             git-ignored: projects/ (public), layouts/ (private)
```

## 7. Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The suite uses `DB_NAME_TEST` (wiped between tests) and a temporary upload folder, so it never
touches your real data. It covers login/CSRF/rate limits, project CRUD and image uploads, public
pages and API, inquiry validation for both service types, layout privacy, and request size limits.

## 8. Security summary

- Parameterized SQL only; Jinja2 auto-escaping; strict Content-Security-Policy (no inline scripts).
- Admin sessions are random tokens in an HttpOnly, SameSite=Lax cookie; only a SHA-256 hash is
  stored in the database, and logout deletes the session.
- CSRF token required on every state-changing admin request; the login form has its own signed token.
- Passwords hashed with bcrypt. Login limited to 5 failures per IP+username per 15 minutes.
- Uploads are checked by file signature (not just extension), size-limited while streaming, and
  stored under generated names. Layout files live outside any public mount and are only served
  to logged-in admins.
- Rate limits are in memory, so they reset when the server restarts.

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `Can't connect to MySQL server` on startup | Start MySQL/MariaDB (e.g. XAMPP control panel) and check `DB_HOST`/`DB_PORT`. |
| `Access denied for user` | Check `DB_USER`/`DB_PASSWORD`; the user needs rights on `DB_NAME` (and `DB_NAME_TEST` for tests). |
| `SESSION_SECRET must be set` | Add a 64-character hex secret to `.env` (command above). |
| Server stops responding after a code change with `--reload` | The Windows file-watcher occasionally hangs mid-reload: stop it (Ctrl+C) and start it again. |
| Port 8000 in use | Add `--port 8001` to the uvicorn command. |
