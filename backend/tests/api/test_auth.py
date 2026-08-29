"""
Auth API tests — pytest + httpx AsyncClient against the real FastAPI ASGI app.

Requires a running PostgreSQL with seeded dev users:
    python scripts/seed_users.py   (or: make seed)

asyncio_mode = "auto" is set in pyproject.toml — no @pytest.mark.asyncio needed.

Cases covered:
  1. Successful login — all 4 seeded roles (citizen, officer, reviewer, admin)
  2. Wrong password → 401
  3. Nonexistent email → 401
  4. Missing token on GET /auth/me → 401
  5. Successful GET /auth/me with a valid access token
  6. Successful POST /auth/refresh
  7. require_roles: citizen rejected from an admin-only endpoint → 403
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE_URL = "http://test"

# Real seeded dev credentials — matches scripts/seed_users.py exactly.
USERS = {
    "citizen": ("citizen@kaagaz.dev", "Citizen@123"),
    "officer": ("officer@kaagaz.dev", "Officer@123"),
    "reviewer": ("reviewer@kaagaz.dev", "Reviewer@123"),
    "admin": ("admin@kaagaz.dev", "Admin@123"),
}


@pytest.fixture
async def client():
    """AsyncClient wired to the FastAPI ASGI app — no real HTTP server needed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helper: log in and return the full token response body
# ---------------------------------------------------------------------------
async def _login(client: AsyncClient, email: str, password: str):
    return await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


# ---------------------------------------------------------------------------
# Case 1 — Successful login for all 4 seeded roles
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["citizen", "officer", "reviewer", "admin"])
async def test_login_success_all_roles(client: AsyncClient, role: str):
    email, password = USERS[role]
    response = await _login(client, email, password)

    assert (
        response.status_code == 200
    ), f"[{role}] Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert "access_token" in body, f"[{role}] Missing access_token"
    assert "refresh_token" in body, f"[{role}] Missing refresh_token"
    assert (
        body["token_type"] == "bearer"
    ), f"[{role}] Wrong token_type: {body['token_type']}"
    assert len(body["access_token"]) > 0, f"[{role}] Empty access_token"
    assert len(body["refresh_token"]) > 0, f"[{role}] Empty refresh_token"


# ---------------------------------------------------------------------------
# Case 2 — Wrong password → 401
# ---------------------------------------------------------------------------
async def test_login_wrong_password(client: AsyncClient):
    email, _ = USERS["citizen"]
    response = await _login(client, email, "definitely-wrong-password")

    assert (
        response.status_code == 401
    ), f"Expected 401, got {response.status_code}: {response.text}"
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Case 3 — Nonexistent email → 401
# ---------------------------------------------------------------------------
async def test_login_nonexistent_email(client: AsyncClient):
    response = await _login(client, "nobody@kaagaz.dev", "SomePassword@123")

    assert (
        response.status_code == 401
    ), f"Expected 401, got {response.status_code}: {response.text}"
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Case 4 — Missing token on GET /auth/me → 401
# ---------------------------------------------------------------------------
async def test_me_missing_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")

    # FastAPI's OAuth2PasswordBearer returns 401 with WWW-Authenticate header
    # when no Bearer token is supplied.
    assert (
        response.status_code == 401
    ), f"Expected 401, got {response.status_code}: {response.text}"
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Case 5 — Successful GET /auth/me with a valid access token
# ---------------------------------------------------------------------------
async def test_me_with_valid_token(client: AsyncClient):
    email, password = USERS["citizen"]

    # Step 1: log in to get a real token
    login_resp = await _login(client, email, password)
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Step 2: call /auth/me with the token
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert (
        me_resp.status_code == 200
    ), f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
    body = me_resp.json()
    assert body["email"] == email
    assert body["role"] == "citizen"
    assert body["is_active"] is True
    assert "id" in body
    assert "full_name" in body
    # hashed_password must never appear in the response
    assert "hashed_password" not in body


# ---------------------------------------------------------------------------
# Case 6 — Successful POST /auth/refresh
# ---------------------------------------------------------------------------
async def test_refresh_success(client: AsyncClient):
    email, password = USERS["citizen"]

    # Step 1: log in to get both tokens
    login_resp = await _login(client, email, password)
    assert login_resp.status_code == 200
    original_refresh = login_resp.json()["refresh_token"]

    # Step 2: exchange refresh token for a new access token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert (
        refresh_resp.status_code == 200
    ), f"Expected 200, got {refresh_resp.status_code}: {refresh_resp.text}"
    body = refresh_resp.json()
    assert "access_token" in body
    assert len(body["access_token"]) > 0
    # The original refresh token must be returned unchanged (per auth.py contract)
    assert body["refresh_token"] == original_refresh

    # Step 3: confirm the new access token actually works on /auth/me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


# ---------------------------------------------------------------------------
# Case 7 — require_roles: citizen rejected from admin-only endpoint → 403
# ---------------------------------------------------------------------------
async def test_require_roles_citizen_rejected_from_admin(client: AsyncClient):
    # Step 1: log in as citizen (lowest privilege role)
    email, password = USERS["citizen"]
    login_resp = await _login(client, email, password)
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Step 2: hit the admin-only endpoint — must be forbidden
    resp = await client.get(
        "/api/v1/health/admin",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    assert "detail" in resp.json()

    # Step 3: sanity-check that admin CAN access it
    admin_email, admin_password = USERS["admin"]
    admin_login = await _login(client, admin_email, admin_password)
    admin_token = admin_login.json()["access_token"]

    admin_resp = await client.get(
        "/api/v1/health/admin",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert (
        admin_resp.status_code == 200
    ), f"Admin should get 200, got {admin_resp.status_code}: {admin_resp.text}"
