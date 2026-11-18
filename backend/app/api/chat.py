"""Chat endpoint: ask a question, get a grounded answer with sources (API.md §5).

Two shapes: `/ask` returns the whole answer as one JSON object (used by tests, the eval harness
and the attacker round); `/ask/stream` streams the same answer as Server-Sent Events so the UI can
render tokens as they arrive. Both apply the same auth and rate limits.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_employee, get_db
from app.core.config import settings
from app.core.ratelimit import chat_limiter
from app.core.reason_codes import ErrorCode
from app.db.models import Employee
from app.db.session import SessionLocal
from app.obs.metrics import record, timed
from app.router.orchestrator import answer, answer_stream

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


def _enforce_rate_limits(emp_id: int) -> None:
    """Per-session minute cap, and a global daily cap tied to the spend ceiling. Raises 429."""
    if not chat_limiter.allow(f"chat:emp:{emp_id}", settings.per_session_minute_cap, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": ErrorCode.RATE_LIMITED.value, "message": "Slow down a moment."},
        )
    if not chat_limiter.allow("chat:global:day", settings.daily_query_cap, 86400):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": ErrorCode.RATE_LIMITED.value, "message": "Daily limit reached."},
        )


@router.post("/ask")
def ask(
    body: AskRequest,
    emp: Employee = Depends(current_employee),
    db: Session = Depends(get_db),
) -> dict:
    _enforce_rate_limits(emp.id)
    history = [(t.question, t.answer) for t in body.history]
    with timed() as t:
        result = answer(db, emp.id, body.question, history)
    # Record metadata only — never the question or answer text.
    record(db, route=result.route, latency_ms=t["ms"], outcome=result.outcome)
    return {"success": True, "data": result.to_data()}


def _sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/ask/stream")
def ask_stream(
    body: AskRequest,
    emp: Employee = Depends(current_employee),
) -> StreamingResponse:
    """Stream the same answer as SSE: a `meta` event (route/confidence/sources), then `token`
    events with incremental text, then `done`. Records one QueryMetric with TTFT and TTLT."""
    _enforce_rate_limits(emp.id)
    history = [(t.question, t.answer) for t in body.history]
    emp_id = emp.id  # capture before the generator runs (request scope ends first)

    def _events() -> Iterator[str]:
        # The request-scoped Session closes before this generator runs, so open our own.
        start = time.monotonic()
        ttft_ms: int | None = None
        with SessionLocal() as db:
            handle = answer_stream(db, emp_id, body.question, history)
            meta = handle.meta
            yield _sse(
                "meta",
                {
                    "route": meta.route,
                    "route_reason": meta.route_reason,
                    "confidence": meta.confidence,
                    "outcome": meta.outcome,
                    "sources": meta.sources,
                },
            )
            for chunk in handle.tokens:
                if ttft_ms is None:
                    ttft_ms = int((time.monotonic() - start) * 1000)
                yield _sse("token", {"text": chunk})
            yield _sse("done", {})
            latency_ms = int((time.monotonic() - start) * 1000)
            # Metadata only — never the question or answer text. final_outcome() reflects a
            # mid-stream abstain (policy sentinel), which meta.outcome couldn't know up front.
            record(
                db,
                route=meta.route,
                latency_ms=latency_ms,
                outcome=handle.final_outcome(),
                ttft_ms=ttft_ms,
            )

    return StreamingResponse(_events(), media_type="text/event-stream")
