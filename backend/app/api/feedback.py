"""Feedback endpoint. Storing question+answer text happens ONLY here, on an explicit
thumbs rating — the one consented path (COMPLIANCE.md, AI_QUALITY.md day-2). These rows
become candidate golden-set cases. No other endpoint persists Q/A text.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_employee, get_db
from app.db.models import Employee, Feedback

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=8000)
    route: str = Field(max_length=10)
    rating: str = Field(pattern="^(up|down)$")


@router.post("/feedback")
def submit(
    body: FeedbackRequest,
    emp: Employee = Depends(current_employee),
    db: Session = Depends(get_db),
) -> dict:
    db.add(
        Feedback(
            employee_id=emp.id,
            question_text=body.question,
            answer_text=body.answer,
            route=body.route,
            rating=body.rating,
        )
    )
    db.commit()
    return {"success": True}
