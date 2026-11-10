"""SQL agent: turn a DATA question into a guarded, employee-scoped read.

Flow (ARCHITECTURE §4, SECURITY §6): the model drafts SQL from a fixed schema description →
the guardrails validate it → it runs on the read-only connection pinned to the employee's id,
under a row cap → the exact SQL and the rows are returned for display. The model never sees or
chooses the employee id; the scope is applied by the connection and the database RLS policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text

from app.core.config import settings
from app.core.llm import LLMError, chat
from app.core.reason_codes import Confidence, ReasonCode
from app.sql_agent.guardrails import Blocked, strip_employee_predicates, validate
from app.sql_agent.scope import scoped_ro_connection

SCHEMA = """Tables (you may read ONLY these; every query is already restricted to the current
employee, so do NOT add an employee filter yourself and do NOT reference other employees):
- leave_balance(year, entitlement_days, used_days)
- leave_record(leave_type, start_date, end_date, days, status)
- attendance_record(work_date, status, minutes_late)   -- status: present|late|absent|leave|holiday
- claim(claim_type, amount, currency, status)          -- status: submitted|approved|rejected|paid
Remaining annual leave = entitlement_days - used_days for the current year (2026)."""

SYSTEM = f"""You write ONE read-only PostgreSQL SELECT that answers the employee's question
about their own records. {SCHEMA}

Rules: a single SELECT only; no writes; no other tables; no semicolons beyond the end;
never reference employee_id or any employee function — the rows are already scoped for you.
Reply with ONLY the SQL, no prose, no code fences."""


@dataclass
class SqlAnswer:
    sql: str
    rows: list[dict] = field(default_factory=list)
    blocked: Blocked | None = None
    confidence: Confidence = Confidence.HIGH


def _generate_sql(question: str) -> str:
    raw = chat(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}],
        max_tokens=200,
    )
    sql = raw.strip()
    # Strip code fences if the model added them despite instructions.
    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    return sql.strip()


def answer_data_question(employee_id: int, question: str) -> SqlAnswer:
    try:
        sql = _generate_sql(question)
    except LLMError:
        return SqlAnswer(
            sql="",
            blocked=Blocked(ReasonCode.PARSE_ERROR, "Model unavailable."),
            confidence=Confidence.LOW,
        )

    blocked = validate(sql)
    if blocked is not None:
        return SqlAnswer(sql=sql, blocked=blocked, confidence=Confidence.LOW)

    # Drop any redundant employee_id predicate the model added (RLS already scopes rows).
    runnable = strip_employee_predicates(sql)
    capped = f"SELECT * FROM ({runnable.rstrip(';')}) AS _agent LIMIT {settings.sql_row_limit}"
    try:
        with scoped_ro_connection(employee_id) as conn:
            conn.execute(text(f"SET LOCAL statement_timeout = {settings.sql_timeout_ms}"))
            result = conn.execute(text(capped))
            rows = [dict(r._mapping) for r in result]
    except Exception:
        # A runtime failure (e.g. timeout, bad column at execution) is surfaced, not leaked.
        return SqlAnswer(
            sql=sql,
            blocked=Blocked(ReasonCode.PARSE_ERROR, "Query could not run."),
            confidence=Confidence.LOW,
        )

    confidence = Confidence.HIGH if rows else Confidence.LOW
    return SqlAnswer(sql=sql, rows=rows, confidence=confidence)
