"""Security checks (Phase 7): headers, denial-of-wallet stop switch, safe errors."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.ratelimit import RateLimiter
from app.main import app

client = TestClient(app)


def test_security_headers_present() -> None:
    r = client.get("/api/v1/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in r.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in r.headers.get("Content-Security-Policy", "")


def test_cap_of_zero_is_a_hard_stop() -> None:
    # Denial-of-wallet stop switch: a limit of 0 denies everything (set daily_query_cap=0).
    rl = RateLimiter()
    assert rl.allow("k", 0, 60) is False
    assert rl.allow("k", 0, 60) is False


def test_rate_limiter_enforces_window() -> None:
    rl = RateLimiter()
    results = [rl.allow("k", 3, 60) for _ in range(5)]
    assert results == [True, True, True, False, False]
