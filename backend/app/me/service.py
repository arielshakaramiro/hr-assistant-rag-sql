"""Per-employee self-service reads (the data behind the My leave/Attendance/Claims menus).

Read-only. Every query filters on `employee_id` EXPLICITLY — the app role bypasses row-level
security, so (unlike the SQL-agent path) the scope is not applied by the database here and must
be named in the query. The employee id always comes from the signed-in session (the router
passes `emp.id`), never from the request. Mirrors app/admin/service.py.

Remaining leave is DERIVED (entitlement - used), never stored (DATABASE.md §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.service import CURRENT_YEAR  # single source of the current-year convention (2026)
from app.db.models import AttendanceRecord, Claim, LeaveBalance, LeaveRecord


@dataclass(frozen=True)
class LeaveRecordRow:
    leave_type: str
    start_date: str  # ISO date
    end_date: str
    days: int
    status: str


@dataclass(frozen=True)
class LeaveSummary:
    entitlement_days: int
    used_days: int
    remaining_days: int
    records: list[LeaveRecordRow] = field(default_factory=list)


@dataclass(frozen=True)
class AttendanceRecordRow:
    work_date: str  # ISO date
    status: str
    minutes_late: int


@dataclass(frozen=True)
class AttendanceSummary:
    counts: dict[str, int]  # count per status
    records: list[AttendanceRecordRow] = field(default_factory=list)


@dataclass(frozen=True)
class ClaimRow:
    claim_type: str
    amount: float
    currency: str
    status: str
    submitted: str  # ISO datetime (created_at)


@dataclass(frozen=True)
class ClaimsSummary:
    claims: list[ClaimRow] = field(default_factory=list)
    totals_count: dict[str, int] = field(default_factory=dict)  # count per status
    totals_amount: dict[str, float] = field(default_factory=dict)  # summed amount per status


def leave_summary(db: Session, employee_id: int) -> LeaveSummary:
    balance = db.execute(
        select(LeaveBalance.entitlement_days, LeaveBalance.used_days).where(
            LeaveBalance.employee_id == employee_id, LeaveBalance.year == CURRENT_YEAR
        )
    ).first()
    entitlement = int(balance[0]) if balance else 0
    used = int(balance[1]) if balance else 0

    rows = db.execute(
        select(
            LeaveRecord.leave_type,
            LeaveRecord.start_date,
            LeaveRecord.end_date,
            LeaveRecord.days,
            LeaveRecord.status,
        )
        .where(LeaveRecord.employee_id == employee_id)
        .order_by(LeaveRecord.start_date.desc())
    ).all()
    records = [
        LeaveRecordRow(
            leave_type=lt,
            start_date=sd.isoformat(),
            end_date=ed.isoformat(),
            days=int(days),
            status=status,
        )
        for lt, sd, ed, days, status in rows
    ]
    return LeaveSummary(
        entitlement_days=entitlement,
        used_days=used,
        remaining_days=entitlement - used,
        records=records,
    )


def attendance_summary(db: Session, employee_id: int) -> AttendanceSummary:
    counts = {
        status: int(n)
        for status, n in db.execute(
            select(AttendanceRecord.status, func.count(AttendanceRecord.id))
            .where(AttendanceRecord.employee_id == employee_id)
            .group_by(AttendanceRecord.status)
        ).all()
    }
    rows = db.execute(
        select(
            AttendanceRecord.work_date,
            AttendanceRecord.status,
            AttendanceRecord.minutes_late,
        )
        .where(AttendanceRecord.employee_id == employee_id)
        .order_by(AttendanceRecord.work_date.desc())
    ).all()
    records = [
        AttendanceRecordRow(work_date=wd.isoformat(), status=status, minutes_late=int(ml))
        for wd, status, ml in rows
    ]
    return AttendanceSummary(counts=counts, records=records)


def claims_summary(db: Session, employee_id: int) -> ClaimsSummary:
    rows = db.execute(
        select(
            Claim.claim_type,
            Claim.amount,
            Claim.currency,
            Claim.status,
            Claim.created_at,
        )
        .where(Claim.employee_id == employee_id)
        .order_by(Claim.created_at.desc())
    ).all()
    claims = [
        ClaimRow(
            claim_type=ct,
            amount=float(amount),
            currency=currency,
            status=status,
            submitted=created.isoformat(),
        )
        for ct, amount, currency, status, created in rows
    ]

    totals = db.execute(
        select(
            Claim.status,
            func.count(Claim.id),
            func.coalesce(func.sum(Claim.amount), 0),
        )
        .where(Claim.employee_id == employee_id)
        .group_by(Claim.status)
    ).all()
    totals_count = {status: int(n) for status, n, _ in totals}
    totals_amount = {status: float(amount) for status, _, amount in totals}
    return ClaimsSummary(claims=claims, totals_count=totals_count, totals_amount=totals_amount)
