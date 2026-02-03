"""Add session_token and is_active columns to sessions table

Revision ID: 006
Revises: 005_add_support_system
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005_add_support_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add session_token column to sessions table
    op.add_column(
        'sessions',
        sa.Column('session_token', sa.String(128), unique=True, nullable=True)
    )
    op.create_index('ix_sessions_session_token', 'sessions', ['session_token'])

    # Add is_active column to sessions table
    op.add_column(
        'sessions',
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False)
    )
    op.create_index('ix_sessions_is_active', 'sessions', ['is_active'])

    # Make refresh_token_hash nullable (it was NOT NULL before)
    op.alter_column(
        'sessions',
        'refresh_token_hash',
        existing_type=sa.String(64),
        nullable=True
    )


def downgrade() -> None:
    # Remove is_active column
    op.drop_index('ix_sessions_is_active', table_name='sessions')
    op.drop_column('sessions', 'is_active')

    # Remove session_token column
    op.drop_index('ix_sessions_session_token', table_name='sessions')
    op.drop_column('sessions', 'session_token')

    # Make refresh_token_hash NOT NULL again
    op.alter_column(
        'sessions',
        'refresh_token_hash',
        existing_type=sa.String(64),
        nullable=False
    )
