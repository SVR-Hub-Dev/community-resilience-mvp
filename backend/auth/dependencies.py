"""FastAPI authentication dependencies for protecting endpoints."""

import logging
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db import get_db
from auth.models import User, UserRole
from auth.service import auth_service

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme (supports both JWT and API keys)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    request: Request = None,
) -> User:
    """
    Get the current authenticated user from JWT or API key.

    Raises HTTPException 401 if not authenticated.
    """
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Try to get token from cookie
        if request is not None:
            token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Try JWT first
    payload = auth_service.verify_access_token(token)
    if payload:
        user_id = int(payload["sub"])
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if user:
            return user
        logger.warning(f"JWT valid but user not found or inactive: {user_id}")

    # Try API key
    user = auth_service.verify_api_key(db, token)
    if user:
        return user

    # Neither worked
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(allowed_roles: List[str]):
    """
    Dependency factory for role-based access control.

    Usage:
        @app.get("/admin")
        def admin_endpoint(user: User = Depends(require_role(["admin"]))):
            ...
    """

    async def role_checker(user: User = Depends(get_current_user)) -> User:
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


# Convenience dependencies for common role combinations
require_admin = require_role([UserRole.ADMIN.value])
require_editor = require_role([UserRole.ADMIN.value, UserRole.EDITOR.value])
require_viewer = require_role(
    [UserRole.ADMIN.value, UserRole.EDITOR.value, UserRole.VIEWER.value]
)
