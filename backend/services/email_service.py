"""Email service using Resend for transactional emails."""

import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

# Lazy import resend to avoid import errors if not installed
_resend = None


def _get_resend():
    """Lazy load resend module."""
    global _resend
    if _resend is None:
        try:
            import resend
            resend.api_key = settings.resend_api_key
            _resend = resend
        except ImportError:
            logger.error("Resend package not installed. Run: pip install resend")
            raise
    return _resend


class EmailService:
    """Service for sending transactional emails via Resend."""

    def __init__(self):
        self.from_address = f"{settings.email_from_name} <{settings.email_from_address}>"
        self.admin_email = settings.admin_email
        self.enabled = settings.email_enabled and settings.email_configured

    def _send(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
    ) -> bool:
        """
        Send an email via Resend.

        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML content
            text: Plain text fallback (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(
                "email.send.disabled",
                extra={"to": to, "subject": subject},
            )
            return False

        try:
            resend = _get_resend()
            params = {
                "from": self.from_address,
                "to": [to],
                "subject": subject,
                "html": html,
            }
            if text:
                params["text"] = text

            result = resend.Emails.send(params)
            logger.info(
                "email.send.success",
                extra={"to": to, "subject": subject, "id": result.get("id")},
            )
            return True
        except Exception as e:
            logger.error(
                "email.send.failed",
                extra={"to": to, "subject": subject, "error": str(e)},
                exc_info=True,
            )
            return False

    def send_password_reset(
        self,
        to: str,
        reset_url: str,
        expires_in_hours: int = 1,
    ) -> bool:
        """
        Send a password reset email.

        Args:
            to: Recipient email address
            reset_url: Full URL for password reset
            expires_in_hours: Hours until link expires

        Returns:
            True if sent successfully
        """
        subject = "Reset Your Password"
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #2563eb; margin-bottom: 24px;">Reset Your Password</h1>
    <p>You requested a password reset for your Community Resilience account.</p>
    <p>Click the button below to reset your password:</p>
    <p style="margin: 32px 0;">
        <a href="{reset_url}"
           style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
            Reset Password
        </a>
    </p>
    <p style="color: #666; font-size: 14px;">
        This link will expire in {expires_in_hours} hour(s).
    </p>
    <p style="color: #666; font-size: 14px;">
        If you didn't request this, you can safely ignore this email.
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
    <p style="color: #999; font-size: 12px;">
        Community Resilience Platform
    </p>
</body>
</html>
"""
        text = f"""Reset Your Password

You requested a password reset for your Community Resilience account.

Click the link below to reset your password:
{reset_url}

This link will expire in {expires_in_hours} hour(s).

If you didn't request this, you can safely ignore this email.

---
Community Resilience Platform
"""
        return self._send(to, subject, html, text)

    def send_ticket_confirmation(
        self,
        to: str,
        ticket_id: int,
        subject: str,
        ticket_url: str,
    ) -> bool:
        """
        Send confirmation email when a support ticket is created.

        Args:
            to: Recipient email address
            ticket_id: Ticket ID number
            subject: Ticket subject
            ticket_url: URL to view ticket

        Returns:
            True if sent successfully
        """
        email_subject = f"Support Ticket #{ticket_id} Created"
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #2563eb; margin-bottom: 24px;">Support Ticket Created</h1>
    <p>Your support ticket has been submitted successfully.</p>
    <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin: 24px 0;">
        <p style="margin: 0;"><strong>Ticket #:</strong> {ticket_id}</p>
        <p style="margin: 8px 0 0;"><strong>Subject:</strong> {subject}</p>
    </div>
    <p>Our team will review your request and respond as soon as possible.</p>
    <p style="margin: 32px 0;">
        <a href="{ticket_url}"
           style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
            View Ticket
        </a>
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
    <p style="color: #999; font-size: 12px;">
        Community Resilience Platform
    </p>
</body>
</html>
"""
        text = f"""Support Ticket Created

Your support ticket has been submitted successfully.

Ticket #: {ticket_id}
Subject: {subject}

Our team will review your request and respond as soon as possible.

View your ticket: {ticket_url}

---
Community Resilience Platform
"""
        return self._send(to, email_subject, html, text)

    def send_admin_notification(
        self,
        notification_type: str,
        title: str,
        details: str,
        action_url: Optional[str] = None,
    ) -> bool:
        """
        Send notification email to admin.

        Args:
            notification_type: Type of notification (e.g., 'new_ticket', 'contact')
            title: Notification title
            details: Notification details
            action_url: Optional URL for action button

        Returns:
            True if sent successfully
        """
        if not self.admin_email:
            logger.warning("email.admin_notification.no_admin_email")
            return False

        subject = f"[{notification_type.upper()}] {title}"
        action_button = ""
        if action_url:
            action_button = f"""
    <p style="margin: 32px 0;">
        <a href="{action_url}"
           style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
            View Details
        </a>
    </p>
"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #2563eb; margin-bottom: 24px;">{title}</h1>
    <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; margin: 24px 0;">
        <pre style="margin: 0; white-space: pre-wrap; font-family: inherit;">{details}</pre>
    </div>
    {action_button}
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
    <p style="color: #999; font-size: 12px;">
        Community Resilience Platform - Admin Notification
    </p>
</body>
</html>
"""
        text = f"""{title}

{details}

{f"View details: {action_url}" if action_url else ""}

---
Community Resilience Platform - Admin Notification
"""
        return self._send(self.admin_email, subject, html, text)

    def send_contact_notification(
        self,
        name: str,
        email: str,
        subject: str,
        message: str,
        contact_id: int,
    ) -> bool:
        """
        Send notification to admin when a contact form is submitted.

        Args:
            name: Sender name
            email: Sender email
            subject: Contact subject
            message: Contact message
            contact_id: Contact submission ID

        Returns:
            True if sent successfully
        """
        details = f"""From: {name} <{email}>
Subject: {subject}

Message:
{message}
"""
        return self.send_admin_notification(
            notification_type="contact",
            title=f"New Contact: {subject}",
            details=details,
            action_url=f"{settings.frontend_url}/admin/contacts/{contact_id}" if settings.frontend_url else None,
        )

    def send_new_ticket_notification(
        self,
        ticket_id: int,
        user_email: str,
        subject: str,
        priority: str,
        description: str,
    ) -> bool:
        """
        Send notification to admin when a new support ticket is created.

        Args:
            ticket_id: Ticket ID
            user_email: User's email
            subject: Ticket subject
            priority: Ticket priority
            description: Ticket description

        Returns:
            True if sent successfully
        """
        details = f"""Ticket #{ticket_id}
From: {user_email}
Priority: {priority.upper()}
Subject: {subject}

Description:
{description}
"""
        return self.send_admin_notification(
            notification_type="new_ticket",
            title=f"New Ticket #{ticket_id}: {subject}",
            details=details,
            action_url=f"{settings.frontend_url}/admin/support/{ticket_id}" if settings.frontend_url else None,
        )


# Singleton instance
email_service = EmailService()
