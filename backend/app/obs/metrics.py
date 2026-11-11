"""Per-query observability. Records metadata ONLY — never question/answer text (privacy, by
design: text is stored only for feedback-tagged items, see app.api.feedback).

Each handled chat request writes one QueryMetric row with the route, latency, estimated cost
and outcome. The /metrics endpoint aggregates these for the dashboard and the README.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import QueryMetric

logger = logging.getLogger("hr.metrics")


@dataclass
class MetricsSummary:
    count: int
    p95_latency_ms: int
    mean_cost_usd: float
    failure_rate: float
    by_route: dict[str, int]


def record(
    db: Session, route: str, latency_ms: int, outcome: str, est_cost_usd: float = 0.0
) -> None:
    db.add(
        QueryMetric(route=route, latency_ms=latency_ms, outcome=outcome, est_cost_usd=est_cost_usd)
    )
    db.commit()
    # Structured log line (no Q/A text) for external aggregation if wired later.
    logger.info(
        json.dumps(
            {"route": route, "latency_ms": latency_ms, "outcome": outcome, "cost": est_cost_usd}
        )
    )


@contextmanager
def timed():
    """Measure wall-clock latency of the enclosed block in milliseconds."""
    start = time.monotonic()
    holder = {"ms": 0}
    try:
        yield holder
    finally:
        holder["ms"] = int((time.monotonic() - start) * 1000)


def summary(db: Session) -> MetricsSummary:
    total = db.scalar(select(func.count(QueryMetric.id))) or 0
    if total == 0:
        return MetricsSummary(0, 0, 0.0, 0.0, {r: 0 for r in ("POLICY", "DATA", "BOTH", "CLARIFY")})

    # p95 latency via percentile_cont (Postgres).
    p95 = db.scalar(select(func.percentile_cont(0.95).within_group(QueryMetric.latency_ms.asc())))
    mean_cost = db.scalar(select(func.avg(QueryMetric.est_cost_usd))) or 0
    failures = (
        db.scalar(select(func.count(QueryMetric.id)).where(QueryMetric.outcome == "error")) or 0
    )
    rows = db.execute(
        select(QueryMetric.route, func.count(QueryMetric.id)).group_by(QueryMetric.route)
    ).all()
    by_route = {r: 0 for r in ("POLICY", "DATA", "BOTH", "CLARIFY")}
    for route, n in rows:
        by_route[route] = n
    return MetricsSummary(
        count=total,
        p95_latency_ms=int(p95 or 0),
        mean_cost_usd=round(float(mean_cost), 6),
        failure_rate=round(failures / total, 4),
        by_route=by_route,
    )
