"""Self-service per-employee reads: correctness and isolation (My leave/Attendance/Claims).

Runs against the seeded production engine (`make up && make seed`). Proves a user reads only
their OWN rows via the new /me/* endpoints — an extra leakage=0 witness alongside
test_isolation.py, which the app role (RLS-bypassing) makes worth asserting here explicitly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import requires_db

MAYA = {"email": "maya@example.com", "password": "demo-maya"}
ADI = {"email": "adi@example.com", "password": "demo-adi"}


def _client_for(creds: dict) -> TestClient:
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json=creds)
    assert r.status_code == 200, r.text
    return c


@requires_db
def test_leave_shows_own_balance_and_records() -> None:
    c = _client_for(MAYA)
    data = c.get("/api/v1/me/leave").json()["data"]
    # Maya: entitlement 12, used 5 → 7 remaining (derived, not stored).
    assert data["entitlement_days"] == 12
    assert data["used_days"] == 5
    assert data["remaining_days"] == 7
    # Three seeded leave records, newest first.
    assert len(data["records"]) == 3
    assert data["records"][0]["start_date"] == "2026-06-20"


@requires_db
def test_attendance_counts_own_rows() -> None:
    c = _client_for(MAYA)
    data = c.get("/api/v1/me/attendance").json()["data"]
    assert data["counts"] == {"present": 2, "late": 1}
    assert len(data["records"]) == 3


@requires_db
def test_claims_shows_own_totals() -> None:
    c = _client_for(MAYA)
    data = c.get("/api/v1/me/claims").json()["data"]
    assert len(data["claims"]) == 2
    assert data["totals_count"] == {"paid": 1, "approved": 1}
    assert data["totals_amount"]["paid"] == 450000.0


@requires_db
def test_isolation_other_employee_rows_never_returned() -> None:
    # Adi sees only his own single claim and no leave records — never Maya's rows.
    c = _client_for(ADI)
    claims = c.get("/api/v1/me/claims").json()["data"]
    assert len(claims["claims"]) == 1
    assert claims["claims"][0]["claim_type"] == "meal"
    assert claims["totals_count"] == {"submitted": 1}
    leave = c.get("/api/v1/me/leave").json()["data"]
    assert leave["records"] == []


@requires_db
def test_unauthenticated_is_rejected() -> None:
    anon = TestClient(app)
    for path in ("/api/v1/me/leave", "/api/v1/me/attendance", "/api/v1/me/claims"):
        r = anon.get(path)
        assert r.status_code == 401, path
        assert r.json()["detail"]["code"] == "UNAUTHENTICATED"
