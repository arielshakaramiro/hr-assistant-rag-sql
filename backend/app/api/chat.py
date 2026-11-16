"""Chat endpoint: ask a question, get a grounded answer with sources (API.md §5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_employee, get_db
from app.core.config import settings
from app.core.ratelimit import chat_limiter
from app.core.reason_codes import ErrorCode
from app.db.models import Employee
from app.obs.metrics import record, timed
from app.router.orchestrator import answer

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class Turn(BaseModel):
    """One prior exchange, sent by the client for follow-up context. Untrusted input, so each
    field is length-bounded; the orchestrator further caps how many turns it uses."""

    question: str = Field(max_length=1000)
    answer: str = Field(max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    # Recent turns for multi-turn follow-ups. Client-held (nothing is persisted server-side);
    # capped here and again in the contextualizer.
    history: list[Turn] = Field(default_factory=list, max_length=10)


@router.post("/ask")
def ask(
    body: AskRequest,
    emp: Employee = Depends(current_employee),
    db: Session = Depends(get_db),
) -> dict:
    # Per-session minute cap, and a global daily cap tied to the spend ceiling.
    if not chat_limiter.allow(f"chat:emp:{emp.id}", settings.per_session_minute_cap, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": ErrorCode.RATE_LIMITED.value, "message": "Slow down a moment."},
        )
    if not chat_limiter.allow("chat:global:day", settings.daily_query_cap, 86400):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": ErrorCode.RATE_LIMITED.value, "message": "Daily limit reached."},
        )

    history = [(t.question, t.answer) for t in body.history]
    with timed() as t:
        result = answer(db, emp.id, body.question, history)
    # Record metadata only — never the question or answer text.
    record(db, route=result.route, latency_ms=t["ms"], outcome=result.outcome)
    return {"success": True, "data": result.to_data()}
