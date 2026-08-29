# Kaagaz2Code — SIH26018

> **Smart Land Record Digitization Platform**
> Convert scanned / handwritten land documents into structured, searchable digital records using OCR and AI extraction.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [Option A — Docker Compose (Recommended)](#option-a--docker-compose-recommended)
  - [Option B — Manual Local Setup](#option-b--manual-local-setup)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Useful URLs (Local Dev)](#useful-urls-local-dev)
- [Make Targets (Backend)](#make-targets-backend)
- [Running Tests](#running-tests)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)

---

## Overview

Kaagaz2Code is a fullstack monorepo built for **Smart India Hackathon 2026 (Problem Statement SIH26018)**. It provides a pipeline to:

1. **Upload** scanned or photographed land record documents (PDFs, images).
2. **Extract** text and structured fields via a pluggable OCR + AI pipeline.
3. **Review** extracted data with confidence scores and flag low-confidence fields for human verification.
4. **Store** both raw documents and processed records securely.
5. **Serve** a citizen and officer portal via a modern React frontend.

---

## Features

- 📄 **Multi-format document ingestion** — PDF, PNG, JPEG, TIFF (up to 20 MB per file)
- 🔍 **Pluggable OCR** — swap providers via a single env variable (`OCR_PROVIDER`)
- 🤖 **AI field extraction** — structured extraction of critical fields (`owner_name`, `survey_number`, `khata_number`, `village`, etc.)
- ✅ **Confidence-based auto-approval** — configurable thresholds; low-confidence fields are routed for manual review
- 🔐 **JWT authentication** — access + refresh token flow, bcrypt password hashing
- 🗺️ **Map integration** — Leaflet-based location features in the frontend
- 🐳 **Fully containerized** — one `docker compose up` spins up all services
- 🧪 **Test suite** — pytest with async support and HTTPX for API-level tests

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser / Client                     │
│           React 19 + TypeScript + Vite + Tailwind       │
│                    (port 5173 in dev)                   │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / REST
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                       │
│          Python 3.x · Uvicorn · Pydantic v2             │
│                    (port 8000)                          │
└──────────┬─────────────────────────────┬────────────────┘
           │ SQLAlchemy / psycopg2        │ S3 API
┌──────────▼──────────┐       ┌──────────▼───────────────┐
│   PostgreSQL 16     │       │   MinIO (object storage) │
│     (port 5432)     │       │   ports 9000 / 9001      │
└─────────────────────┘       └──────────────────────────┘
```

---

## Project Structure

```
SIH26018-Kaagaz2Code/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, middleware, routers
│   │   ├── api/routes/           # One module per API domain (auth, documents, …)
│   │   ├── core/                 # config.py (env settings), logging.py
│   │   ├── db/
│   │   │   ├── database.py       # SQLAlchemy engine/session, Base, get_db()
│   │   │   └── models/           # ORM models, one module per entity group
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Business logic, one service per domain
│   │   ├── integrations/
│   │   │   ├── ocr/              # OCR provider adapters (pluggable)
│   │   │   └── ai/               # AI extraction provider adapters (pluggable)
│   │   └── utils/
│   ├── alembic/                  # DB migration scripts
│   ├── scripts/                  # Utility scripts (e.g., seed_users.py)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── api/
│   ├── requirements.txt
│   ├── docker-compose.yml        # Local infra (Postgres, MinIO, Adminer, API)
│   ├── Dockerfile
│   ├── Makefile                  # Dev shortcuts
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/                  # API client layer
    │   ├── components/           # Reusable UI components
    │   ├── pages/                # Page-level components (e.g., LoginPage.tsx)
    │   └── assets/               # Static assets
    ├── public/
    ├── package.json
    ├── vite.config.ts
    └── tsconfig.json
```

---

## Prerequisites

| Tool | Minimum Version | Notes |
|------|----------------|-------|
| Docker + Docker Compose | 24+ | Recommended path |
| Node.js | 18+ | For frontend development |
| Python | 3.10+ | For backend without Docker |
| Make | any | Optional; for `make` shortcuts |

---

## Getting Started

### Option A — Docker Compose (Recommended)

> Spins up PostgreSQL, MinIO, Adminer, and the FastAPI backend in one command.

```bash
# 1. Clone the repo
git clone https://github.com/Nishant-2208/SIH26018-Kaagaz2Code.git
cd SIH26018-Kaagaz2Code

# 2. Configure the backend environment
cd backend
cp .env.example .env
# Edit .env to set a strong JWT_SECRET and any other values

# 3. Start all services
docker compose up --build
```

**Frontend (separate terminal):**

```bash
cd frontend
npm install
npm run dev
```

---

### Option B — Manual Local Setup

> Requires a running PostgreSQL instance on your machine.

**Backend:**

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set DATABASE_URL to point at your local Postgres instance

# Apply database migrations
alembic upgrade head

# (Optional) Seed default users
python scripts/seed_users.py

# Start the dev server
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Copy `backend/.env.example` → `backend/.env` and fill in the values. **Never commit a real `.env` file.**

| Variable | Description | Default (example) |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg2://kaagaz2code:kaagaz2code@localhost:5432/kaagaz2code` |
| `JWT_SECRET` | Secret key for signing JWT tokens | *(must be changed)* |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `60` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `7` |
| `OBJECT_STORAGE_ENDPOINT` | MinIO / S3 endpoint | `http://localhost:9000` |
| `OBJECT_STORAGE_ACCESS_KEY` | Object storage access key | `minioadmin` |
| `OBJECT_STORAGE_SECRET_KEY` | Object storage secret key | `minioadmin` |
| `OBJECT_STORAGE_BUCKET` | Bucket name | `kaagaz2code-documents` |
| `OCR_PROVIDER` | OCR backend to use (`mock`, etc.) | `mock` |
| `AI_PROVIDER` | AI extraction backend (`mock`, etc.) | `mock` |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Claude) | *(empty)* |
| `MIN_FIELD_CONFIDENCE` | Confidence threshold for auto-approval | `0.85` |
| `CRITICAL_FIELDS` | Comma-separated list of critical field names | `owner_name,survey_number,…` |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload file size | `20` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

---

## Database Migrations

All schema changes must go through **Alembic** — the app never auto-creates tables at startup.

```bash
# Generate a migration from current SQLAlchemy models
alembic revision --autogenerate -m "your description here"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

---

## Useful URLs (Local Dev)

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | — |
| Backend API | http://localhost:8000 | — |
| Swagger / OpenAPI | http://localhost:8000/api/v1/docs | — |
| Adminer (DB UI) | http://localhost:8081 | system: `PostgreSQL`, server: `postgres`, user/pass: `kaagaz2code` / `kaagaz2code`, db: `kaagaz2code` |
| MinIO Console | http://localhost:9001 | `minioadmin` / `minioadmin` |

**Health checks:**

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/db
# Both should return {"status": "ok", ...}
```

---

## Make Targets (Backend)

Run from the `backend/` directory:

```bash
make dev      # Start uvicorn with --reload
make migrate  # Apply Alembic migrations (upgrade head)
make seed     # Run seed_users.py
make test     # Run the full pytest suite
```

---

## Running Tests

```bash
cd backend

# Activate the virtual environment first
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # macOS / Linux

pytest
# Or using make:
make test
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4, React Router DOM, Leaflet |
| **Backend** | Python 3.x, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0, Alembic |
| **Auth** | JWT (python-jose), bcrypt (passlib) |
| **Database** | PostgreSQL 16 |
| **Object Storage** | MinIO (local) / S3-compatible (production) |
| **Containerization** | Docker, Docker Compose |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Linting / Formatting** | ruff, black (Python) · oxlint (TypeScript) |
| **Git Hooks** | pre-commit |

> See [TECHSTACK.md](./TECHSTACK.md) for detailed version pinning and notes.

---

## Contributing

1. Fork the repository and create a feature branch (`git checkout -b feat/your-feature`).
2. Follow the existing code style — `ruff` / `black` for Python, `oxlint` for TypeScript.
3. Write or update tests for any changed behaviour.
4. Open a pull request with a clear description of changes.

---

*Last updated: August 2026 · SIH26018 — Smart India Hackathon*
