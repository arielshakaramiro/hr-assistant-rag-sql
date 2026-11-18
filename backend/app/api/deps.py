"""Shared API dependencies: DB session and the signed-in employee.

The employee identity used for every data read comes ONLY from the server-side session
cookie, never from the request body or query (SECURITY.md §2).
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.reason_codes import ErrorCode
from app.core.sessions import COOKIE_NAME, resolve_employee
from app.db.models import Employee
from app.db.session import SessionLocal


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_employee(
    db: Session = Depends(get_db),
    hr_session: str | None = Cookie(default=None),
) -> Employee:
    emp = resolve_employee(db, hr_session)
    if emp is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": ErrorCode.UNAUTHENTICATED.value, "message": "Sign in required."},
        )
    return emp


def require_hr_admin(emp: Employee = Depends(current_employee)) -> Employee:
    """Guard for the HR-admin surface. The role comes only from the session-resolved employee,
    never the client (SECURITY.md §2); a non-admin is rejected with 403 before any team read."""
    if emp.role != "hr_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": ErrorCode.FORBIDDEN.value, "message": "HR admin access required."},
        )
    return emp


__all__ = ["get_db", "current_employee", "require_hr_admin", "COOKIE_NAME"]
