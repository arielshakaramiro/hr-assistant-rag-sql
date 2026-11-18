"""Deterministic streaming tests: SSE parsing in chat_stream and the abstain-sentinel guard in
the streaming answerer. No live model or DB — httpx and chat_stream are stubbed.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx

import app.core.llm as llm
import app.rag.answerer as answerer
from app.core.reason_codes import Confidence


class _FakeStream:
    """Stands in for the httpx.stream(...) context manager over an SSE response."""

    def __init__(self, lines: list[str]):
        self._lines = lines

    def __enter__(self) -> _FakeStream:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self) -> Iterator[str]:
        yield from self._lines


def test_chat_stream_yields_deltas_and_stops_on_done(monkeypatch) -> None:
    lines = [
        'data: {"choices":[{"delta":{"role":"assistant"}}]}',  # role-only chunk → skipped
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        "",  # keep-alive blank line → skipped
        'data: {"choices":[{"delta":{"content":" world"}}]}',
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":"ignored after done"}}]}',
    ]
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: _FakeStream(lines))
    out = list(llm.chat_stream([{"role": "user", "content": "hi"}]))
    assert out == ["Hello", " world"]


def test_chat_stream_maps_transport_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "stream", boom)
    try:
        list(llm.chat_stream([{"role": "user", "content": "hi"}]))
        raise AssertionError("expected LLMError")
    except llm.LLMError:
        pass


def test_stream_answer_sentinel_becomes_abstain(monkeypatch) -> None:
    # Model streams only the decline sentinel → the guard must abstain and never emit it.
    monkeypatch.setattr(answerer, "chat_stream", lambda *a, **k: iter(["NOT_IN", "_HANDBOOK"]))
    # Bypass retrieval so we exercise the streaming path with a non-empty hit set.
    hit = answerer.Retrieved(doc_title="Employee Handbook", section="§1", text="x", similarity=0.9)
    monkeypatch.setattr(answerer, "retrieve", lambda db, q: [hit])

    ps = answerer.stream_policy_answer(db=None, question="anything")  # type: ignore[arg-type]
    emitted = "".join(ps.tokens)
    assert "NOT_IN_HANDBOOK" not in emitted
    assert ps.abstained is True
    assert ps.confidence is Confidence.LOW
    assert emitted == answerer.ABSTAIN_MESSAGE


def test_stream_answer_normal_text_flows(monkeypatch) -> None:
    monkeypatch.setattr(
        answerer, "chat_stream", lambda *a, **k: iter(["Full-time staff ", "get 12 days."])
    )
    hit = answerer.Retrieved(
        doc_title="Employee Handbook", section="§2.1 Entitlement", text="12 days", similarity=0.9
    )
    monkeypatch.setattr(answerer, "retrieve", lambda db, q: [hit])

    ps = answerer.stream_policy_answer(db=None, question="how many leave days?")  # type: ignore[arg-type]
    emitted = "".join(ps.tokens)
    assert emitted == "Full-time staff get 12 days."
    assert ps.abstained is False
    assert ps.citations and "Entitlement" in ps.citations[0].section
