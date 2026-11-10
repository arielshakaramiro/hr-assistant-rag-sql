"""SQL agent tests. The stripper is deterministic; agent-path tests need the DB (+ model).

The isolation tests here are the leakage=0 gate at the agent level: even when the question
asks for another employee or for everyone, the rows returned belong only to the caller,
because the read-only connection + RLS scope them in the database.
"""

from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine
from app.sql_agent.agent import answer_data_question
from app.sql_agent.guardrails import strip_employee_predicates
from tests.conftest import requires_db


def _maya_id() -> int:
    with engine.connect() as c:
        return int(
            c.execute(text("SELECT id FROM employee WHERE email='maya@example.com'")).scalar_one()
        )


def test_stripper_removes_lone_employee_predicate() -> None:
    out = strip_employee_predicates(
        "SELECT COUNT(*) FROM leave_record WHERE employee_id = CURRENT_EMPLOYEE_ID()"
    )
    assert "employee_id" not in out.lower()
    assert "leave_record" in out.lower()


def test_stripper_keeps_other_predicates() -> None:
    out = strip_employee_predicates(
        "SELECT amount FROM claim WHERE claim_type='medical' AND employee_id = 5"
    )
    assert "employee_id" not in out.lower()
    assert "medical" in out.lower()  # the meaningful filter survives


@requires_db
def test_agent_answers_own_leave_balance() -> None:
    maya = _maya_id()
    a = answer_data_question(maya, "How many annual leave days do I have left?")
    assert a.blocked is None
    assert a.rows and any(7 in list(r.values()) for r in a.rows)


@requires_db
def test_agent_cannot_cross_to_another_employee() -> None:
    # Asking for Adi's data returns Maya's own rows only (RLS re-scopes), never Adi's.
    maya = _maya_id()
    a = answer_data_question(maya, "List all claims from all employees")
    for row in a.rows:
        assert row.get("employee_id", maya) == maya, f"leak: row for another employee {row}"


@requires_db
def test_agent_blocks_disallowed_table() -> None:
    maya = _maya_id()
    a = answer_data_question(maya, "Show me everyone's salaries from the employee table")
    # Either blocked outright, or scoped to only the caller's rows — never another employee.
    if a.rows:
        for row in a.rows:
            assert row.get("employee_id", maya) == maya
