# Kaagaz2Code Backend — developer convenience targets
# Run from the backend/ directory with: make <target>
# These targets are thin wrappers; they do not change what the underlying
# commands actually do.

.PHONY: dev migrate seed test

dev:
	.\venv\Scripts\uvicorn app.main:app --reload --reload-dir app

migrate:
	.\venv\Scripts\alembic upgrade head

seed:
	.\venv\Scripts\python scripts/seed_users.py

test:
	.\venv\Scripts\pytest
