"""Eval harness entry point: `python -m app.eval.run` (also `make eval`).

Scores the development split of the golden set against whatever is wired, prints each
metric as k/n with its 95% interval, and gates each success rate on its lower bound
against the thresholds in AI_QUALITY.md. The report feeds the README eval table.

As slices land, more metrics switch from "not wired yet" to measured:
- router accuracy        : wired (Slice 2)
- RAG faithfulness/relev : wired when the RAG answerer lands (Slice 5)
- SQL execution-accuracy : wired when the SQL agent lands (Slice 4)
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from app.db.session import SessionLocal, engine
from app.eval.golden import DEVELOPMENT, Case
from app.eval.interval import wilson
from app.rag.answerer import answer_policy_question
from app.router.classifier import classify
from app.sql_agent.agent import answer_data_question

# Thresholds (AI_QUALITY.md). Gated on the interval lower bound for success rates.
ROUTER_MIN = 90.0
RAG_MIN = 85.0  # answerable-correct + abstain-correct, combined
SQL_MIN = 85.0


@dataclass
class MetricResult:
    name: str
    k: int
    n: int
    threshold: float | None
    note: str = ""

    def line(self) -> str:
        iv = wilson(self.k, self.n)
        verdict = ""
        if self.threshold is not None and self.n:
            ok = iv.low * 100 >= self.threshold
            verdict = f"  [{'PASS' if ok else 'FAIL'} ≥{self.threshold}% on lower bound]"
        extra = f"  ({self.note})" if self.note else ""
        return f"{self.name:24} {iv}{verdict}{extra}"


def _score_router(cases: list[Case]) -> MetricResult:
    route_cases = [c for c in cases if c.kind == "route"]
    k = sum(1 for c in route_cases if classify(c.question).route.value == c.expected_route)
    return MetricResult("router accuracy", k, len(route_cases), ROUTER_MIN)


def _score_policy(cases: list[Case]) -> MetricResult:
    """Grounded-answer accuracy: an answerable case answers with the right content and a
    citation to the right section; an unanswerable case abstains."""
    policy_cases = [c for c in cases if c.kind == "policy"]
    k = 0
    with SessionLocal() as db:
        for c in policy_cases:
            a = answer_policy_question(db, c.question)
            if c.answerable:
                content_ok = all(w.lower() in a.answer.lower() for w in c.expected_answer_contains)
                cite_ok = (
                    any(c.must_cite_section.lower() in cit.section.lower() for cit in a.citations)
                    if c.must_cite_section
                    else True
                )
                if content_ok and cite_ok and not a.abstained:
                    k += 1
            elif a.abstained:
                k += 1
    return MetricResult("policy grounded accuracy", k, len(policy_cases), RAG_MIN)


def _maya_id() -> int:
    with engine.connect() as c:
        row = c.execute(text("SELECT id FROM employee WHERE email='maya@example.com'"))
        return int(row.scalar_one())


def sql_value_matches(rows: list[dict], expected: tuple[str, ...]) -> bool:
    """A result matches when every expected token appears among the result VALUES.

    Matching the value cells (not the whole row repr) avoids a false pass where the digit
    only appears in an id/date/other column (verifier finding: substring-on-repr is too loose).
    """
    if not rows or not expected:
        return False
    cells = {str(v) for row in rows for v in row.values()}
    joined = " ".join(cells)
    return all(tok in joined for tok in expected)


def _score_sql(cases: list[Case]) -> MetricResult:
    """SQL execution-accuracy: the result VALUES contain the hand-worked expected value."""
    sql_cases = [c for c in cases if c.kind == "sql"]
    maya = _maya_id()
    k = 0
    for c in sql_cases:
        a = answer_data_question(maya, c.question)
        if sql_value_matches(a.rows, c.expected_answer_contains):
            k += 1
    return MetricResult("SQL execution-accuracy", k, len(sql_cases), SQL_MIN)


def run() -> list[MetricResult]:
    results = [
        _score_router(DEVELOPMENT),
        _score_policy(DEVELOPMENT),
        _score_sql(DEVELOPMENT),
    ]
    return results


def main() -> None:
    print("Golden-set evaluation (development split)\n")
    for r in run():
        print(r.line())
    print("\nFirst-run numbers on an author-written set are weak evidence; the adversarial")
    print("round and a larger set in Phase 6 harden them.")


if __name__ == "__main__":
    main()
