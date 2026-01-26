"""Add authentication tables - users, api_keys, sessions

Revision ID: 002
Revises: 001
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('oauth_provider', sa.String(50)),
        sa.Column('oauth_id', sa.String(255)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('admin', 'editor', 'viewer')", name='valid_role'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])
    op.create_index('ix_users_oauth', 'users', ['oauth_provider', 'oauth_id'], unique=True)

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('scopes', sa.ARRAY(sa.String())),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_api_keys_id', 'api_keys', ['id'])
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_sessions_id', 'sessions', ['id'])
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_refresh_token_hash', 'sessions', ['refresh_token_hash'])
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'])


def downgrade() -> None:
    op.drop_table('sessions')
    op.drop_table('api_keys')
    op.drop_table('users')
