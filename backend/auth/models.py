"""SQLAlchemy ORM models for authentication."""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    ARRAY,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from models.models import Base


class UserRole(str, PyEnum):
    """User role enumeration for RBAC."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    """
    User account model.

    Supports OAuth login, email/password login, and API key authentication.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.VIEWER.value)
    password_hash = Column(String(255))  # NULL for OAuth-only users
    oauth_provider = Column(String(50))  # 'google', 'github', 'microsoft', or NULL
    oauth_id = Column(String(255))  # Provider's unique user ID
    avatar_url = Column(String(500))
    totp_secret = Column(String(32))  # Base32-encoded TOTP secret
    totp_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class APIKey(Base):
    """
    API Key for service-to-service authentication.

    Keys are stored as SHA-256 hashes. The plaintext key is only
    shown once during creation.
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(
        String(12), nullable=False
    )  # First chars for identification (e.g., "cr_abc123")
    name = Column(String(100), nullable=False)
    description = Column(Text)
    scopes = Column(ARRAY(String))  # Optional permission scopes
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"


class Session(Base):
    """
    User session for JWT refresh tokens.

    Tracks active sessions and enables logout functionality.
    """

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Legacy refresh token column retained for compatibility, now nullable so
    # new session creation paths don't need to provide it.
    refresh_token_hash = Column(String(64), unique=True, nullable=True, index=True)

    # New session_token used by SvelteKit as the browser session identifier.
    session_token = Column(String(128), unique=True, nullable=True, index=True)

    user_agent = Column(String(500))
    ip_address = Column(String(45))  # Supports IPv6

    # Expiration and lifecycle fields
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id})>"


class PasswordResetToken(Base):
    """
    Password reset token for secure password recovery.

    Tokens are one-time use and expire after a set period.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"
