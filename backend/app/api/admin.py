"""HR-admin endpoints: whole-company team aggregates for the admin dashboard (PRD F).

Read-only. Gated by require_hr_admin, so only a signed-in hr_admin (role resolved from the
server-side session) reaches it; a normal employee gets 403. No LLM calls, no cost.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.admin.service import team_overview
from app.api.deps import get_db, require_hr_admin
from app.db.models import Employee

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/team")
def team(
    _: Employee = Depends(require_hr_admin),
    db: Session = Depends(get_db),
) -> dict:
    overview = team_overview(db)
    return {"success": True, "data": asdict(overview)}
