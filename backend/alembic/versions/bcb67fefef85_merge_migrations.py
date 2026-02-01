"""merge_migrations

Revision ID: bcb67fefef85
Revises: 003_document_processing, 004
Create Date: 2026-02-01 11:43:52.696459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'bcb67fefef85'
down_revision: Union[str, None] = ('003_document_processing', '004')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
