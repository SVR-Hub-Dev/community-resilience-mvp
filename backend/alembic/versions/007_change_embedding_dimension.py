"""Change embedding dimension from 384 to 512 for Voyage AI

Revision ID: 007
Revises: 006
Create Date: 2026-02-04

This migration changes the embedding vector dimension from 384 (all-MiniLM-L6-v2)
to 512 (voyage-3-lite). Existing embeddings are cleared as they are incompatible.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_DIM = 384
NEW_DIM = 512

# Tables with embedding columns
TABLES_WITH_EMBEDDINGS = [
    'community_knowledge',
    'community_event',
    'community_asset',
    'documents',
]


def upgrade() -> None:
    # For each table with embeddings, alter the vector column dimension
    # PostgreSQL pgvector allows altering the dimension with ALTER COLUMN TYPE
    for table in TABLES_WITH_EMBEDDINGS:
        # First, set existing embeddings to NULL (they're incompatible)
        op.execute(f"UPDATE {table} SET embedding = NULL WHERE embedding IS NOT NULL")
        # Then alter the column type to the new dimension
        op.execute(f"ALTER TABLE {table} ALTER COLUMN embedding TYPE vector({NEW_DIM})")


def downgrade() -> None:
    # Revert to old dimension
    for table in TABLES_WITH_EMBEDDINGS:
        # Clear embeddings (incompatible)
        op.execute(f"UPDATE {table} SET embedding = NULL WHERE embedding IS NOT NULL")
        # Alter back to old dimension
        op.execute(f"ALTER TABLE {table} ALTER COLUMN embedding TYPE vector({OLD_DIM})")
