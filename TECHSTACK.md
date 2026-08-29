# Kaagaz2Code — Tech Stack Documentation

> **Project**: SIH26018 — Kaagaz2Code
> **Type**: Document Digitization / Handwritten-to-Code Conversion Platform
> **Architecture**: Fullstack Monorepo (Frontend + Backend + Infra)

---

## Overview

Kaagaz2Code is a document digitization platform that converts scanned/handwritten documents into structured digital output. The stack is split into a **React TypeScript frontend**, a **Python FastAPI backend**, and a **Docker-managed infrastructure layer**.

---

## Frontend

| Category    | Technology              | Version           |
|-------------|-------------------------|-------------------|
| Framework   | React                   | ^19.2.8           |
| Language    | TypeScript              | ~6.0.2            |
| Build Tool  | Vite                    | ^8.2.2            |
| Styling     | Tailwind CSS            | ^4.3.3            |
| Routing     | React Router DOM        | ^7.18.2           |
| Maps        | Leaflet + react-leaflet | ^1.9.4 / ^5.0.0   |
| Linter      | oxlint                  | ^1.79.0           |

### Key Notes
- **Vite** bundler with `@vitejs/plugin-react` for fast HMR.
- **Tailwind CSS v4** integrated via the `@tailwindcss/vite` plugin.
- **Leaflet** for map-based document/location features.
- Strict TypeScript config with separate `tsconfig.app.json` and `tsconfig.node.json`.

---

## Backend

| Category      | Technology                     | Version        |
|---------------|--------------------------------|----------------|
| Framework     | FastAPI                        | >=0.115, <1.0  |
| Language      | Python                         | 3.x            |
| ASGI Server   | Uvicorn (standard extras)      | >=0.30         |
| ORM           | SQLAlchemy                     | >=2.0, <3.0    |
| Migrations    | Alembic                        | >=1.13         |
| DB Driver     | psycopg2-binary                | >=2.9          |
| Validation    | Pydantic v2                    | >=2.7          |
| Settings      | pydantic-settings              | >=2.3          |
| Auth (JWT)    | python-jose[cryptography]      | >=3.3          |
| Password Hash | passlib[bcrypt] + bcrypt       | >=1.7 / ==4.0.1|
| File Uploads  | python-multipart               | >=0.0.9        |

### Key Notes
- **FastAPI** + **Pydantic v2** for type-safe request/response handling.
- **SQLAlchemy 2.0** ORM with **Alembic** for schema migrations.
- JWT-based auth via `python-jose`; passwords hashed with `passlib + bcrypt`.
- `bcrypt==4.0.1` pinned — passlib is incompatible with bcrypt >= 4.1.
- `python-multipart` enables file/form uploads for document ingestion.

---

## Infrastructure

All local infrastructure is managed via **Docker Compose**.

| Service       | Image                 | Port(s)     | Purpose                             |
|---------------|-----------------------|-------------|-------------------------------------|
| PostgreSQL 16 | postgres:16-alpine    | 5432        | Primary relational database         |
| MinIO         | minio/minio:latest    | 9000 / 9001 | S3-compatible object storage (docs) |
| Adminer       | adminer:latest        | 8081->8080  | Web-based DB admin UI               |
| Backend API   | Local Dockerfile      | 8000        | FastAPI app container               |

### Key Notes
- **MinIO** acts as local S3-compatible store for raw scanned docs and processed derivatives.
  In production, point `OBJECT_STORAGE_*` env vars at a real cloud bucket (AWS S3, GCS, etc.).
- **Adminer** available at `http://localhost:8081` for quick DB inspection.
- Backend container mounts `./app` and `./alembic` for live-reload in dev.

---

## Dev Tooling & Quality

| Tool             | Purpose                           |
|------------------|-----------------------------------|
| pytest           | Backend unit & integration tests  |
| pytest-asyncio   | Async test support                |
| httpx            | HTTP client for API tests         |
| ruff             | Fast Python linter                |
| black            | Python code formatter             |
| pre-commit       | Git hook enforcement              |
| oxlint           | Fast JS/TS linter (frontend)      |

---

## Project Structure

```
SIH26018-Kaagaz2Code/
├── backend/
│   ├── app/                  # FastAPI application source
│   ├── alembic/              # DB migration scripts
│   ├── scripts/              # Utility scripts (e.g., seed_users.py)
│   ├── tests/                # pytest test suite
│   ├── requirements.txt      # Python dependencies
│   ├── docker-compose.yml    # Local infra (Postgres, MinIO, Adminer)
│   ├── Dockerfile            # Backend container definition
│   ├── Makefile              # Dev shortcuts
│   └── .env / .env.example   # Environment config
└── frontend/
    ├── src/                  # React app source
    │   └── pages/            # Page components (e.g., LoginPage.tsx)
    ├── public/               # Static assets
    ├── package.json          # Node dependencies
    ├── vite.config.ts        # Vite configuration
    └── tsconfig.json         # TypeScript config
```

---

## Environment Variables

Configured via `backend/.env` (see `.env.example`):

| Variable                  | Description                        |
|---------------------------|------------------------------------|
| `DATABASE_URL`            | PostgreSQL connection string       |
| `OBJECT_STORAGE_ENDPOINT` | MinIO / S3 endpoint URL            |
| `OBJECT_STORAGE_*`        | Bucket credentials and config      |
| JWT secret / settings     | Auth token signing configuration   |

---

*Last updated: August 2026*
