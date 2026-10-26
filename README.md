# Architect App

Website and admin panel for an architecture and interior design firm.
FastAPI + PyMySQL + Jinja2, with a JSON REST API under `/api`.

## Run locally (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env          # then edit DB + admin values
.\.venv\Scripts\python.exe -m scripts.seed_admin
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Site: http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/admin
- API docs: http://127.0.0.1:8000/api/docs

Tables are created automatically on startup. To change the admin password, edit `.env` and run the seed script again.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use `DB_NAME_TEST`, which is wiped between tests.
