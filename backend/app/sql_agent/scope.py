"""Row-level scope for the read-only SQL agent connection (ADR-3, SECURITY.md §2).

Every agent query runs on a connection that (1) uses the read-only role and (2) sets a
per-transaction GUC ``app.employee_id``. Postgres row-level-security policies on each
per-employee table restrict rows to that id, so even a query the model got wrong — or an
injected one — cannot read another employee's rows. This is enforced in the database,
not in the prompt.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.db.session import engine_ro

# Tables the agent may read, and the column that carries the employee scope on each.
SCOPED_TABLES = {
    "leave_balance": "employee_id",
    "leave_record": "employee_id",
    "attendance_record": "employee_id",
    "claim": "employee_id",
}
# employee is readable but only the signed-in row (see the RLS policy below).
ALLOWED_TABLES = set(SCOPED_TABLES) | {"employee"}


@contextmanager
def scoped_ro_connection(employee_id: int) -> Iterator[Connection]:
    """A read-only connection whose transaction is pinned to one employee id."""
    conn = engine_ro.connect()
    try:
        trans = conn.begin()
        # set_config(..., is_local=true) scopes the GUC to this transaction only.
        conn.execute(
            text("SELECT set_config('app.employee_id', :eid, true)"),
            {"eid": str(employee_id)},
        )
        try:
            yield conn
        finally:
            trans.rollback()  # read-only: never commit
    finally:
        conn.close()
