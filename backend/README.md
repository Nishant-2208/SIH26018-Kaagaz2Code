# Kaagaz2Code Backend (SIH26018)

Smart Land Record Digitization — backend API.

FastAPI + PostgreSQL (SQLAlchemy + Alembic) + S3-compatible object storage,
built to serve the existing React/Vite frontend.

## Status

**Phase 1 complete:** project foundation — FastAPI app, config, DB
connection, Alembic wired up, Docker Compose for local infra, health checks.

Everything else (auth, documents, OCR/AI pipeline, review, audit, citizen
portal, dashboard) is implemented in later phases — see the project's
development plan.

## Local setup

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
```

This starts PostgreSQL, MinIO (S3-compatible object storage), Adminer (DB
UI), and the backend itself.

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/api/v1/docs
- Adminer (DB UI): http://localhost:8081 (system: PostgreSQL, server:
  `postgres`, user/pass: `kaagaz2code`/`kaagaz2code`, db: `kaagaz2code`)
- MinIO console: http://localhost:9001 (`minioadmin` / `minioadmin`)

### Option B — Run locally without Docker

Requires a running PostgreSQL instance.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL to point at your local Postgres

uvicorn app.main:app --reload
```

## Database migrations (Alembic)

```bash
# generate a migration from current models
alembic revision --autogenerate -m "description of change"

# apply migrations
alembic upgrade head

# roll back one migration
alembic downgrade -1
```

Never let the app auto-create tables at startup — all schema changes go
through Alembic migrations.

## Verifying the setup

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/db
```

Both should return `{"status": "ok", ...}`.

## Project structure

```
app/
├── main.py                 FastAPI app factory, middleware, router registration
├── api/routes/              One module per API domain (auth, documents, ...)
├── core/                     config.py (env-based settings), logging.py
├── db/
│   ├── database.py          SQLAlchemy engine/session, Base, get_db()
│   └── models/               ORM models, one module per entity group
├── schemas/                  Pydantic request/response schemas
├── services/                  Business logic, one service per domain
├── integrations/
│   ├── ocr/                  OCR provider adapters (pluggable)
│   └── ai/                   AI extraction provider adapters (pluggable)
└── utils/
alembic/                       Migration scripts
tests/
├── unit/
├── integration/
└── api/
```

## Environment variables

See `.env.example` for the full list (database, JWT, object storage, OCR/AI
provider selection, auto-approval thresholds, upload limits, CORS). Never
commit a real `.env` file.
