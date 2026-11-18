"""Chat orchestration: route a question, run the right path(s), assemble the response.

Ties the router, RAG answerer and SQL agent into one answer carrying its sources, route
(with reason), and confidence (API.md §5). The signed-in employee id is passed in by the
endpoint from the session — never taken from the question.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.reason_codes import Confidence, Outcome, Route
from app.rag.answerer import answer_policy_question, stream_policy_answer
from app.router.classifier import classify
from app.router.contextualizer import contextualize
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


def answer(
    db: Session,
    employee_id: int,
    question: str,
    history: list[tuple[str, str]] | None = None,
) -> ChatResponse:
    # Resolve a follow-up into a standalone question first; the rest of the pipeline is single-turn
    # and unchanged. With no history this is a no-op (no model call), so first turns are identical.
    question = contextualize(history or [], question)
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


@dataclass
class StreamMeta:
    """The non-text envelope sent before tokens: everything known without the generated answer."""

    route: str
    route_reason: str
    confidence: str
    outcome: str
    sources: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamHandle:
    """A streamed answer: `meta` is ready immediately; `tokens` yields display text. Call
    `final_outcome()` AFTER exhausting `tokens` — a policy sentinel can flip the outcome to
    abstained mid-stream, so the recorded metric uses this rather than the pre-stream meta."""

    meta: StreamMeta
    tokens: Iterator[str]
    final_outcome: Callable[[], str]


def answer_stream(
    db: Session,
    employee_id: int,
    question: str,
    history: list[tuple[str, str]] | None = None,
) -> StreamHandle:
    """Streaming counterpart of `answer`. Only the POLICY text is token-streamed (the one
    LLM-generated surface); DATA/CLARIFY answers and the DATA prefix of BOTH are deterministic and
    yielded whole. Routing, retrieval and SQL run first so the meta envelope is complete up front.
    The non-stream `answer` is untouched and still used by `/ask`, eval and the attacker round."""
    question = contextualize(history or [], question)
    decision = classify(question)
    route = decision.route

    if route is Route.CLARIFY:
        meta = StreamMeta(
            route.value, decision.reason, Confidence.LOW.value, Outcome.ABSTAINED.value
        )
        return StreamHandle(meta, iter([CLARIFY_MESSAGE]), lambda: Outcome.ABSTAINED.value)

    if route is Route.DATA:
        ans, sources, conf, outcome = _data_part(employee_id, question)
        meta = StreamMeta(route.value, decision.reason, conf.value, outcome.value, sources)
        data_outcome = outcome.value
        return StreamHandle(meta, iter([ans]), lambda: data_outcome)

    if route is Route.POLICY:
        ps = stream_policy_answer(db, question)
        outcome = Outcome.ABSTAINED if ps.abstained else Outcome.SUCCESS
        sources = {"citations": [asdict(c) for c in ps.citations]}
        meta = StreamMeta(route.value, decision.reason, ps.confidence.value, outcome.value, sources)
        # ps.abstained can flip mid-stream (sentinel), so read it after tokens are exhausted.
        return StreamHandle(
            meta,
            ps.tokens,
            lambda: Outcome.ABSTAINED.value if ps.abstained else Outcome.SUCCESS.value,
        )

    # BOTH: the data part is deterministic (emit whole, first), then stream the policy part.
    d_ans, d_src, _, _ = _data_part(employee_id, question)
    ps = stream_policy_answer(db, question)
    sources = {**{"citations": [asdict(c) for c in ps.citations]}, **d_src}
    conf = Confidence.LOW if ps.confidence is Confidence.LOW else Confidence.HIGH
    meta = StreamMeta(route.value, decision.reason, conf.value, Outcome.SUCCESS.value, sources)

    def _both_tokens() -> Iterator[str]:
        yield f"{d_ans}\n\n"
        yield from ps.tokens

    return StreamHandle(meta, _both_tokens(), lambda: Outcome.SUCCESS.value)


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
