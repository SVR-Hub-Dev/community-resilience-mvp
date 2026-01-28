"""Add knowledge graph tables - entities, relationships, evidence

Revision ID: 004
Revises: 003
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Embedding dimension (384 for all-MiniLM-L6-v2)
EMBEDDING_DIM = 384


def upgrade() -> None:
    # Enable pg_trgm for fuzzy text matching
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # Create kg_entities table
    op.create_table(
        'kg_entities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_subtype', sa.String(50)),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('canonical_name', sa.Text()),
        sa.Column('attributes', sa.JSON(), server_default='{}'),
        sa.Column('location_text', sa.Text()),
        sa.Column('confidence_score', sa.Float(), server_default='0.5'),
        sa.Column('extraction_method', sa.String(50)),
        sa.Column('embedding', Vector(EMBEDDING_DIM)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), server_default='false'),
        sa.UniqueConstraint('canonical_name', 'entity_type', name='uq_kg_entity_canonical_type'),
    )
    op.create_index('ix_kg_entities_id', 'kg_entities', ['id'])
    op.create_index('ix_kg_entities_entity_type', 'kg_entities', ['entity_type'])
    op.create_index('ix_kg_entities_entity_type_subtype', 'kg_entities', ['entity_type', 'entity_subtype'])
    op.create_index('ix_kg_entities_canonical_name', 'kg_entities', ['canonical_name'])
    # Trigram index for fuzzy name search
    op.execute(
        'CREATE INDEX ix_kg_entities_name_trgm ON kg_entities '
        'USING gin (name gin_trgm_ops)'
    )

    # Create kg_relationships table
    op.create_table(
        'kg_relationships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_entity_id', sa.Integer(), sa.ForeignKey('kg_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_entity_id', sa.Integer(), sa.ForeignKey('kg_entities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relationship_type', sa.String(100), nullable=False),
        sa.Column('attributes', sa.JSON(), server_default='{}'),
        sa.Column('confidence_score', sa.Float(), server_default='0.5'),
        sa.Column('extraction_method', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), server_default='false'),
        sa.UniqueConstraint(
            'source_entity_id', 'target_entity_id', 'relationship_type',
            name='uq_kg_relationship',
        ),
    )
    op.create_index('ix_kg_relationships_id', 'kg_relationships', ['id'])
    op.create_index('ix_kg_relationships_source', 'kg_relationships', ['source_entity_id'])
    op.create_index('ix_kg_relationships_target', 'kg_relationships', ['target_entity_id'])
    op.create_index('ix_kg_relationships_type', 'kg_relationships', ['relationship_type'])
    op.create_index('ix_kg_relationships_source_type', 'kg_relationships', ['source_entity_id', 'relationship_type'])

    # Create kg_evidence table
    op.create_table(
        'kg_evidence',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entity_id', sa.Integer(), sa.ForeignKey('kg_entities.id', ondelete='CASCADE')),
        sa.Column('relationship_id', sa.Integer(), sa.ForeignKey('kg_relationships.id', ondelete='CASCADE')),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evidence_text', sa.Text()),
        sa.Column('extraction_confidence', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            '(entity_id IS NOT NULL AND relationship_id IS NULL) OR '
            '(entity_id IS NULL AND relationship_id IS NOT NULL)',
            name='ck_kg_evidence_target',
        ),
    )
    op.create_index('ix_kg_evidence_id', 'kg_evidence', ['id'])
    op.create_index('ix_kg_evidence_entity_id', 'kg_evidence', ['entity_id'])
    op.create_index('ix_kg_evidence_relationship_id', 'kg_evidence', ['relationship_id'])
    op.create_index('ix_kg_evidence_document_id', 'kg_evidence', ['document_id'])

    # Add kg_extraction_status to documents table
    op.add_column(
        'documents',
        sa.Column('kg_extraction_status', sa.String(50), server_default='pending'),
    )
    op.create_index('ix_documents_kg_extraction_status', 'documents', ['kg_extraction_status'])


def downgrade() -> None:
    # Drop kg_extraction_status from documents
    op.drop_index('ix_documents_kg_extraction_status', table_name='documents')
    op.drop_column('documents', 'kg_extraction_status')

    # Drop kg_evidence
    op.drop_table('kg_evidence')

    # Drop kg_relationships
    op.drop_table('kg_relationships')

    # Drop kg_entities (trigram index drops automatically with table)
    op.drop_table('kg_entities')
