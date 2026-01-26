"""Authentication service - JWT, hashing, and verification logic."""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import settings
from auth.models import User, APIKey, Session as UserSession

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication operations."""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days
        self.api_key_prefix = settings.api_key_prefix

    # ========================================================================
    # JWT Token Operations
    # ========================================================================

    def create_access_token(self, user_id: int, role: str) -> str:
        """Create a JWT access token."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self) -> str:
        """Create a cryptographically secure refresh token."""
        return secrets.token_urlsafe(32)

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT access token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "access":
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid access token: {e}")
            return None

    # ========================================================================
    # Hash Operations
    # ========================================================================

    def hash_token(self, token: str) -> str:
        """Hash a token using SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()

    # ========================================================================
    # API Key Operations
    # ========================================================================

    def generate_api_key(self) -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            tuple: (full_key, key_hash, key_prefix)
        """
        # Generate random key
        random_part = secrets.token_urlsafe(24)
        full_key = f"{self.api_key_prefix}{random_part}"

        # Create hash for storage
        key_hash = self.hash_token(full_key)

        # Create prefix for identification
        key_prefix = full_key[:12]

        return full_key, key_hash, key_prefix

    def verify_api_key(self, db: Session, api_key: str) -> Optional[User]:
        """
        Verify an API key and return the associated user.

        Also updates last_used_at timestamp.
        """
        # Check if it looks like an API key
        if not api_key.startswith(self.api_key_prefix):
            return None

        # Hash the key and look it up
        key_hash = self.hash_token(api_key)

        api_key_record = (
            db.query(APIKey)
            .filter(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
            .first()
        )

        if not api_key_record:
            return None

        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.now(timezone.utc):
            logger.debug(f"API key expired: {api_key_record.key_prefix}")
            return None

        # Update last_used_at
        api_key_record.last_used_at = datetime.now(timezone.utc)
        db.commit()

        # Get the user
        user = db.query(User).filter(User.id == api_key_record.user_id, User.is_active == True).first()
        if not user:
            return None

        logger.info(f"API key authenticated: {api_key_record.key_prefix} for user {user.email}")
        return user

    # ========================================================================
    # Session Operations
    # ========================================================================

    def create_user_session(
        self,
        db: Session,
        user: User,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Create access and refresh tokens for a user session.

        Returns:
            tuple: (access_token, refresh_token)
        """
        # Create tokens
        access_token = self.create_access_token(user.id, user.role)
        refresh_token = self.create_refresh_token()

        # Store session
        session = UserSession(
            user_id=user.id,
            refresh_token_hash=self.hash_token(refresh_token),
            user_agent=user_agent[:500] if user_agent else None,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days),
        )
        db.add(session)
        db.commit()

        logger.info(f"Session created for user {user.email}")
        return access_token, refresh_token

    def refresh_access_token(self, db: Session, refresh_token: str) -> Optional[tuple[str, User]]:
        """
        Refresh an access token using a refresh token.

        Returns:
            tuple: (new_access_token, user) or None if invalid
        """
        # Find the session
        token_hash = self.hash_token(refresh_token)
        session = (
            db.query(UserSession)
            .filter(
                UserSession.refresh_token_hash == token_hash,
                UserSession.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

        if not session:
            logger.debug("Invalid or expired refresh token")
            return None

        # Get the user
        user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
        if not user:
            logger.debug("User not found or inactive for refresh token")
            return None

        # Create new access token
        access_token = self.create_access_token(user.id, user.role)

        logger.info(f"Access token refreshed for user {user.email}")
        return access_token, user

    def logout(self, db: Session, refresh_token: str) -> bool:
        """
        Logout by invalidating a refresh token.

        Returns:
            bool: True if session was found and deleted
        """
        token_hash = self.hash_token(refresh_token)
        result = db.query(UserSession).filter(UserSession.refresh_token_hash == token_hash).delete()
        db.commit()

        if result > 0:
            logger.info("Session invalidated")
            return True
        return False

    def logout_all(self, db: Session, user_id: int) -> int:
        """
        Logout all sessions for a user.

        Returns:
            int: Number of sessions invalidated
        """
        result = db.query(UserSession).filter(UserSession.user_id == user_id).delete()
        db.commit()
        logger.info(f"All sessions invalidated for user {user_id}: {result} sessions")
        return result

    def cleanup_expired_sessions(self, db: Session) -> int:
        """
        Remove expired sessions from the database.

        Returns:
            int: Number of sessions removed
        """
        result = (
            db.query(UserSession)
            .filter(UserSession.expires_at < datetime.now(timezone.utc))
            .delete()
        )
        db.commit()
        if result > 0:
            logger.info(f"Cleaned up {result} expired sessions")
        return result

    # ========================================================================
    # User Operations
    # ========================================================================

    def get_or_create_oauth_user(
        self,
        db: Session,
        email: str,
        name: str,
        oauth_provider: str,
        oauth_id: str,
        avatar_url: Optional[str] = None,
    ) -> User:
        """
        Get existing user by OAuth ID or create a new one.

        If user exists with same email but different OAuth, link them.
        """
        # Try to find by OAuth credentials first
        user = (
            db.query(User)
            .filter(
                User.oauth_provider == oauth_provider,
                User.oauth_id == oauth_id,
            )
            .first()
        )

        if user:
            # Update user info if changed
            if user.name != name or user.avatar_url != avatar_url:
                user.name = name
                user.avatar_url = avatar_url
                db.commit()
            logger.info(f"OAuth login: existing user {user.email}")
            return user

        # Try to find by email (linking accounts)
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Link OAuth to existing account
            user.oauth_provider = oauth_provider
            user.oauth_id = oauth_id
            user.avatar_url = avatar_url or user.avatar_url
            db.commit()
            logger.info(f"OAuth linked to existing user {user.email}")
            return user

        # Create new user
        user = User(
            email=email,
            name=name,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            avatar_url=avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"New OAuth user created: {user.email}")
        return user


# Singleton instance
auth_service = AuthService()
