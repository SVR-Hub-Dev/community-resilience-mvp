"""Support system API endpoints."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from auth.dependencies import require_admin, require_viewer
from auth.models import User
from config import settings
from db import get_db
from models.support_models import (
    ContactSubmission,
    SupportTicket,
    TicketPriority,
    TicketResponse,
    TicketStatus,
)
from services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["support"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class ContactSubmitIn(BaseModel):
    """Input model for contact form submission."""

    name: str
    email: EmailStr
    subject: str
    message: str


class ContactSubmitOut(BaseModel):
    """Output model for contact form submission."""

    success: bool
    message: str


class ContactSubmissionOut(BaseModel):
    """Output model for a contact submission."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    subject: str
    message: str
    is_read: bool
    created_at: datetime


class ContactSubmissionListOut(BaseModel):
    """Paginated list of contact submissions."""

    contacts: List[ContactSubmissionOut]
    total: int


class TicketCreateIn(BaseModel):
    """Input model for creating a support ticket."""

    subject: str
    description: str
    priority: Optional[str] = TicketPriority.MEDIUM.value


class TicketUpdateIn(BaseModel):
    """Input model for updating a support ticket (admin)."""

    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None


class TicketResponseIn(BaseModel):
    """Input model for adding a response to a ticket."""

    message: str
    is_internal: bool = False


class UserBrief(BaseModel):
    """Brief user info for ticket responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: Optional[str] = None


class TicketResponseOut(BaseModel):
    """Output model for a ticket response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    user_id: Optional[int] = None
    message: str
    is_internal: bool
    created_at: datetime
    user: Optional[UserBrief] = None


class TicketOut(BaseModel):
    """Output model for a support ticket."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    subject: str
    description: str
    status: str
    priority: str
    assigned_to: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None


class TicketDetailOut(TicketOut):
    """Detailed ticket with responses and user info."""

    user: Optional[UserBrief] = None
    assignee: Optional[UserBrief] = None
    responses: List[TicketResponseOut] = []


class TicketListOut(BaseModel):
    """Paginated list of tickets."""

    tickets: List[TicketOut]
    total: int


# ── Public endpoints ──────────────────────────────────────────────────────────


@router.post("/contact", response_model=ContactSubmitOut)
def submit_contact(
    payload: ContactSubmitIn,
    db: Session = Depends(get_db),
):
    """
    Submit a contact form (public, no auth required).

    Stores the submission and sends notification email to admin.
    """
    logger.info(
        "support.contact.submit",
        extra={"name": payload.name, "email": payload.email, "subject": payload.subject},
    )

    # Create contact submission record
    submission = ContactSubmission(
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Send notification email to admin
    email_service.send_contact_notification(
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
        contact_id=submission.id,
    )

    logger.info(
        "support.contact.created",
        extra={"contact_id": submission.id},
    )

    return ContactSubmitOut(
        success=True,
        message="Thank you for your message. We'll get back to you soon.",
    )


# ── User ticket endpoints ─────────────────────────────────────────────────────


@router.get("/support/tickets", response_model=TicketListOut)
def list_user_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List the current user's support tickets."""
    query = db.query(SupportTicket).filter(SupportTicket.user_id == user.id)

    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)

    total = query.count()
    tickets = (
        query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()
    )

    return TicketListOut(
        tickets=[TicketOut.model_validate(t) for t in tickets],
        total=total,
    )


@router.post("/support/tickets", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreateIn,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Create a new support ticket."""
    # Validate priority
    if payload.priority not in [p.value for p in TicketPriority]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: {', '.join([p.value for p in TicketPriority])}",
        )

    ticket = SupportTicket(
        user_id=user.id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        status=TicketStatus.OPEN.value,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    logger.info(
        "support.ticket.created",
        extra={"ticket_id": ticket.id, "user_id": user.id, "subject": ticket.subject},
    )

    # Send confirmation email to user
    ticket_url = f"{settings.frontend_url}/support/{ticket.id}"
    email_service.send_ticket_confirmation(
        to=user.email,
        ticket_id=ticket.id,
        subject=ticket.subject,
        ticket_url=ticket_url,
    )

    # Send notification to admin
    email_service.send_new_ticket_notification(
        ticket_id=ticket.id,
        user_email=user.email,
        subject=ticket.subject,
        priority=ticket.priority,
        description=ticket.description,
    )

    return TicketOut.model_validate(ticket)


@router.get("/support/tickets/{ticket_id}", response_model=TicketDetailOut)
def get_user_ticket(
    ticket_id: int,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Get a specific ticket (must be owned by user or user is admin)."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Check ownership (unless admin)
    if ticket.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get responses (exclude internal notes for non-admins)
    responses = (
        db.query(TicketResponse)
        .filter(TicketResponse.ticket_id == ticket_id)
        .order_by(TicketResponse.created_at.asc())
        .all()
    )

    # Filter internal notes for non-admin users
    if user.role != "admin":
        responses = [r for r in responses if not r.is_internal]

    # Build response with user info
    response_out = []
    for r in responses:
        r_out = TicketResponseOut.model_validate(r)
        if r.user:
            r_out.user = UserBrief.model_validate(r.user)
        response_out.append(r_out)

    ticket_out = TicketDetailOut.model_validate(ticket)
    ticket_out.responses = response_out

    if ticket.user:
        ticket_out.user = UserBrief.model_validate(ticket.user)
    if ticket.assignee:
        ticket_out.assignee = UserBrief.model_validate(ticket.assignee)

    return ticket_out


@router.post(
    "/support/tickets/{ticket_id}/responses",
    response_model=TicketResponseOut,
    status_code=status.HTTP_201_CREATED,
)
def add_ticket_response(
    ticket_id: int,
    payload: TicketResponseIn,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Add a response to a ticket."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Check ownership (unless admin)
    if ticket.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Only admins can add internal notes
    is_internal = payload.is_internal if user.role == "admin" else False

    response = TicketResponse(
        ticket_id=ticket_id,
        user_id=user.id,
        message=payload.message,
        is_internal=is_internal,
    )
    db.add(response)

    # Update ticket timestamp
    ticket.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(response)

    logger.info(
        "support.ticket.response_added",
        extra={
            "ticket_id": ticket_id,
            "response_id": response.id,
            "user_id": user.id,
            "is_internal": is_internal,
        },
    )

    response_out = TicketResponseOut.model_validate(response)
    response_out.user = UserBrief.model_validate(user)

    return response_out


# ── Admin endpoints ───────────────────────────────────────────────────────────


@router.get("/admin/support/tickets", response_model=TicketListOut)
def admin_list_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    assigned_to: Optional[int] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all support tickets (admin only)."""
    query = db.query(SupportTicket)

    if status_filter:
        query = query.filter(SupportTicket.status == status_filter)
    if priority_filter:
        query = query.filter(SupportTicket.priority == priority_filter)
    if assigned_to is not None:
        query = query.filter(SupportTicket.assigned_to == assigned_to)

    total = query.count()
    tickets = (
        query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()
    )

    return TicketListOut(
        tickets=[TicketOut.model_validate(t) for t in tickets],
        total=total,
    )


@router.get("/admin/support/tickets/{ticket_id}", response_model=TicketDetailOut)
def admin_get_ticket(
    ticket_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get any ticket (admin only)."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Get all responses including internal notes
    responses = (
        db.query(TicketResponse)
        .filter(TicketResponse.ticket_id == ticket_id)
        .order_by(TicketResponse.created_at.asc())
        .all()
    )

    response_out = []
    for r in responses:
        r_out = TicketResponseOut.model_validate(r)
        if r.user:
            r_out.user = UserBrief.model_validate(r.user)
        response_out.append(r_out)

    ticket_out = TicketDetailOut.model_validate(ticket)
    ticket_out.responses = response_out

    if ticket.user:
        ticket_out.user = UserBrief.model_validate(ticket.user)
    if ticket.assignee:
        ticket_out.assignee = UserBrief.model_validate(ticket.assignee)

    return ticket_out


@router.put("/admin/support/tickets/{ticket_id}", response_model=TicketOut)
def admin_update_ticket(
    ticket_id: int,
    payload: TicketUpdateIn,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a ticket's status, priority, or assignment (admin only)."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # Validate status
    if payload.status is not None:
        if payload.status not in [s.value for s in TicketStatus]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join([s.value for s in TicketStatus])}",
            )
        ticket.status = payload.status

        # Set resolved_at when marking as resolved
        if payload.status == TicketStatus.RESOLVED.value and not ticket.resolved_at:
            ticket.resolved_at = datetime.now(timezone.utc)

    # Validate priority
    if payload.priority is not None:
        if payload.priority not in [p.value for p in TicketPriority]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Must be one of: {', '.join([p.value for p in TicketPriority])}",
            )
        ticket.priority = payload.priority

    # Validate assignee
    if payload.assigned_to is not None:
        assignee = db.query(User).filter(User.id == payload.assigned_to).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee not found",
            )
        ticket.assigned_to = payload.assigned_to

    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)

    logger.info(
        "support.ticket.updated",
        extra={
            "ticket_id": ticket_id,
            "admin_id": user.id,
            "changes": payload.model_dump(exclude_unset=True),
        },
    )

    return TicketOut.model_validate(ticket)


@router.post(
    "/admin/support/tickets/{ticket_id}/responses",
    response_model=TicketResponseOut,
    status_code=status.HTTP_201_CREATED,
)
def admin_add_response(
    ticket_id: int,
    payload: TicketResponseIn,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add an admin response to a ticket."""
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    response = TicketResponse(
        ticket_id=ticket_id,
        user_id=user.id,
        message=payload.message,
        is_internal=payload.is_internal,
    )
    db.add(response)

    # Update ticket to in_progress if it was open
    if ticket.status == TicketStatus.OPEN.value:
        ticket.status = TicketStatus.IN_PROGRESS.value

    ticket.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(response)

    logger.info(
        "support.ticket.admin_response",
        extra={
            "ticket_id": ticket_id,
            "response_id": response.id,
            "admin_id": user.id,
            "is_internal": payload.is_internal,
        },
    )

    response_out = TicketResponseOut.model_validate(response)
    response_out.user = UserBrief.model_validate(user)

    return response_out


# ── Admin contact endpoints ───────────────────────────────────────────────────


@router.get("/admin/support/contacts", response_model=ContactSubmissionListOut)
def admin_list_contacts(
    is_read: Optional[bool] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all contact form submissions (admin only)."""
    query = db.query(ContactSubmission)

    if is_read is not None:
        query = query.filter(ContactSubmission.is_read == is_read)

    total = query.count()
    contacts = (
        query.order_by(ContactSubmission.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return ContactSubmissionListOut(
        contacts=[ContactSubmissionOut.model_validate(c) for c in contacts],
        total=total,
    )


@router.put("/admin/support/contacts/{contact_id}/read")
def admin_mark_contact_read(
    contact_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Mark a contact submission as read (admin only)."""
    contact = db.query(ContactSubmission).filter(ContactSubmission.id == contact_id).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact submission not found",
        )

    contact.is_read = True
    db.commit()

    logger.info(
        "support.contact.marked_read",
        extra={"contact_id": contact_id, "admin_id": user.id},
    )

    return {"status": "success"}
