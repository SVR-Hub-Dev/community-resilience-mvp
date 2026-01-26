"""Initial schema - create core tables

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding dimension (384 for all-MiniLM-L6-v2)
EMBEDDING_DIM = 384


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create community_knowledge table
    op.create_table(
        'community_knowledge',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tags', sa.ARRAY(sa.String())),
        sa.Column('location', sa.String()),
        sa.Column('hazard_type', sa.String()),
        sa.Column('source', sa.String()),
        sa.Column('embedding', Vector(EMBEDDING_DIM)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_community_knowledge_id', 'community_knowledge', ['id'])
    op.create_index('ix_community_knowledge_hazard_type', 'community_knowledge', ['hazard_type'])

    # Create community_event table
    op.create_table(
        'community_event',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('location', sa.String()),
        sa.Column('severity', sa.Integer()),
        sa.Column('reported_by', sa.String()),
        sa.Column('embedding', Vector(EMBEDDING_DIM)),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_community_event_id', 'community_event', ['id'])
    op.create_index('ix_community_event_event_type', 'community_event', ['event_type'])

    # Create community_asset table
    op.create_table(
        'community_asset',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('asset_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('location', sa.String()),
        sa.Column('capacity', sa.Integer()),
        sa.Column('status', sa.String()),
        sa.Column('tags', sa.ARRAY(sa.String())),
        sa.Column('embedding', Vector(EMBEDDING_DIM)),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_community_asset_id', 'community_asset', ['id'])
    op.create_index('ix_community_asset_asset_type', 'community_asset', ['asset_type'])
    op.create_index('ix_community_asset_status', 'community_asset', ['status'])

    # Create model_feedback_log table
    op.create_table(
        'model_feedback_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_input', sa.Text(), nullable=False),
        sa.Column('retrieved_knowledge_ids', sa.ARRAY(sa.Integer())),
        sa.Column('retrieved_asset_ids', sa.ARRAY(sa.Integer())),
        sa.Column('model_output', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer()),
        sa.Column('comments', sa.Text()),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_model_feedback_log_id', 'model_feedback_log', ['id'])
    op.create_index('ix_model_feedback_log_rating', 'model_feedback_log', ['rating'])


def downgrade() -> None:
    op.drop_table('model_feedback_log')
    op.drop_table('community_asset')
    op.drop_table('community_event')
    op.drop_table('community_knowledge')
    op.execute('DROP EXTENSION IF EXISTS vector')
