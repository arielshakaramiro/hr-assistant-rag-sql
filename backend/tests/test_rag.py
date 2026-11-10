"""RAG tests: retrieval, citations and abstain behaviour (need the seeded DB + model)."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.rag.answerer import answer_policy_question
from app.rag.retriever import retrieve
from tests.conftest import requires_db


@requires_db
def test_retrieve_returns_k_chunks() -> None:
    with SessionLocal() as db:
        hits = retrieve(db, "overtime pay", k=4)
    assert len(hits) == 4  # ivfflat probes must return the full k on a small corpus


@requires_db
def test_policy_answer_cites_right_section() -> None:
    with SessionLocal() as db:
        a = answer_policy_question(db, "What is the overtime policy?")
    assert not a.abstained
    assert any("overtime" in c.section.lower() for c in a.citations)


@requires_db
def test_policy_answer_contains_fact() -> None:
    with SessionLocal() as db:
        a = answer_policy_question(db, "How many annual leave days do employees get?")
    assert "12" in a.answer


@requires_db
def test_unanswerable_abstains() -> None:
    with SessionLocal() as db:
        a = answer_policy_question(db, "What is the policy on grandparental leave?")
    assert a.abstained
    assert not a.citations
