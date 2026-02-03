"""add_support_system

Revision ID: 005_add_support_system
Revises: c197fb1903ea
Create Date: 2026-02-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_add_support_system"
down_revision: Union[str, None] = "c197fb1903ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create support_tickets table
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_support_tickets_id"),
        "support_tickets",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_user_id"),
        "support_tickets",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_support_tickets_assigned_to"),
        "support_tickets",
        ["assigned_to"],
        unique=False,
    )

    # Create ticket_responses table
    op.create_table(
        "ticket_responses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_responses_id"),
        "ticket_responses",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_responses_ticket_id"),
        "ticket_responses",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_responses_user_id"),
        "ticket_responses",
        ["user_id"],
        unique=False,
    )

    # Create contact_submissions table
    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contact_submissions_id"),
        "contact_submissions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_contact_submissions_is_read"),
        "contact_submissions",
        ["is_read"],
        unique=False,
    )


def downgrade() -> None:
    # Drop contact_submissions
    op.drop_index(op.f("ix_contact_submissions_is_read"), table_name="contact_submissions")
    op.drop_index(op.f("ix_contact_submissions_id"), table_name="contact_submissions")
    op.drop_table("contact_submissions")

    # Drop ticket_responses
    op.drop_index(op.f("ix_ticket_responses_user_id"), table_name="ticket_responses")
    op.drop_index(op.f("ix_ticket_responses_ticket_id"), table_name="ticket_responses")
    op.drop_index(op.f("ix_ticket_responses_id"), table_name="ticket_responses")
    op.drop_table("ticket_responses")

    # Drop support_tickets
    op.drop_index(op.f("ix_support_tickets_assigned_to"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_user_id"), table_name="support_tickets")
    op.drop_index(op.f("ix_support_tickets_id"), table_name="support_tickets")
    op.drop_table("support_tickets")
