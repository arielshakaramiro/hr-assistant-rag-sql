"""Database engines and sessions.

Two engines by design (SECURITY.md, ADR-4):
- `engine`      : the app role (read/write) for auth, feedback, metrics, ingestion.
- `engine_ro`   : the read-only role the SQL agent uses. It can only SELECT; even a
                  wrong or injected query cannot write. Row scope is applied on top.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
engine_ro = create_engine(settings.database_url_ro, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
