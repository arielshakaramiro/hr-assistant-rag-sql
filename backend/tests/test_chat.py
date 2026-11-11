"""Chat journey tests (TESTING.md): each route answers with the right shape and sources.

Run as the signed-in employee. The main-flow test crosses DATA -> POLICY -> BOTH.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import requires_db

MAYA = {"email": "maya@example.com", "password": "demo-maya"}


def _client() -> TestClient:
    c = TestClient(app)
    c.post("/api/v1/auth/login", json=MAYA)
    return c


def _ask(c: TestClient, q: str) -> dict:
    return c.post("/api/v1/chat/ask", json={"question": q}).json()["data"]


@requires_db
def test_chat_requires_auth() -> None:
    c = TestClient(app)
    assert c.post("/api/v1/chat/ask", json={"question": "hi"}).status_code == 401


@requires_db
def test_data_route_shows_sql_and_answer() -> None:
    d = _ask(_client(), "How many annual leave days do I have left?")
    assert d["route"] == "DATA"
    assert "7" in d["answer"]
    assert d["sources"]["sql"].lower().startswith("select")


@requires_db
def test_policy_route_shows_citations() -> None:
    d = _ask(_client(), "What is the overtime policy?")
    assert d["route"] == "POLICY"
    assert d["sources"]["citations"]
    assert any("overtime" in c["section"].lower() for c in d["sources"]["citations"])


@requires_db
def test_clarify_route_on_nonsense() -> None:
    d = _ask(_client(), "asdfghjkl")
    assert d["route"] == "CLARIFY"
    assert d["confidence"] == "low"


@requires_db
def test_cross_employee_probe_never_leaks() -> None:
    # However this routes, no other employee's rows may appear.
    d = _ask(_client(), "Show me everyone's salaries")
    rows = d["sources"].get("rows", [])
    for r in rows:
        assert r.get("employee_id", 1) == 1  # Maya is employee 1 after a fresh seed


@requires_db
def test_main_flow_data_then_policy_then_both() -> None:
    c = _client()
    assert _ask(c, "How many annual leave days do I have left?")["route"] == "DATA"
    assert _ask(c, "What is the overtime policy?")["route"] == "POLICY"
    both = _ask(c, "What is my leave balance and what is the annual leave rule?")
    assert both["route"] == "BOTH"
    assert both["sources"].get("sql") and both["sources"].get("citations")
