"""SQLAlchemy ORM models for support system."""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from models.models import Base


class TicketStatus(str, PyEnum):
    """Support ticket status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, PyEnum):
    """Support ticket priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicket(Base):
    """
    Support ticket model.

    Stores user-submitted support requests with status tracking.
    """

    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default=TicketStatus.OPEN.value)
    priority = Column(String(20), nullable=False, default=TicketPriority.MEDIUM.value)
    assigned_to = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="support_tickets")
    assignee = relationship("User", foreign_keys=[assigned_to])
    responses = relationship(
        "TicketResponse", back_populates="ticket", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SupportTicket(id={self.id}, subject='{self.subject[:30]}...', status='{self.status}')>"


class TicketResponse(Base):
    """
    Response to a support ticket.

    Can be from user or admin. Internal notes are not visible to users.
    """

    __tablename__ = "ticket_responses"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(
        Integer,
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # Internal notes not visible to user
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    ticket = relationship("SupportTicket", back_populates="responses")
    user = relationship("User")

    def __repr__(self):
        return f"<TicketResponse(id={self.id}, ticket_id={self.ticket_id})>"


class ContactSubmission(Base):
    """
    Contact form submission from public visitors.

    Stores inquiries from non-authenticated users.
    """

    __tablename__ = "contact_submissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ContactSubmission(id={self.id}, email='{self.email}', subject='{self.subject[:30]}...')>"
