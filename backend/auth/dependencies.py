"""FastAPI authentication dependencies for protecting endpoints."""

import logging
from typing import List, Optional

from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db import get_db
from auth.models import User, UserRole
from auth.service import auth_service
from auth.derived import verify_derived_token_raw

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme (supports both JWT and API keys)
bearer_scheme = HTTPBearer(auto_error=False)


def get_request(request: Request):
    return request


def _mask_token(t: Optional[str]) -> str:
    if not t:
        return ""
    t = str(t)
    if len(t) <= 16:
        return t[:4] + "...(masked)"
    return t[:8] + "...(masked)..." + t[-8:]


async def get_current_user_from_derived_jwt(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current user from a derived JWT token minted by SvelteKit.

    This dependency ONLY accepts derived JWTs - it does NOT accept API keys.
    Use this for all browser-facing routes to ensure API keys cannot be used
    from browser contexts.

    Raises HTTPException 401 if not authenticated or if API key is used.
    """
    remote = None
    try:
        remote = request.client.host if request and request.client else None
    except Exception:
        remote = None

    token = None
    if credentials:
        token = credentials.credentials

    logger.info(
        "auth.derived_only.attempt",
        extra={"remote": remote, "token_mask": _mask_token(token)},
    )

    if not token:
        logger.debug("auth.derived_only.missing_token", extra={"remote": remote})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reject if this looks like an API key (has the API key prefix)
    if token.startswith(auth_service.api_key_prefix):
        logger.warning(
            "auth.derived_only.api_key_rejected",
            extra={"remote": remote, "token_mask": _mask_token(token)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API keys are not accepted for this endpoint",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify derived JWT
    try:
        payload = verify_derived_token_raw(token)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(
            "auth.derived_only.verify_failed",
            extra={"error": str(e), "remote": remote, "token_mask": _mask_token(token)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid derived token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from sub claim
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError) as e:
        logger.warning(
            "auth.derived_only.invalid_sub",
            extra={"error": str(e), "payload": payload},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

    if not user:
        logger.warning(
            "auth.derived_only.user_not_found",
            extra={"user_id": user_id, "remote": remote},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(
        "auth.derived_only.success",
        extra={"user_id": user_id, "role": payload.get("role"), "remote": remote},
    )
    return user


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT or API key.

    IMPORTANT: This dependency accepts API keys and should only be used for
    endpoints intended for programmatic/CLI access. For browser-facing routes,
    use get_current_user_from_derived_jwt instead.

    Supports three authentication methods (in order of precedence):
    1. Authorization header with Bearer token (JWT or API key)
    2. Cookie with access_token (for browser-based OAuth flow)
    3. API key passed as Bearer token

    Raises HTTPException 401 if not authenticated.
    """
    token = None
    source = "none"
    remote = None
    try:
        remote = request.client.host if request and request.client else None
    except Exception:
        remote = None

    # Method 1: Try Authorization header first (Bearer token)
    if credentials:
        token = credentials.credentials
        source = "authorization_header"
    # Method 2: Fall back to cookie (for OAuth/browser flow)
    else:
        token = request.cookies.get("access_token")
        if token:
            source = "cookie"

    logger.info(
        "auth.attempt",
        extra={
            "source": source,
            "remote": remote,
            "token_mask": _mask_token(token),
        },
    )

    if not token:
        logger.debug("auth.missing_token", extra={"remote": remote})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Try JWT first (most common for OAuth users)
    try:
        payload = auth_service.verify_access_token(token)
    except Exception as e:
        logger.warning(
            "auth.verify_access_token.failed",
            extra={"error": str(e), "token_mask": _mask_token(token)},
        )
        payload = None

    if payload:
        try:
            user_id = int(payload["sub"])
        except Exception:
            logger.warning(
                "auth.jwt.invalid_sub",
                extra={"payload": payload, "token_mask": _mask_token(token)},
            )
            user_id = None

        if user_id is not None:
            user = (
                db.query(User)
                .filter(User.id == user_id, User.is_active == True)
                .first()
            )
            if user:
                logger.info(
                    "auth.jwt.success",
                    extra={
                        "user_id": user_id,
                        "remote": remote,
                        "token_mask": _mask_token(token),
                    },
                )
                return user
            logger.warning(
                "auth.jwt.user_not_found_or_inactive",
                extra={"user_id": user_id, "remote": remote},
            )

    # Try API key (for programmatic access)
    try:
        user = auth_service.verify_api_key(db, token)
    except Exception as e:
        logger.warning(
            "auth.verify_api_key.failed",
            extra={"error": str(e), "token_mask": _mask_token(token)},
        )
        user = None

    if user:
        logger.info(
            "auth.api_key.success",
            extra={"user_id": getattr(user, "id", None), "remote": remote},
        )
        return user

    # Neither worked
    logger.warning(
        "auth.failed",
        extra={"remote": remote, "token_mask": _mask_token(token), "source": source},
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work differently for authenticated vs anonymous users.

    FIXED: Now properly checks cookies in addition to Authorization header.
    """
    # If no credentials and no cookie, return None immediately
    if not credentials and not request.cookies.get("access_token"):
        return None

    try:
        return await get_current_user(credentials, db, request)
    except HTTPException:
        return None


def require_role(allowed_roles: List[str], allow_api_keys: bool = False):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: List of roles that are allowed to access the endpoint.
        allow_api_keys: If False (default), only derived JWTs from SvelteKit are
                        accepted. If True, API keys are also accepted (for CLI/automation).

    Usage:
        @app.get("/admin")
        def admin_endpoint(user: User = Depends(require_role(["admin"]))):
            ...

        @app.get("/cli/export")
        def cli_export(user: User = Depends(require_role(["admin"], allow_api_keys=True))):
            ...
    """
    # Choose the appropriate user dependency based on whether API keys are allowed
    user_dependency = (
        get_current_user if allow_api_keys else get_current_user_from_derived_jwt
    )

    async def role_checker(user: User = Depends(user_dependency)) -> User:
        if user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {user.email} (role: {user.role}), required: {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}",
            )
        return user

    return role_checker


# =============================================================================
# Browser-only role dependencies (derived JWT only, NO API keys)
# Use these for all browser-facing routes
# =============================================================================
require_admin = require_role([UserRole.ADMIN.value])
require_editor = require_role([UserRole.ADMIN.value, UserRole.EDITOR.value])
require_viewer = require_role(
    [UserRole.ADMIN.value, UserRole.EDITOR.value, UserRole.VIEWER.value]
)

# =============================================================================
# CLI/Automation role dependencies (accepts API keys)
# Use these for routes intended for programmatic access
# =============================================================================
require_admin_or_api_key = require_role([UserRole.ADMIN.value], allow_api_keys=True)
require_editor_or_api_key = require_role(
    [UserRole.ADMIN.value, UserRole.EDITOR.value], allow_api_keys=True
)
require_viewer_or_api_key = require_role(
    [UserRole.ADMIN.value, UserRole.EDITOR.value, UserRole.VIEWER.value],
    allow_api_keys=True,
)
