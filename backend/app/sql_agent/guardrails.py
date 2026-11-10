"""SQL guardrails: validate generated SQL before it runs (SECURITY.md §6, ADR-4).

Defence in depth sits in layers: the agent runs as a read-only role (cannot write), the
row-level-security policies confine rows to the signed-in employee, and this validator
rejects anything that is not a single read against the allowlist. A block returns a
structured ReasonCode so the UI can explain it. Parsing uses sqlglot (Postgres dialect).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast

import sqlglot
from sqlglot import exp

from app.core.reason_codes import ReasonCode
from app.sql_agent.scope import ALLOWED_TABLES

# Columns the agent may reference, per table. Kept tight on purpose.
ALLOWED_COLUMNS = {
    "employee": {"id", "full_name", "department", "role"},
    "leave_balance": {"id", "employee_id", "year", "entitlement_days", "used_days"},
    "leave_record": {"id", "employee_id", "leave_type", "start_date", "end_date", "days", "status"},
    "attendance_record": {"id", "employee_id", "work_date", "status", "minutes_late"},
    "claim": {"id", "employee_id", "claim_type", "amount", "currency", "status"},
}


@dataclass(frozen=True)
class Blocked:
    code: ReasonCode
    message: str


def strip_employee_predicates(sql: str) -> str:
    """Remove any condition that references employee_id.

    Row scope is enforced by the read-only connection + RLS policies, so an employee_id
    predicate is redundant — and small models often write it against a non-existent helper
    (e.g. CURRENT_EMPLOYEE_ID()). Dropping it keeps the query runnable without weakening
    isolation. Returns the original SQL if it cannot be parsed/rewritten.
    """
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return sql
    if tree is None:
        return sql

    def _drops(node: exp.Expression) -> bool:
        return any(c.name == "employee_id" for c in node.find_all(exp.Column))

    for where in list(tree.find_all(exp.Where)):
        cond = where.this
        if cond is None:
            continue
        # Split the top-level AND chain and drop any conjunct mentioning employee_id.
        if isinstance(cond, exp.And):
            conjuncts: list[exp.Expression] = list(cast("Iterable[exp.Expression]", cond.flatten()))
        else:
            conjuncts = [cond]
        kept = [c for c in conjuncts if not _drops(c)]
        if len(kept) == len(conjuncts):
            continue
        if not kept:
            where.pop()
        else:
            new_cond = kept[0]
            for extra in kept[1:]:
                new_cond = exp.And(this=new_cond, expression=extra)
            where.set("this", new_cond)
    return tree.sql(dialect="postgres")


def validate(sql: str) -> Blocked | None:
    """Return None if the SQL is allowed, else a Blocked with the reason."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        return Blocked(ReasonCode.PARSE_ERROR, "Empty query.")

    # Reject multiple statements before parsing (a semicolon that is not a trailing one).
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception:
        return Blocked(ReasonCode.PARSE_ERROR, "Could not parse the query.")
    real = [s for s in statements if s is not None]
    if len(real) != 1:
        return Blocked(ReasonCode.MULTIPLE_STATEMENTS, "Only a single statement is allowed.")

    tree = real[0]

    # Must be a SELECT (no INSERT/UPDATE/DELETE/DDL, no CTE-wrapped writes).
    if not isinstance(tree, exp.Select):
        return Blocked(ReasonCode.NON_SELECT, "Only read (SELECT) queries are allowed.")
    for node in tree.walk():
        write_ops = (
            exp.Command,
            exp.Into,
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Alter,
            exp.Create,
        )
        if isinstance(node, write_ops):
            return Blocked(ReasonCode.NON_SELECT, "Only read (SELECT) queries are allowed.")

    # Tables referenced must be in the allowlist.
    referenced = {t.name for t in tree.find_all(exp.Table)}
    bad_tables = referenced - ALLOWED_TABLES
    if bad_tables:
        return Blocked(
            ReasonCode.DISALLOWED_TABLE,
            f"Query references a table that is not allowed: {', '.join(sorted(bad_tables))}.",
        )

    # `SELECT *` as a projection bypasses the column allowlist (it would include disallowed
    # columns such as employee.password_hash), so a bare star projection is rejected — the query
    # must name columns. `COUNT(*)` and other aggregates over `*` are fine (they expose no column).
    for proj in tree.expressions:
        if isinstance(proj, exp.Star) or (
            isinstance(proj, exp.Column) and isinstance(proj.this, exp.Star)
        ):
            return Blocked(
                ReasonCode.DISALLOWED_COLUMN,
                "Select specific columns, not *, so only allowed fields are read.",
            )

    # Columns referenced by name must be in the per-table allowlist (unqualified names allowed
    # if they exist on any referenced table).
    allowed_here: set[str] = set()
    for t in referenced:
        allowed_here |= ALLOWED_COLUMNS.get(t, set())
    for col in tree.find_all(exp.Column):
        if col.name and col.name not in allowed_here:
            return Blocked(
                ReasonCode.DISALLOWED_COLUMN,
                f"Query references a column that is not allowed: {col.name}.",
            )

    return None
