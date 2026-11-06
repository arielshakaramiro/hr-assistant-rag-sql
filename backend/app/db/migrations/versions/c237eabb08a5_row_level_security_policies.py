"""row level security policies

Applies row-level security + read-only grants so the SQL-agent role (hr_ro) can only
read the signed-in employee's rows. Keyed on the per-connection GUC app.employee_id.

Revision ID: c237eabb08a5
Revises: b4dcaff54894
Create Date: 2026-11-06 10:09:41.729998
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c237eabb08a5"
down_revision: str | Sequence[str] | None = "b4dcaff54894"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCOPED = ["leave_balance", "leave_record", "attendance_record", "claim"]


def upgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM hr_ro")
    for t in [*SCOPED, "employee"]:
        op.execute(f"GRANT SELECT ON {t} TO hr_ro")
    for t in SCOPED:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS rls_{t} ON {t}")
        op.execute(
            f"CREATE POLICY rls_{t} ON {t} FOR SELECT TO hr_ro "
            "USING (employee_id = current_setting('app.employee_id', true)::int)"
        )
    op.execute("ALTER TABLE employee ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE employee FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS rls_employee ON employee")
    op.execute(
        "CREATE POLICY rls_employee ON employee FOR SELECT TO hr_ro "
        "USING (id = current_setting('app.employee_id', true)::int)"
    )


def downgrade() -> None:
    for t in [*SCOPED, "employee"]:
        op.execute(f"DROP POLICY IF EXISTS rls_{t} ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
