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


__all__ = ["get_db", "current_employee", "COOKIE_NAME"]
