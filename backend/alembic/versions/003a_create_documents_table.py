"""Create documents table

Revision ID: 003a
Revises: 003
Create Date: 2026-02-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "003a"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding dimension (384 for all-MiniLM-L6-v2)
EMBEDDING_DIM = 384


def upgrade() -> None:
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tags", sa.ARRAY(sa.String())),
        sa.Column("location", sa.String()),
        sa.Column("hazard_type", sa.String()),
        sa.Column("source", sa.String()),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("ix_documents_id", "documents", ["id"])
    op.create_index("ix_documents_hazard_type", "documents", ["hazard_type"])


def downgrade() -> None:
    op.drop_table("documents")
