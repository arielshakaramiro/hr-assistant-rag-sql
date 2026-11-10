"""SQL guardrail unit tests — one per block reason, plus allowed queries pass.

Deterministic (no model). These are the first line of the leakage=0 defence and the
set the mutation check breaks against.
"""

from __future__ import annotations

from app.core.reason_codes import ReasonCode
from app.sql_agent.guardrails import validate


def test_allows_a_scoped_select() -> None:
    sql = "SELECT entitlement_days - used_days AS remaining FROM leave_balance WHERE year = 2026"
    assert validate(sql) is None


def test_blocks_select_star_projection() -> None:
    # SELECT * would surface disallowed columns (e.g. employee.password_hash); it must be blocked.
    b = validate("SELECT * FROM claim")
    assert b is not None and b.code is ReasonCode.DISALLOWED_COLUMN


def test_blocks_star_from_employee_hiding_password_hash() -> None:
    b = validate("SELECT * FROM employee")
    assert b is not None and b.code is ReasonCode.DISALLOWED_COLUMN


def test_allows_count_star() -> None:
    # COUNT(*) exposes no column and is a common, safe aggregate.
    assert validate("SELECT COUNT(*) FROM claim") is None


def test_allows_explicit_columns() -> None:
    assert validate("SELECT claim_type, amount, status FROM claim") is None


def test_blocks_insert() -> None:
    b = validate("INSERT INTO claim (amount) VALUES (1)")
    assert b is not None and b.code is ReasonCode.NON_SELECT


def test_blocks_update() -> None:
    b = validate("UPDATE claim SET status='paid'")
    assert b is not None and b.code is ReasonCode.NON_SELECT


def test_blocks_delete() -> None:
    b = validate("DELETE FROM claim")
    assert b is not None and b.code is ReasonCode.NON_SELECT


def test_blocks_drop() -> None:
    b = validate("DROP TABLE claim")
    assert b is not None and b.code is ReasonCode.NON_SELECT


def test_blocks_multiple_statements() -> None:
    b = validate("SELECT * FROM claim; DROP TABLE claim;")
    assert b is not None and b.code in (
        ReasonCode.MULTIPLE_STATEMENTS,
        ReasonCode.NON_SELECT,
    )


def test_blocks_disallowed_table() -> None:
    b = validate("SELECT * FROM pg_user")
    assert b is not None and b.code is ReasonCode.DISALLOWED_TABLE


def test_blocks_disallowed_column() -> None:
    b = validate("SELECT password_hash FROM employee")
    assert b is not None and b.code is ReasonCode.DISALLOWED_COLUMN


def test_blocks_unparseable() -> None:
    b = validate("this is not sql !!!")
    assert b is not None and b.code in (ReasonCode.PARSE_ERROR, ReasonCode.NON_SELECT)


def test_blocks_empty() -> None:
    b = validate("   ")
    assert b is not None and b.code is ReasonCode.PARSE_ERROR
