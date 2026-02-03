"""Add document processing fields for hybrid cloud/local deployment.

Revision ID: 003_document_processing
Revises: 003a
Create Date: 2026-01-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_document_processing"
down_revision: Union[str, None] = "003a"  # Depends on documents table creation
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add document processing fields to documents table
    op.add_column(
        "documents",
        sa.Column(
            "needs_full_processing",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "processing_mode",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "documents",
        sa.Column("raw_file_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "processing_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
    )

    # Add index for finding unprocessed documents
    op.create_index(
        "ix_documents_needs_full_processing",
        "documents",
        ["needs_full_processing"],
        postgresql_where=sa.text("needs_full_processing = true"),
    )
    op.create_index(
        "ix_documents_processing_status",
        "documents",
        ["processing_status"],
    )

    # Create sync_metadata table
    op.create_table(
        "sync_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(100), unique=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create sync_log table
    op.create_table(
        "sync_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "sync_type",
            sa.String(50),
            nullable=False,
        ),  # 'pull', 'push', 'process'
        sa.Column(
            "status", sa.String(50), nullable=False
        ),  # 'started', 'completed', 'failed'
        sa.Column("documents_processed", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add index for sync_log queries
    op.create_index(
        "ix_sync_log_sync_type_status",
        "sync_log",
        ["sync_type", "status"],
    )
    op.create_index(
        "ix_sync_log_started_at",
        "sync_log",
        ["started_at"],
    )


def downgrade() -> None:
    # Drop sync tables
    op.drop_index("ix_sync_log_started_at", table_name="sync_log")
    op.drop_index("ix_sync_log_sync_type_status", table_name="sync_log")
    op.drop_table("sync_log")
    op.drop_table("sync_metadata")

    # Drop document processing columns
    op.drop_index("ix_documents_processing_status", table_name="documents")
    op.drop_index("ix_documents_needs_full_processing", table_name="documents")
    op.drop_column("documents", "processing_status")
    op.drop_column("documents", "processed_at")
    op.drop_column("documents", "raw_file_path")
    op.drop_column("documents", "processing_mode")
    op.drop_column("documents", "needs_full_processing")
