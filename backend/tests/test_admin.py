"""HR-admin team dashboard: authorization and aggregate correctness (PRD F).

Runs against the seeded production engine (`make up && make seed`). The admin surface reads
whole-company aggregates on the app role; the employee isolation path (test_isolation.py) is
unchanged and must still pass — that is the leakage=0 gate.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import requires_db

ADMIN = {"email": "hr@example.com", "password": "demo-hr"}
MAYA = {"email": "maya@example.com", "password": "demo-maya"}

TEAM_URL = "/api/v1/admin/team"


def _client_for(creds: dict) -> TestClient:
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json=creds)
    assert r.status_code == 200, r.text
    return c


@requires_db
def test_admin_sees_team_overview() -> None:
    c = _client_for(ADMIN)
    r = c.get(TEAM_URL)
    assert r.status_code == 200, r.text
    data = r.json()["data"]

    # Headcount and departments (three seeded employees across three departments).
    assert data["headcount"] == 3
    assert set(data["by_department"]) == {"Engineering", "Finance", "People"}

    # Leave totals: 12+12+12 entitlement, 5+2+0 used → 29 remaining, one pending request (Maya).
    assert data["leave"] == {
        "entitlement_days": 36,
        "used_days": 7,
        "remaining_days": 29,
        "pending_requests": 1,
    }

    # Attendance and claims grouped by status (hand-worked from seed).
    assert data["attendance"] == {"present": 3, "late": 1}
    assert data["claims_count"] == {"paid": 1, "approved": 1, "submitted": 1}

    # Roster: one row per employee, sorted by name, with derived remaining leave.
    roster = data["roster"]
    assert [row["full_name"] for row in roster] == [
        "Adi Santoso",
        "Maya Putri",
        "Rina Hartono",
    ]
    maya_row = next(row for row in roster if row["full_name"] == "Maya Putri")
    assert maya_row["remaining_days"] == 7  # 12 − 5, derived not stored


@requires_db
def test_normal_employee_is_forbidden() -> None:
    c = _client_for(MAYA)
    r = c.get(TEAM_URL)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "FORBIDDEN"


@requires_db
def test_unauthenticated_is_rejected() -> None:
    r = TestClient(app).get(TEAM_URL)
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHENTICATED"
