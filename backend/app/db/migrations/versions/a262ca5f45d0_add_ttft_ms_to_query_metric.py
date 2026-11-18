"""add ttft_ms to query_metric

Records time-to-first-token for streamed answers (TRD §5). Nullable: non-streamed `/ask` rows
and pre-migration rows have no first-token timing.

Revision ID: a262ca5f45d0
Revises: 9345ef04c638
Create Date: 2026-11-16 22:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a262ca5f45d0"
down_revision: str | Sequence[str] | None = "9345ef04c638"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_metric", sa.Column("ttft_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_metric", "ttft_ms")
