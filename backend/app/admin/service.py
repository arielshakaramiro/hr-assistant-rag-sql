"""Team-aggregate service for the HR-admin dashboard (PRD F, backlog item).

Whole-company, read-only aggregates built with parameter-free SQLAlchemy queries on the APP
engine. The app role bypasses row-level security, so these queries see every employee's rows —
by design and only here, behind the require_hr_admin guard. The employee SQL-agent path (the
read-only hr_ro role + RLS, the leakage=0 gate) is never touched by this module.

Remaining leave is DERIVED (entitlement - used), never stored (DATABASE.md §5). The current year
matches the seed/SQL-agent convention (2026).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AttendanceRecord, Claim, Employee, LeaveBalance, LeaveRecord

CURRENT_YEAR = 2026  # same convention as the SQL agent schema and the seed


@dataclass(frozen=True)
class RosterRow:
    full_name: str
    department: str
    role: str
    entitlement_days: int
    used_days: int
    remaining_days: int


@dataclass(frozen=True)
class TeamOverview:
    headcount: int
    by_department: dict[str, int]
    leave: dict[str, int]  # entitlement_days, used_days, remaining_days, pending_requests
    attendance: dict[str, int]  # count per status
    claims_count: dict[str, int]  # count per status
    claims_amount: dict[str, float]  # summed amount per status
    roster: list[RosterRow] = field(default_factory=list)


def team_overview(db: Session) -> TeamOverview:
    headcount = db.scalar(select(func.count(Employee.id))) or 0
    by_department = {
        dept: n
        for dept, n in db.execute(
            select(Employee.department, func.count(Employee.id)).group_by(Employee.department)
        ).all()
    }

    # Current-year leave totals across the company; remaining is derived, not stored.
    entitlement = (
        db.scalar(
            select(func.coalesce(func.sum(LeaveBalance.entitlement_days), 0)).where(
                LeaveBalance.year == CURRENT_YEAR
            )
        )
        or 0
    )
    used = (
        db.scalar(
            select(func.coalesce(func.sum(LeaveBalance.used_days), 0)).where(
                LeaveBalance.year == CURRENT_YEAR
            )
        )
        or 0
    )
    pending = (
        db.scalar(select(func.count(LeaveRecord.id)).where(LeaveRecord.status == "pending")) or 0
    )
    leave = {
        "entitlement_days": int(entitlement),
        "used_days": int(used),
        "remaining_days": int(entitlement) - int(used),
        "pending_requests": int(pending),
    }

    attendance = {
        status: n
        for status, n in db.execute(
            select(AttendanceRecord.status, func.count(AttendanceRecord.id)).group_by(
                AttendanceRecord.status
            )
        ).all()
    }

    claims_rows = db.execute(
        select(
            Claim.status,
            func.count(Claim.id),
            func.coalesce(func.sum(Claim.amount), 0),
        ).group_by(Claim.status)
    ).all()
    claims_count = {status: int(n) for status, n, _ in claims_rows}
    claims_amount = {status: float(amount) for status, _, amount in claims_rows}

    # Roster: one row per employee with their current-year leave summary (LEFT JOIN so an
    # employee without a balance row still appears). No raw leave/attendance/claim rows.
    roster_rows = db.execute(
        select(
            Employee.full_name,
            Employee.department,
            Employee.role,
            func.coalesce(LeaveBalance.entitlement_days, 0),
            func.coalesce(LeaveBalance.used_days, 0),
        )
        .outerjoin(
            LeaveBalance,
            (LeaveBalance.employee_id == Employee.id) & (LeaveBalance.year == CURRENT_YEAR),
        )
        .order_by(Employee.full_name)
    ).all()
    roster = [
        RosterRow(
            full_name=name,
            department=dept,
            role=role,
            entitlement_days=int(ent),
            used_days=int(usd),
            remaining_days=int(ent) - int(usd),
        )
        for name, dept, role, ent, usd in roster_rows
    ]

    return TeamOverview(
        headcount=int(headcount),
        by_department=by_department,
        leave=leave,
        attendance=attendance,
        claims_count=claims_count,
        claims_amount=claims_amount,
        roster=roster,
    )
