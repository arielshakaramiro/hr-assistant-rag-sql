"""Shared test fixtures. Tests that need the database are marked with `db` and skipped
when Postgres is not reachable, so the unit suite still runs without a container."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.ratelimit import chat_limiter, login_limiter
from app.db.session import engine


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> None:
    """Each test starts with empty rate-limit windows so shared in-memory state doesn't leak."""
    login_limiter.reset()
    chat_limiter.reset()


def _db_available() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _db_available(), reason="Postgres not reachable")
