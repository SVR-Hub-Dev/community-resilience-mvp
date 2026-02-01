"""Authentication API router with OAuth, token, and user management endpoints."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, cast

from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from config import Settings
from db import get_db
from auth.models import User, Session as SessionModel
from auth.service import auth_service

logger = logging.getLogger("community_resilience.auth.router")
router = APIRouter(prefix="/internal/auth", tags=["internal.auth"])

settings = Settings()


def _require_internal_secret(request: Request):
    if not settings.internal_auth_secret:
        logger.warning("internal.secret.not_set")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal auth not configured",
        )
    secret = request.headers.get("x-internal-secret") or request.headers.get(
        "X-Internal-Secret"
    )
    if not secret or secret != settings.internal_auth_secret:
        logger.warning(
            "internal.auth.unauthorized",
            extra={"remote": getattr(request.client, "host", None)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


class SessionValidateIn(BaseModel):
    session_id: str


class SessionCreateIn(BaseModel):
    user_id: int
    ttl_seconds: Optional[int] = 60 * 60 * 24  # default 24h


class UserOut(BaseModel):
    id: int
    email: Optional[str] = None
    role: Optional[str] = None


@router.post("/session/validate", response_model=UserOut)
def internal_validate_session(
    payload: SessionValidateIn,
    request: Request,
    _=Depends(_require_internal_secret),
    db: DBSession = Depends(get_db),
):
    """
    Validate a session_id and return minimal user info.
    Used by SvelteKit hooks.server.ts to resolve session -> user.
    """
    session_id = payload.session_id
    logger.debug(
        "internal.session.validate.attempt", extra={"session_id_mask": session_id[:16]}
    )

    # Try lookup by primary key/id
    session = (
        db.query(SessionModel).filter(getattr(SessionModel, "id") == session_id).first()
    )
    # Fallback: lookup by token field if present
    if not session and hasattr(SessionModel, "session_token"):
        session = (
            db.query(SessionModel)
            .filter(getattr(SessionModel, "session_token") == session_id)
            .first()
        )

    if not session:
        logger.info(
            "internal.session.validate.not_found",
            extra={"session_id_mask": session_id[:16]},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        )

    # Optional: check is_active / expires_at if those fields exist
    if getattr(session, "is_active", True) is False:
        logger.info(
            "internal.session.validate.inactive",
            extra={"session_id_mask": session_id[:16]},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session inactive"
        )

    expires_at = getattr(session, "expires_at", None)
    if expires_at and isinstance(expires_at, datetime):
        # Handle both timezone-aware and timezone-naive datetimes
        now = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            # expires_at is naive, convert now to naive for comparison
            now = now.replace(tzinfo=None)
        if expires_at < now:
            logger.info(
                "internal.session.validate.expired",
                extra={"session_id_mask": session_id[:16]},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
            )

    # Resolve user
    user = None
    if hasattr(session, "user_id"):
        user = (
            db.query(User)
            .filter(User.id == session.user_id, User.is_active == True)
            .first()
        )
    elif hasattr(session, "user"):
        # relationship
        user = session.user if getattr(session.user, "is_active", True) else None

    if not user:
        logger.info(
            "internal.session.validate.user_not_found",
            extra={"session_id_mask": session_id[:16]},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    logger.info("internal.session.validate.success", extra={"user_id": user.id})
    return UserOut(
        id=cast(int, user.id),
        email=getattr(user, "email", None),
        role=getattr(user, "role", None),
    )


@router.post("/session/create")
def internal_create_session(
    payload: SessionCreateIn,
    request: Request,
    _=Depends(_require_internal_secret),
    db: DBSession = Depends(get_db),
):
    """
    Create a session record for a given user_id and return the created session identifier.
    Intended for SvelteKit to call when it is the session authority.
    """
    user_id = payload.user_id
    ttl = payload.ttl_seconds or (60 * 60 * 24)
    logger.info(
        "internal.session.create.attempt",
        extra={"user_id": user_id, "remote": getattr(request.client, "host", None)},
    )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        logger.warning(
            "internal.session.create.user_not_found", extra={"user_id": user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found or inactive"
        )

    token = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    # Construct SessionModel instance with best-effort fields
    session_kwargs = {}
    if hasattr(SessionModel, "user_id"):
        session_kwargs["user_id"] = user_id
    if hasattr(SessionModel, "session_token"):
        session_kwargs["session_token"] = token
    if hasattr(SessionModel, "expires_at"):
        session_kwargs["expires_at"] = expires_at
    if hasattr(SessionModel, "is_active"):
        session_kwargs["is_active"] = True
    if hasattr(SessionModel, "created_at"):
        session_kwargs["created_at"] = datetime.now(timezone.utc)

    session = SessionModel(**session_kwargs)
    try:
        db.add(session)
        db.commit()
        db.refresh(session)
        session_identifier = (
            getattr(session, "id", None)
            or getattr(session, "session_token", None)
            or token
        )
        logger.info(
            "internal.session.create.success",
            extra={
                "user_id": user_id,
                "session_identifier_mask": str(session_identifier)[:16],
            },
        )
        return {"session_id": session_identifier}
    except Exception as e:
        db.rollback()
        logger.error(
            "internal.session.create.failed",
            extra={"error": str(e), "user_id": user_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


# =============================================================================
# Password & TOTP Verification Endpoints
# =============================================================================


class PasswordVerifyIn(BaseModel):
    email: str
    password: str


class PasswordVerifyOut(BaseModel):
    success: bool
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
    totp_required: bool = False
    totp_token: Optional[str] = None


@router.post("/verify-password", response_model=PasswordVerifyOut)
def internal_verify_password(
    payload: PasswordVerifyIn,
    request: Request,
    _=Depends(_require_internal_secret),
    db: DBSession = Depends(get_db),
):
    """
    Verify email/password credentials.
    Returns user info if valid, or TOTP challenge if 2FA is enabled.
    """
    logger.debug(
        "internal.verify_password.attempt",
        extra={"email": payload.email, "remote": getattr(request.client, "host", None)},
    )

    user = auth_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        logger.info("internal.verify_password.failed", extra={"email": payload.email})
        return PasswordVerifyOut(success=False)

    # Check if TOTP is enabled
    if getattr(user, "totp_enabled", False):
        totp_token = auth_service.create_totp_pending_token(cast(int, user.id))
        logger.info(
            "internal.verify_password.totp_required", extra={"user_id": user.id}
        )
        return PasswordVerifyOut(
            success=True,
            totp_required=True,
            totp_token=totp_token,
        )

    logger.info("internal.verify_password.success", extra={"user_id": user.id})
    return PasswordVerifyOut(
        success=True,
        user_id=cast(int, user.id),
        email=getattr(user, "email", None),
        role=getattr(user, "role", None),
    )


class TotpVerifyIn(BaseModel):
    totp_token: str
    code: str


@router.post("/verify-totp", response_model=PasswordVerifyOut)
def internal_verify_totp(
    payload: TotpVerifyIn,
    request: Request,
    _=Depends(_require_internal_secret),
    db: DBSession = Depends(get_db),
):
    """
    Verify TOTP code after password verification.
    Returns user info if valid.
    """
    logger.debug(
        "internal.verify_totp.attempt",
        extra={"remote": getattr(request.client, "host", None)},
    )

    # Verify the pending token
    user_id = auth_service.verify_totp_pending_token(payload.totp_token)
    if not user_id:
        logger.info("internal.verify_totp.invalid_token")
        return PasswordVerifyOut(success=False)

    # Get user and verify TOTP code
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        logger.info("internal.verify_totp.user_not_found", extra={"user_id": user_id})
        return PasswordVerifyOut(success=False)

    totp_secret = getattr(user, "totp_secret", None)
    if not totp_secret:
        logger.info("internal.verify_totp.no_secret", extra={"user_id": user_id})
        return PasswordVerifyOut(success=False)

    if not auth_service.verify_totp_code(totp_secret, payload.code):
        logger.info("internal.verify_totp.invalid_code", extra={"user_id": user_id})
        return PasswordVerifyOut(success=False)

    logger.info("internal.verify_totp.success", extra={"user_id": user_id})
    return PasswordVerifyOut(
        success=True,
        user_id=cast(int, user.id),
        email=getattr(user, "email", None),
        role=getattr(user, "role", None),
    )


class SessionDeleteIn(BaseModel):
    session_id: str


@router.post("/session/delete")
def internal_delete_session(
    payload: SessionDeleteIn,
    request: Request,
    _=Depends(_require_internal_secret),
    db: DBSession = Depends(get_db),
):
    """
    Delete a session by session_id.
    Used for logout.
    """
    session_id = payload.session_id
    logger.debug(
        "internal.session.delete.attempt",
        extra={
            "session_id_mask": session_id[:16] if len(session_id) >= 16 else session_id
        },
    )

    # Try to find and delete by session_token
    deleted = 0
    if hasattr(SessionModel, "session_token"):
        deleted = (
            db.query(SessionModel)
            .filter(getattr(SessionModel, "session_token") == session_id)
            .delete()
        )

    # Fallback: try by id
    if deleted == 0:
        try:
            deleted = (
                db.query(SessionModel)
                .filter(getattr(SessionModel, "id") == session_id)
                .delete()
            )
        except Exception:
            pass  # id might not be string-compatible

    db.commit()

    if deleted > 0:
        logger.info(
            "internal.session.delete.success",
            extra={
                "session_id_mask": (
                    session_id[:16] if len(session_id) >= 16 else session_id
                )
            },
        )
        return {"deleted": True}

    logger.info(
        "internal.session.delete.not_found",
        extra={
            "session_id_mask": session_id[:16] if len(session_id) >= 16 else session_id
        },
    )
    return {"deleted": False}


# =============================================================================
# OAuth User Management
# =============================================================================


class OAuthUserIn(BaseModel):
    provider: str  # 'google', 'github', 'microsoft'
    provider_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None


class OAuthUserOut(BaseModel):
    user_id: int
    email: str
    role: str
    created: bool  # True if new user was created


@router.post("/oauth/find-or-create", response_model=OAuthUserOut)
def internal_oauth_find_or_create(
    payload: OAuthUserIn,
    request: Request,
    _=Depends(_require_internal_secret),
    db: DBSession = Depends(get_db),
):
    """
    Find or create a user from OAuth identity.
    1. Find by (provider, provider_id)
    2. If not found, find by email and link OAuth identity
    3. If not found, create new user
    """
    logger.info(
        "internal.oauth.find_or_create.attempt",
        extra={
            "provider": payload.provider,
            "email": payload.email,
            "remote": getattr(request.client, "host", None),
        },
    )

    # 1. Try to find by OAuth identity
    user = (
        db.query(User)
        .filter(
            User.oauth_provider == payload.provider,
            User.oauth_id == payload.provider_id,
            User.is_active == True,
        )
        .first()
    )

    if user:
        logger.info(
            "internal.oauth.find_or_create.found_by_oauth",
            extra={"user_id": user.id, "provider": payload.provider},
        )
        return OAuthUserOut(
            user_id=cast(int, user.id),
            email=cast(str, user.email),
            role=cast(str, user.role),
            created=False,
        )

    # 2. Try to find by email and link OAuth
    user = (
        db.query(User)
        .filter(User.email == payload.email, User.is_active == True)
        .first()
    )

    if user:
        # Link OAuth identity to existing user
        setattr(user, "oauth_provider", payload.provider)
        setattr(user, "oauth_id", payload.provider_id)
        if payload.avatar_url and not getattr(user, "avatar_url", None):
            setattr(user, "avatar_url", payload.avatar_url)
        db.commit()
        logger.info(
            "internal.oauth.find_or_create.linked",
            extra={"user_id": user.id, "provider": payload.provider},
        )
        return OAuthUserOut(
            user_id=cast(int, user.id),
            email=cast(str, user.email),
            role=cast(str, user.role),
            created=False,
        )

    # 3. Create new user
    user = User(
        email=payload.email,
        name=payload.name,
        oauth_provider=payload.provider,
        oauth_id=payload.provider_id,
        avatar_url=payload.avatar_url,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(
        "internal.oauth.find_or_create.created",
        extra={"user_id": user.id, "provider": payload.provider},
    )
    return OAuthUserOut(
        user_id=cast(int, user.id),
        email=cast(str, user.email),
        role=cast(str, user.role),
        created=True,
    )
