"""Authentication endpoints: login, logout, me (API.md §3-5, SECURITY.md §2)."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_employee, get_db
from app.core.config import settings
from app.core.ratelimit import login_limiter
from app.core.reason_codes import ErrorCode
from app.core.security import verify_password
from app.core.sessions import COOKIE_NAME, create_session, revoke_session
from app.db.models import Employee

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: int
    full_name: str
    department: str
    role: str


def _set_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=60 * 60 * settings.session_ttl_hours,
        path="/",
    )


@router.post("/login")
def login(
    body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> dict:
    # Rate-limit per email and per client IP (10 attempts / 5 min each).
    ip = request.client.host if request.client else "unknown"
    for key in (f"login:email:{body.email}", f"login:ip:{ip}"):
        if not login_limiter.allow(key, limit=10, window_seconds=300):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": ErrorCode.RATE_LIMITED.value,
                    "message": "Too many attempts. Try again shortly.",
                },
            )
    emp = db.scalar(select(Employee).where(Employee.email == body.email))
    # Same message whether the email is unknown or the password is wrong (no account probing).
    if emp is None or not verify_password(body.password, emp.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.UNAUTHENTICATED.value,
                "message": "Email or password is incorrect.",
            },
        )
    token = create_session(db, emp.id)
    _set_cookie(response, token)
    return {"success": True, "data": {"id": emp.id, "full_name": emp.full_name}}


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    hr_session: str | None = Cookie(default=None),
) -> dict:
    revoke_session(db, hr_session)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"success": True}


@router.get("/me")
def me(emp: Employee = Depends(current_employee)) -> dict:
    return {
        "success": True,
        "data": MeResponse(
            id=emp.id, full_name=emp.full_name, department=emp.department, role=emp.role
        ).model_dump(),
    }
