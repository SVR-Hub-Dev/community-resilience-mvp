"""Authentication API router with OAuth, token, and user management endpoints."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config import settings
from db import get_db
from auth.models import User, APIKey, Session as UserSession, UserRole
from auth.schemas import (
    UserOut,
    UserUpdate,
    UserAdminUpdate,
    UserListOut,
    TokenPair,
    TokenRefresh,
    OAuthRedirect,
    APIKeyCreate,
    APIKeyOut,
    APIKeyCreated,
    APIKeyListOut,
    SessionOut,
    SessionListOut,
    AuthResponse,
    MessageResponse,
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TOTPLoginRequest,
    SetPasswordRequest,
)
from auth.service import auth_service
from auth.oauth import get_oauth_provider
from auth.dependencies import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Store OAuth states temporarily (in production, use Redis or database)
_oauth_states: dict[str, datetime] = {}


def _cleanup_old_states():
    """Remove OAuth states older than 10 minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired = [k for k, v in _oauth_states.items() if v < cutoff]
    for k in expired:
        del _oauth_states[k]


# ============================================================================
# OAuth Endpoints
# ============================================================================


@router.get("/login/{provider}")
async def oauth_login(provider: str):
    """
    Redirect to OAuth authorization URL for the specified provider.

    Supported providers: google, github
    """
    oauth_provider = get_oauth_provider(provider)
    if not oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    # Generate and store state for CSRF protection
    state = oauth_provider.generate_state()
    _oauth_states[state] = datetime.now(timezone.utc)
    _cleanup_old_states()

    authorization_url = oauth_provider.get_authorization_url(state)

    return RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle OAuth callback from provider.

    Exchanges code for tokens, creates/updates user, and redirects to frontend.
    """
    logger.info(
        f"OAuth callback received: provider={provider}, state={state}, code exists={bool(code)}"
    )

    # Verify state
    if state not in _oauth_states:
        logger.error(
            f"Invalid OAuth state: {state}. Current states: {list(_oauth_states.keys())}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )
    del _oauth_states[state]

    # Get provider
    oauth_provider = get_oauth_provider(provider)
    if not oauth_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    # Exchange code for token
    access_token = await oauth_provider.exchange_code(code)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code",
        )

    # Get user info
    user_info = await oauth_provider.get_user_info(access_token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from provider",
        )

    # Create or update user
    user = auth_service.get_or_create_oauth_user(
        db=db,
        email=user_info.email,
        name=user_info.name,
        oauth_provider=user_info.provider,
        oauth_id=user_info.id,
        avatar_url=user_info.avatar_url,
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Create session
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    jwt_token, refresh_token = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Redirect to frontend with tokens
    redirect_url = (
        f"{settings.frontend_url}/auth/callback"
        f"?access_token={jwt_token}"
        f"&refresh_token={refresh_token}"
        f"&expires_in={settings.jwt_access_token_expire_minutes * 60}"
    )

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


# ============================================================================
# Password Auth Endpoints
# ============================================================================


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new account with email and password."""
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    try:
        user = auth_service.register_user(
            db=db,
            email=payload.email,
            password=payload.password,
            name=payload.name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    # Create session
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    access_token, refresh_token = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return AuthResponse(
        user=UserOut.from_user(user),
        tokens=TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Login with email and password. Returns tokens or a TOTP challenge."""
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # If TOTP is enabled, return a challenge instead of tokens
    if user.totp_enabled and user.totp_secret:
        totp_token = auth_service.create_totp_pending_token(user.id)
        return LoginResponse(totp_required=True, totp_token=totp_token)

    # No TOTP - create session directly
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    access_token, refresh_token = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set access token as HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/login/totp", response_model=LoginResponse)
async def login_totp(
    payload: TOTPLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Complete login by verifying a TOTP code after password authentication."""
    user_id = auth_service.verify_totp_pending_token(payload.totp_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired TOTP token",
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP session",
        )

    if not auth_service.verify_totp_code(user.totp_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    # TOTP verified - create session
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    access_token, refresh_token = auth_service.create_user_session(
        db=db,
        user=user,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    # Set access token as HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


# ============================================================================
# Password Management Endpoints
# ============================================================================


@router.put("/password", response_model=MessageResponse)
async def set_password(
    payload: SetPasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or change the user's password. OAuth users can use this to add a password for offline login."""
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # If user already has a password, require the current one
    if user.password_hash:
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required",
            )
        if not auth_service.verify_password(
            payload.current_password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

    user.password_hash = auth_service.hash_password(payload.new_password)
    db.commit()

    logger.info(
        f"Password {'changed' if payload.current_password else 'set'} for user {user.email}"
    )
    return MessageResponse(message="Password has been set successfully")


# ============================================================================
# TOTP Management Endpoints
# ============================================================================


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a TOTP secret and QR code for the authenticated user.

    Call /totp/verify-setup with a valid code to activate TOTP.
    """
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled",
        )

    # Generate secret and store it (not yet enabled)
    secret = auth_service.generate_totp_secret()
    user.totp_secret = secret
    db.commit()

    provisioning_uri = auth_service.get_totp_provisioning_uri(secret, user.email)
    qr_svg = auth_service.generate_totp_qr_svg(provisioning_uri)

    return TOTPSetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_svg=qr_svg,
    )


@router.post("/totp/verify-setup", response_model=MessageResponse)
async def verify_totp_setup(
    payload: TOTPVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify a TOTP code to activate TOTP on the account."""
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is already enabled",
        )

    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call /totp/setup first",
        )

    if not auth_service.verify_totp_code(user.totp_secret, payload.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code. Please try again.",
        )

    user.totp_enabled = True
    db.commit()

    logger.info(f"TOTP enabled for user {user.email}")
    return MessageResponse(message="TOTP has been enabled")


@router.delete("/totp", response_model=MessageResponse)
async def disable_totp(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable TOTP for the authenticated user."""
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP is not enabled",
        )

    user.totp_secret = None
    user.totp_enabled = False
    db.commit()

    logger.info(f"TOTP disabled for user {user.email}")
    return MessageResponse(message="TOTP has been disabled")


# ============================================================================
# Token Endpoints
# ============================================================================


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    payload: TokenRefresh,
    db: Session = Depends(get_db),
):
    """Refresh an access token using a refresh token."""
    result = auth_service.refresh_access_token(db, payload.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, user = result

    return TokenPair(
        access_token=access_token,
        refresh_token=payload.refresh_token,  # Keep same refresh token
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: TokenRefresh,
    response: Response,
    db: Session = Depends(get_db),
):
    """Logout by invalidating the refresh token and clearing the cookie."""
    auth_service.logout(db, payload.refresh_token)
    response.delete_cookie("access_token", path="/")
    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout all sessions for the current user."""
    count = auth_service.logout_all(db, user.id)
    return MessageResponse(message=f"Logged out from {count} sessions")


# ============================================================================
# Current User Endpoints
# ============================================================================


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserOut.from_user(user)


@router.put("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile."""
    if payload.name is not None:
        user.name = payload.name
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url

    db.commit()
    db.refresh(user)
    return user


@router.get("/me/sessions", response_model=SessionListOut)
async def list_my_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active sessions for the current user."""
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        .order_by(UserSession.created_at.desc())
        .all()
    )
    return SessionListOut(sessions=sessions, total=len(sessions))


# ============================================================================
# API Key Endpoints
# ============================================================================


@router.get("/api-keys", response_model=APIKeyListOut)
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all API keys for the current user."""
    keys = (
        db.query(APIKey)
        .filter(APIKey.user_id == user.id)
        .order_by(APIKey.created_at.desc())
        .all()
    )
    return APIKeyListOut(api_keys=keys, total=len(keys))


@router.post(
    "/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    payload: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key.

    The full key is only returned once. Store it securely.
    """
    # Generate key
    full_key, key_hash, key_prefix = auth_service.generate_api_key()

    # Calculate expiration
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=payload.expires_in_days
        )

    # Create record
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=payload.name,
        description=payload.description,
        scopes=payload.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"API key created: {key_prefix} for user {user.email}")

    # Return with the full key (only time it's shown)
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        key=full_key,
    )


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke (delete) an API key."""
    api_key = (
        db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == user.id).first()
    )
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    db.delete(api_key)
    db.commit()

    logger.info(f"API key revoked: {api_key.key_prefix} for user {user.email}")
    return MessageResponse(message="API key revoked")


# ============================================================================
# Admin Endpoints - User Management
# ============================================================================


@router.get("/users", response_model=UserListOut)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    query = db.query(User)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if role:
        query = query.filter(User.role == role)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return UserListOut(users=[UserOut.from_user(user) for user in users], total=total)


@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get a specific user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserOut.from_user(user)


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent removing last admin
    if (
        payload.role
        and payload.role != UserRole.ADMIN
        and user.role == UserRole.ADMIN.value
    ):
        admin_count = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN.value, User.is_active == True)
            .count()
        )
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin",
            )

    if payload.name is not None:
        user.name = payload.name
    if payload.role is not None:
        user.role = payload.role.value
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)

    logger.info(f"User updated by admin: {user.email}")
    return UserOut.from_user(user)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    # Prevent deleting last admin
    if user.role == UserRole.ADMIN.value:
        admin_count = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN.value, User.is_active == True)
            .count()
        )
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin",
            )

    db.delete(user)
    db.commit()

    logger.info(f"User deleted by admin: {user.email}")
    return MessageResponse(message="User deleted")
