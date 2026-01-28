"""Add password_hash, totp_secret, totp_enabled to users table

Revision ID: 003
Revises: 002
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(255)))
    op.add_column('users', sa.Column('totp_secret', sa.String(32)))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'password_hash')
