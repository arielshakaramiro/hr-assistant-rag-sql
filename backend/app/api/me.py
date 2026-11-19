"""Self-service endpoints: the signed-in employee's own leave, attendance and claims.

Read-only. The employee id comes ONLY from the session (`emp.id`), never the request, and the
service filters every query by it — a user can only ever read their own rows (SECURITY.md §2).
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_employee, get_db
from app.db.models import Employee
from app.me.service import attendance_summary, claims_summary, leave_summary

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("/leave")
def my_leave(
    emp: Employee = Depends(current_employee),
    db: Session = Depends(get_db),
) -> dict:
    return {"success": True, "data": asdict(leave_summary(db, emp.id))}


@router.get("/attendance")
def my_attendance(
    emp: Employee = Depends(current_employee),
    db: Session = Depends(get_db),
) -> dict:
    return {"success": True, "data": asdict(attendance_summary(db, emp.id))}


@router.get("/claims")
def my_claims(
    emp: Employee = Depends(current_employee),
    db: Session = Depends(get_db),
) -> dict:
    return {"success": True, "data": asdict(claims_summary(db, emp.id))}
