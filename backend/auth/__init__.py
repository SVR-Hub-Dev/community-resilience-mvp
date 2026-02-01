"""Authentication module for Community Resilience API."""

from auth.models import User, APIKey, Session, UserRole
from auth.dependencies import (
    get_current_user,
    get_current_user_from_derived_jwt,
    get_optional_user,
    require_role,
    # Browser-only dependencies (no API keys)
    require_admin,
    require_editor,
    require_viewer,
    # CLI/Automation dependencies (accepts API keys)
    require_admin_or_api_key,
    require_editor_or_api_key,
    require_viewer_or_api_key,
)

__all__ = [
    "User",
    "APIKey",
    "Session",
    "UserRole",
    "get_current_user",
    "get_current_user_from_derived_jwt",
    "get_optional_user",
    "require_role",
    # Browser-only dependencies (no API keys)
    "require_admin",
    "require_editor",
    "require_viewer",
    # CLI/Automation dependencies (accepts API keys)
    "require_admin_or_api_key",
    "require_editor_or_api_key",
    "require_viewer_or_api_key",
]
