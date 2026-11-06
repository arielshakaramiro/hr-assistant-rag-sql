"""Row-level isolation: the project's core promise (leakage = 0, hard gate).

These run against the seeded production engine. They prove that a scoped read-only
connection cannot read another employee's rows even with an unrestricted query.
Seed first: `make up && make seed`.
"""

from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine
from app.sql_agent.scope import scoped_ro_connection
from tests.conftest import requires_db


def _emp_id(email: str) -> int:
    with engine.connect() as c:
        return int(
            c.execute(text("SELECT id FROM employee WHERE email=:e"), {"e": email}).scalar_one()
        )


@requires_db
def test_scoped_connection_sees_only_own_claims() -> None:
    maya = _emp_id("maya@example.com")
    with scoped_ro_connection(maya) as c:
        # Unrestricted query — RLS must still limit rows to Maya.
        rows = c.execute(text("SELECT DISTINCT employee_id FROM claim")).scalars().all()
    assert rows == [maya], f"leak: claim rows from {rows}, expected only {maya}"


@requires_db
def test_scoped_connection_cannot_read_other_employee_row() -> None:
    maya = _emp_id("maya@example.com")
    with scoped_ro_connection(maya) as c:
        others = c.execute(text("SELECT email FROM employee WHERE id != :m"), {"m": maya}).all()
    assert others == [], f"leak: saw other employees {others}"


@requires_db
def test_scope_switches_with_employee_id() -> None:
    maya = _emp_id("maya@example.com")
    adi = _emp_id("adi@example.com")
    with scoped_ro_connection(adi) as c:
        emails = c.execute(text("SELECT email FROM employee")).scalars().all()
    assert emails == ["adi@example.com"], f"scope did not switch to Adi: {emails}"
    assert maya != adi


@requires_db
def test_readonly_role_cannot_write() -> None:
    maya = _emp_id("maya@example.com")
    with scoped_ro_connection(maya) as c:
        wrote = True
        try:
            c.execute(
                text(
                    "INSERT INTO claim (employee_id, claim_type, amount, currency, status) "
                    "VALUES (:m, 'medical', 1, 'IDR', 'paid')"
                ),
                {"m": maya},
            )
        except Exception:
            wrote = False
    assert wrote is False, "read-only role was able to write"


@requires_db
def test_attacker_no_leak_sample_through_orchestrator() -> None:
    """A sample of the independent attacker no-leak cases, run through the full orchestrator:
    no response may return a row belonging to another employee (leakage = 0 under attack).
    Keeps the attacker leakage evidence reproducible in the test suite."""
    from app.db.session import SessionLocal
    from app.eval.attacker import CASES
    from app.router.orchestrator import answer

    maya = _emp_id("maya@example.com")
    sample_ids = {"atk-2", "atk-6", "atk-7", "atk-8", "atk-18", "atk-20", "atk-46", "atk-54"}
    sample = [c for c in CASES if c.id in sample_ids and c.expect == "no_leak"]
    assert sample, "attacker sample not found"
    with SessionLocal() as db:
        for case in sample:
            r = answer(db, maya, case.question)
            rows = r.sources.get("rows", []) if isinstance(r.sources, dict) else []
            for row in rows:
                assert row.get("employee_id", maya) == maya, (
                    f"LEAK on {case.id}: returned another employee's row {row}"
                )
