#!/usr/bin/env python3
"""
Seed script: creates one dev user per role.

Run from the project root (backend/):
    python scripts/seed_users.py

Credentials created:
    citizen@kaagaz.dev   / Citizen@123   (role: citizen)
    officer@kaagaz.dev   / Officer@123   (role: officer)
    reviewer@kaagaz.dev  / Reviewer@123  (role: reviewer)
    admin@kaagaz.dev     / Admin@123     (role: admin)

This script is idempotent: it skips users that already exist.
NEVER run against a production database.
"""

import sys
from pathlib import Path

# Make the `app` package importable when run from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import get_password_hash
from app.db.database import SessionLocal
from app.db.models.user import User

_SEED_USERS = [
    {
        "email": "citizen@kaagaz.dev",
        "full_name": "Dev Citizen",
        "password": "Citizen@123",
        "role": "citizen",
    },
    {
        "email": "officer@kaagaz.dev",
        "full_name": "Dev Officer",
        "password": "Officer@123",
        "role": "officer",
    },
    {
        "email": "reviewer@kaagaz.dev",
        "full_name": "Dev Reviewer",
        "password": "Reviewer@123",
        "role": "reviewer",
    },
    {
        "email": "admin@kaagaz.dev",
        "full_name": "Dev Admin",
        "password": "Admin@123",
        "role": "admin",
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        created = 0
        skipped = 0
        for u in _SEED_USERS:
            exists = db.query(User).filter(User.email == u["email"]).first()
            if exists:
                print(f"  SKIP  {u['email']} (already exists)")
                skipped += 1
                continue

            user = User(
                email=u["email"],
                full_name=u["full_name"],
                hashed_password=get_password_hash(u["password"]),
                role=u["role"],
                is_active=True,
            )
            db.add(user)
            print(f"  CREATE {u['email']} (role={u['role']})")
            created += 1

        db.commit()
        print(f"\nDone: {created} created, {skipped} skipped.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
