"""Pydantic schemas for authentication requests and responses."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr

from auth.models import UserRole


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a user (internal use)."""

    role: UserRole = UserRole.VIEWER
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None
    avatar_url: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserAdminUpdate(BaseModel):
    """Schema for admin updating any user."""

    name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    """Schema for user response."""

    id: int
    email: str
    name: str
    role: str
    oauth_provider: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListOut(BaseModel):
    """Schema for paginated user list."""

    users: List[UserOut]
    total: int


# ============================================================================
# Token Schemas
# ============================================================================

class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiry in seconds


class TokenRefresh(BaseModel):
    """Request to refresh access token."""

    refresh_token: str


class OAuthRedirect(BaseModel):
    """OAuth authorization URL response."""

    authorization_url: str
    state: str


# ============================================================================
# API Key Schemas
# ============================================================================

class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    expires_in_days: Optional[int] = None  # None = never expires


class APIKeyOut(BaseModel):
    """Schema for API key response (without the actual key)."""

    id: int
    name: str
    description: Optional[str] = None
    key_prefix: str
    scopes: Optional[List[str]] = None
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreated(APIKeyOut):
    """Schema for newly created API key (includes the actual key, shown only once)."""

    key: str  # Full API key - only shown on creation


class APIKeyListOut(BaseModel):
    """Schema for list of API keys."""

    api_keys: List[APIKeyOut]
    total: int


# ============================================================================
# Session Schemas
# ============================================================================

class SessionOut(BaseModel):
    """Schema for session info."""

    id: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SessionListOut(BaseModel):
    """Schema for list of sessions."""

    sessions: List[SessionOut]
    total: int


# ============================================================================
# Auth Response Schemas
# ============================================================================

class AuthResponse(BaseModel):
    """Complete auth response with user and tokens."""

    user: UserOut
    tokens: TokenPair


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
