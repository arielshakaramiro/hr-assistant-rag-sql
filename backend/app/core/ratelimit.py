"""In-memory fixed-window rate limiter (demo scale, single process).

Used for login (per email + per IP) and chat (per session + a global daily cap tied to the
spend ceiling). A real multi-instance deployment would move this to Redis; noted in day-2.
"""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def reset(self) -> None:
        self._hits.clear()

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        """Return True if `key` is under `limit` within the trailing window; records the hit."""
        if limit <= 0:
            return False  # a limit of 0 is a hard stop (e.g. the spend-cap stop switch)
        now = time.monotonic()
        cutoff = now - window_seconds
        hits = [t for t in self._hits[key] if t > cutoff]
        if len(hits) >= limit:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


# Process-wide limiters.
login_limiter = RateLimiter()
chat_limiter = RateLimiter()
