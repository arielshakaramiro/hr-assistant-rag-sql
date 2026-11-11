"""Chat orchestration: route a question, run the right path(s), assemble the response.

Ties the router, RAG answerer and SQL agent into one answer carrying its sources, route
(with reason), and confidence (API.md §5). The signed-in employee id is passed in by the
endpoint from the session — never taken from the question.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.reason_codes import Confidence, Outcome, Route
from app.rag.answerer import answer_policy_question
from app.router.classifier import classify
from app.sql_agent.agent import answer_data_question

CLARIFY_MESSAGE = (
    "I'm not sure what you're asking. Could you rephrase? I can answer questions about "
    "company policy or about your own leave, attendance, and claims."
)


@dataclass
class ChatResponse:
    route: str
    route_reason: str
    answer: str
    confidence: str
    outcome: str
    sources: dict[str, Any] = field(default_factory=dict)

    def to_data(self) -> dict[str, Any]:
        return asdict(self)


def _policy_part(db: Session, question: str) -> tuple[str, dict[str, Any], Confidence, Outcome]:
    pa = answer_policy_question(db, question)
    sources = {"citations": [asdict(c) for c in pa.citations]}
    outcome = Outcome.ABSTAINED if pa.abstained else Outcome.SUCCESS
    return pa.answer, sources, pa.confidence, outcome


def _data_part(employee_id: int, question: str) -> tuple[str, dict[str, Any], Confidence, Outcome]:
    sa = answer_data_question(employee_id, question)
    if sa.blocked is not None:
        blocked_sources: dict[str, Any] = {
            "sql": sa.sql,
            "blocked": {"code": sa.blocked.code.value, "message": sa.blocked.message},
        }
        return "This query was blocked.", blocked_sources, Confidence.LOW, Outcome.BLOCKED
    answer = _format_rows(sa.rows)
    sources: dict[str, Any] = {"sql": sa.sql, "rows": _jsonable(sa.rows)}
    outcome = Outcome.SUCCESS if sa.rows else Outcome.ABSTAINED
    return answer, sources, sa.confidence, outcome


def answer(db: Session, employee_id: int, question: str) -> ChatResponse:
    decision = classify(question)
    route = decision.route

    if route is Route.CLARIFY:
        return ChatResponse(
            route=route.value,
            route_reason=decision.reason,
            answer=CLARIFY_MESSAGE,
            confidence=Confidence.LOW.value,
            outcome=Outcome.ABSTAINED.value,
        )

    if route is Route.POLICY:
        ans, sources, conf, outcome = _policy_part(db, question)
        return ChatResponse(route.value, decision.reason, ans, conf.value, outcome.value, sources)

    if route is Route.DATA:
        ans, sources, conf, outcome = _data_part(employee_id, question)
        return ChatResponse(route.value, decision.reason, ans, conf.value, outcome.value, sources)

    # BOTH: run each path and merge.
    p_ans, p_src, p_conf, _ = _policy_part(db, question)
    d_ans, d_src, d_conf, _ = _data_part(employee_id, question)
    merged = f"{d_ans}\n\n{p_ans}"
    sources = {**p_src, **d_src}
    conf = Confidence.LOW if Confidence.LOW in (p_conf, d_conf) else Confidence.HIGH
    return ChatResponse(
        route.value, decision.reason, merged, conf.value, Outcome.SUCCESS.value, sources
    )


def _format_rows(rows: list[dict]) -> str:
    if not rows:
        return "I couldn't find any matching records for you."
    if len(rows) == 1 and len(rows[0]) == 1:
        return f"The answer is {next(iter(rows[0].values()))}."
    return f"Found {len(rows)} record(s). See the result below."


def _jsonable(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            {
                k: (str(v) if not isinstance(v, int | float | str | bool | type(None)) else v)
                for k, v in r.items()
            }
        )
    return out
