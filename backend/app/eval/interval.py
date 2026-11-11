"""Wilson score interval (95%, two-sided) — the same computation the gate script uses.

Reporting k of n with its interval keeps small-sample results honest (AI_QUALITY.md).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

Z = 1.96


@dataclass(frozen=True)
class Interval:
    k: int
    n: int
    point: float
    low: float
    high: float

    def __str__(self) -> str:
        return (
            f"{self.k}/{self.n} = {self.point * 100:.1f}%, "
            f"95% interval {self.low * 100:.1f} to {self.high * 100:.1f}%"
        )


def wilson(k: int, n: int) -> Interval:
    if n <= 0:
        return Interval(k, n, 0.0, 0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / d
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return Interval(k, n, p, max(0.0, centre - half), min(1.0, centre + half))


def passes_lower(k: int, n: int, min_pct: float) -> bool:
    """A success-rate gate: the lower bound must be at least min_pct percent."""
    return wilson(k, n).low * 100 >= min_pct
