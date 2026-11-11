"""Observability + feedback tests.

Key privacy property: a chat query writes a metric row with NO question/answer text;
text is persisted only when the user submits feedback.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Feedback, QueryMetric
from app.db.session import SessionLocal
from app.main import app
from tests.conftest import requires_db

MAYA = {"email": "maya@example.com", "password": "demo-maya"}


def _client() -> TestClient:
    c = TestClient(app)
    c.post("/api/v1/auth/login", json=MAYA)
    return c


@requires_db
def test_query_records_metric_without_text() -> None:
    c = _client()
    with SessionLocal() as db:
        before = db.scalar(select(QueryMetric.id).order_by(QueryMetric.id.desc())) or 0
    c.post("/api/v1/chat/ask", json={"question": "What is the overtime policy?"})
    with SessionLocal() as db:
        row = db.scalar(
            select(QueryMetric).where(QueryMetric.id > before).order_by(QueryMetric.id.desc())
        )
    assert row is not None
    assert row.route in ("POLICY", "DATA", "BOTH", "CLARIFY")
    # QueryMetric has no text columns at all — the model cannot store Q/A text.
    assert not any("text" in col.name for col in QueryMetric.__table__.columns)


@requires_db
def test_metrics_endpoint_aggregates() -> None:
    c = _client()
    c.post("/api/v1/chat/ask", json={"question": "What is the overtime policy?"})
    r = c.get("/api/v1/metrics")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["count"] >= 1
    assert set(data["by_route"]) == {"POLICY", "DATA", "BOTH", "CLARIFY"}


@requires_db
def test_feedback_stores_text_only_on_submit() -> None:
    c = _client()
    with SessionLocal() as db:
        before = db.scalar(select(Feedback.id).order_by(Feedback.id.desc())) or 0
    c.post(
        "/api/v1/feedback",
        json={"question": "q?", "answer": "a.", "route": "POLICY", "rating": "up"},
    )
    with SessionLocal() as db:
        row = db.scalar(select(Feedback).where(Feedback.id > before))
    assert row is not None
    assert row.question_text == "q?"
    assert row.rating == "up"


@requires_db
def test_metrics_requires_auth() -> None:
    assert TestClient(app).get("/api/v1/metrics").status_code == 401
