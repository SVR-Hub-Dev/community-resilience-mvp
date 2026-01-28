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
    has_password: bool = False
    totp_enabled: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_user(cls, user) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            oauth_provider=user.oauth_provider,
            avatar_url=user.avatar_url,
            has_password=user.password_hash is not None,
            totp_enabled=user.totp_enabled or False,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


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


# ============================================================================
# Password Auth Schemas
# ============================================================================

class RegisterRequest(BaseModel):
    """Schema for registering with email/password."""

    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    """Schema for logging in with email/password."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response - either tokens or TOTP challenge."""

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    totp_required: bool = False
    totp_token: Optional[str] = None


# ============================================================================
# TOTP Schemas
# ============================================================================

class SetPasswordRequest(BaseModel):
    """Schema for setting or changing password."""

    new_password: str
    current_password: Optional[str] = None  # Required if user already has a password


class TOTPSetupResponse(BaseModel):
    """Response with TOTP setup info (secret + QR code)."""

    secret: str
    provisioning_uri: str
    qr_svg: str


class TOTPVerifyRequest(BaseModel):
    """Request to verify a TOTP code."""

    code: str


class TOTPLoginRequest(BaseModel):
    """Request to complete login with TOTP."""

    totp_token: str
    code: str
