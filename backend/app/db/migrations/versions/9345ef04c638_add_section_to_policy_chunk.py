"""add section to policy_chunk and own the embedding index

Adds the citable section heading to each policy chunk. The ivfflat embedding index is
moved into migrations here (it was previously created at seed time), so the schema is
fully described by migrations.

Revision ID: 9345ef04c638
Revises: c237eabb08a5
Create Date: 2026-11-10 23:44:43.321436
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9345ef04c638"
down_revision: str | Sequence[str] | None = "c237eabb08a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add with a server default so existing rows get a value, then drop the default
    # (new rows are always given a section by the ingestion code).
    op.add_column(
        "policy_chunk",
        sa.Column("section", sa.String(length=160), nullable=False, server_default=""),
    )
    op.alter_column("policy_chunk", "section", server_default=None)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policy_chunk_embedding "
        "ON policy_chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_policy_chunk_embedding")
    op.drop_column("policy_chunk", "section")
