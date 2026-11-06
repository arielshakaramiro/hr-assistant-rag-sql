"""Server-side session service. The cookie holds an opaque token; only its hash is stored,
so a database read cannot recover a live session (SECURITY.md §2, §6).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.security import hash_token, new_session_token
from app.db.models import Employee, Session

COOKIE_NAME = "hr_session"


def create_session(db: DbSession, employee_id: int) -> str:
    """Create a session row and return the raw token to set in the cookie."""
    token = new_session_token()
    now = datetime.now(UTC)
    db.add(
        Session(
            id=hash_token(token),
            employee_id=employee_id,
            created_at=now,
            expires_at=now + timedelta(hours=settings.session_ttl_hours),
        )
    )
    db.commit()
    return token


def resolve_employee(db: DbSession, token: str | None) -> Employee | None:
    """Return the signed-in employee for a cookie token, or None if invalid/expired/revoked."""
    if not token:
        return None
    row = db.get(Session, hash_token(token))
    if row is None or row.revoked_at is not None:
        return None
    if row.expires_at <= datetime.now(UTC):
        return None
    return db.scalar(select(Employee).where(Employee.id == row.employee_id))


def revoke_session(db: DbSession, token: str | None) -> None:
    if not token:
        return
    row = db.get(Session, hash_token(token))
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        db.commit()
