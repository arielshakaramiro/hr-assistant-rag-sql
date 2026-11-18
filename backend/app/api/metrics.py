"""Metrics endpoint: aggregate operational metadata for the dashboard (API.md §5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_employee, get_db
from app.db.models import Employee
from app.obs.metrics import summary

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics")
def metrics(
    _: Employee = Depends(current_employee),
    db: Session = Depends(get_db),
) -> dict:
    s = summary(db)
    return {
        "success": True,
        "data": {
            "count": s.count,
            "p95_latency_ms": s.p95_latency_ms,
            "p95_ttft_ms": s.p95_ttft_ms,
            "mean_cost_usd": s.mean_cost_usd,
            "failure_rate": s.failure_rate,
            "by_route": s.by_route,
        },
    }
