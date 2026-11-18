"""Deterministic contextualizer tests: the no-history fast path and safe fallbacks (no DB).

The model call itself is exercised by the eval harness and the multi-turn chat test; here we
pin the behaviour that must hold without a model: empty history is a pure no-op, and any model
failure or garbage rewrite falls back to the raw question rather than blocking.
"""

from __future__ import annotations

import app.router.contextualizer as ctx
from app.core.llm import LLMError


def _stub_chat(reply: str):
    def _chat(*_a, **_k) -> str:
        return reply

    return _chat


def test_empty_history_returns_question_unchanged_without_model(monkeypatch) -> None:
    # If this path ever called the model, this stub would make it raise — proving it does not.
    def _boom(*_a, **_k) -> str:
        raise AssertionError("model called on empty history")

    monkeypatch.setattr(ctx, "chat", _boom)
    q = "How many leave days do I have left?"
    assert ctx.contextualize([], q) is q


def test_llm_error_falls_back_to_raw_question(monkeypatch) -> None:
    def _boom(*_a, **_k) -> str:
        raise LLMError("provider down")

    monkeypatch.setattr(ctx, "chat", _boom)
    q = "And what about last year?"
    assert ctx.contextualize([("How many left?", "You have 7.")], q) == q


def test_empty_rewrite_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(ctx, "chat", _stub_chat("   "))
    q = "And that?"
    assert ctx.contextualize([("x", "y")], q) == q


def test_overlong_rewrite_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(ctx, "chat", _stub_chat("word " * 100))
    q = "And that?"
    assert ctx.contextualize([("x", "y")], q) == q


def test_clean_rewrite_is_used(monkeypatch) -> None:
    monkeypatch.setattr(ctx, "chat", _stub_chat('"How do I request annual leave?"'))
    out = ctx.contextualize([("How many leave days left?", "7")], "And how do I request it?")
    assert out == "How do I request annual leave?"
