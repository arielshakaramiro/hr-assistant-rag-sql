"""Auth journey tests (TESTING.md Auth feature). Run against the seeded demo data.

Demo credentials come from the seed; these prove sign-in, a generic wrong-password
message, 401 on a protected route, and that logout invalidates the session.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import requires_db

client = TestClient(app)

MAYA = {"email": "maya@example.com", "password": "demo-maya"}


@requires_db
def test_login_happy_path_sets_session_and_me_works() -> None:
    r = client.post("/api/v1/auth/login", json=MAYA)
    assert r.status_code == 200
    assert r.json()["success"] is True
    # The session cookie lets /me resolve the signed-in employee.
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["full_name"] == "Maya Putri"
    client.post("/api/v1/auth/logout")


@requires_db
def test_wrong_password_is_generic_and_rejected() -> None:
    fresh = TestClient(app)
    r = fresh.post("/api/v1/auth/login", json={"email": MAYA["email"], "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"]["message"] == "Email or password is incorrect."
    # No session was set.
    assert fresh.get("/api/v1/auth/me").status_code == 401


@requires_db
def test_unknown_email_same_message() -> None:
    fresh = TestClient(app)
    r = fresh.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert r.status_code == 401
    assert r.json()["detail"]["message"] == "Email or password is incorrect."


@requires_db
def test_protected_route_requires_auth() -> None:
    fresh = TestClient(app)
    assert fresh.get("/api/v1/auth/me").status_code == 401


@requires_db
def test_logout_invalidates_session() -> None:
    c = TestClient(app)
    c.post("/api/v1/auth/login", json=MAYA)
    assert c.get("/api/v1/auth/me").status_code == 200
    c.post("/api/v1/auth/logout")
    assert c.get("/api/v1/auth/me").status_code == 401


@requires_db
def test_login_rate_limited_after_many_attempts() -> None:
    # Uses a unique unknown email so it does not consume another test's budget.
    c = TestClient(app)
    email = "ratelimit-probe@example.com"
    statuses = [
        c.post("/api/v1/auth/login", json={"email": email, "password": "x"}).status_code
        for _ in range(12)
    ]
    # First 10 are rejected 401 (bad creds); the 11th+ are rate-limited 429.
    assert 429 in statuses, f"expected a 429 after the limit, got {statuses}"
