"""
Test session expiry and renewal.

Tests Phase 7 checklist item: "Test session expiry and renewal"
from docs/refactor/auth_implementation_plan.md
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from models.models import Base
from auth.models import User, Session as UserSession
from auth.service import auth_service
from db import get_db
from config import Settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    User.__table__.create(bind=engine, checkfirst=True)
    UserSession.__table__.create(bind=engine, checkfirst=True)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        UserSession.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    password = "TestPassword123!"
    password_hash = auth_service.hash_password(password)

    user = User(
        email="test@example.com",
        name="Test User",
        role="viewer",
        password_hash=password_hash,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user.plain_password = password
    return user


@pytest.fixture
def internal_secret():
    """Get the internal auth secret from settings."""
    settings = Settings()
    return settings.internal_auth_secret


class TestSessionExpiry:
    """Test session expiration detection."""

    def test_expired_session_rejected_by_time(self, client, test_user, db, internal_secret):
        """Test that sessions expired by time are rejected."""
        import uuid

        # Create an expired session directly in database
        expired_session = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            is_active=True,
        )
        db.add(expired_session)
        db.commit()
        db.refresh(expired_session)

        # Try to validate expired session
        response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(expired_session.session_token)},
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    def test_session_just_expired(self, client, test_user, db, internal_secret):
        """Test session that expired exactly now."""
        import uuid

        # Create session that expires right now
        session = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Small delay to ensure it's in the past
        time.sleep(0.1)

        response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session.session_token)},
        )

        assert response.status_code == 401

    def test_session_not_yet_expired(self, client, test_user, db, internal_secret):
        """Test session that hasn't expired yet."""
        import uuid

        # Create session that expires in the future
        session = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session.session_token)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id

    def test_session_with_various_ttl_values(self, client, test_user, internal_secret):
        """Test creating sessions with different TTL values."""
        ttl_values = [60, 3600, 86400, 604800]  # 1 min, 1 hour, 1 day, 1 week

        for ttl in ttl_values:
            response = client.post(
                "/internal/auth/session/create",
                headers={"X-Internal-Secret": internal_secret},
                json={
                    "user_id": test_user.id,
                    "ttl_seconds": ttl,
                },
            )

            assert response.status_code == 200
            session_id = response.json()["session_id"]

            # Validate it works
            validate_response = client.post(
                "/internal/auth/session/validate",
                headers={"X-Internal-Secret": internal_secret},
                json={"session_id": str(session_id)},
            )
            assert validate_response.status_code == 200


class TestRefreshTokens:
    """Test refresh token functionality."""

    def test_create_and_use_refresh_token(self, test_user, db):
        """Test creating and using a refresh token."""
        # Create session with refresh token
        access_token, refresh_token = auth_service.create_user_session(
            db, test_user, user_agent="TestAgent", ip_address="127.0.0.1"
        )

        # Verify access token
        payload = auth_service.verify_access_token(access_token)
        assert payload is not None
        assert payload["sub"] == str(test_user.id)

        # Use refresh token to get new access token
        result = auth_service.refresh_access_token(db, refresh_token)
        assert result is not None

        new_access_token, user = result
        assert user.id == test_user.id

        # Verify new access token
        new_payload = auth_service.verify_access_token(new_access_token)
        assert new_payload is not None
        assert new_payload["sub"] == str(test_user.id)

    def test_refresh_token_invalid(self, db):
        """Test that invalid refresh tokens are rejected."""
        result = auth_service.refresh_access_token(db, "invalid_token")
        assert result is None

    def test_refresh_token_expired(self, test_user, db):
        """Test that expired refresh tokens are rejected."""
        # Create a refresh token
        refresh_token = auth_service.create_refresh_token()
        token_hash = auth_service.hash_token(refresh_token)

        # Create an expired session
        expired_session = UserSession(
            user_id=test_user.id,
            refresh_token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(expired_session)
        db.commit()

        # Try to refresh with expired token
        result = auth_service.refresh_access_token(db, refresh_token)
        assert result is None

    def test_refresh_token_for_inactive_user(self, test_user, db):
        """Test that refresh tokens for inactive users are rejected."""
        # Create session
        access_token, refresh_token = auth_service.create_user_session(
            db, test_user
        )

        # Deactivate user
        test_user.is_active = False
        db.commit()

        # Try to refresh
        result = auth_service.refresh_access_token(db, refresh_token)
        assert result is None

    def test_refresh_token_multiple_times(self, test_user, db):
        """Test refreshing tokens multiple times."""
        # Create initial session
        _, refresh_token = auth_service.create_user_session(db, test_user)

        # Refresh multiple times
        for i in range(3):
            result = auth_service.refresh_access_token(db, refresh_token)
            assert result is not None
            new_access_token, user = result
            assert user.id == test_user.id

            # Verify the new token works
            payload = auth_service.verify_access_token(new_access_token)
            assert payload["sub"] == str(test_user.id)


class TestAccessTokenExpiry:
    """Test access token expiration."""

    def test_access_token_contains_expiry(self, test_user):
        """Test that access tokens contain expiration time."""
        token = auth_service.create_access_token(test_user.id, test_user.role)
        payload = auth_service.verify_access_token(token)

        assert payload is not None
        assert "exp" in payload
        assert "iat" in payload

    def test_access_token_expiry_time_correct(self, test_user):
        """Test that access token expiry time is correct."""
        token = auth_service.create_access_token(test_user.id, test_user.role)
        payload = auth_service.verify_access_token(token)

        # Calculate expected expiry
        expected_expiry = datetime.now(timezone.utc) + timedelta(
            minutes=auth_service.access_token_expire_minutes
        )

        # Allow 5 second variance for test execution time
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        time_diff = abs((exp_time - expected_expiry).total_seconds())
        assert time_diff < 5

    def test_expired_access_token_rejected(self, test_user):
        """Test that expired access tokens are rejected."""
        import jwt

        # Create an expired token manually
        expired_payload = {
            "sub": str(test_user.id),
            "role": test_user.role,
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        }
        expired_token = jwt.encode(
            expired_payload,
            auth_service.secret_key,
            algorithm=auth_service.algorithm,
        )

        # Try to verify expired token
        result = auth_service.verify_access_token(expired_token)
        assert result is None

    def test_access_token_type_validation(self, test_user):
        """Test that tokens with wrong type are rejected."""
        import jwt

        # Create a token with wrong type
        wrong_type_payload = {
            "sub": str(test_user.id),
            "role": test_user.role,
            "type": "wrong_type",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "iat": datetime.now(timezone.utc),
        }
        wrong_type_token = jwt.encode(
            wrong_type_payload,
            auth_service.secret_key,
            algorithm=auth_service.algorithm,
        )

        result = auth_service.verify_access_token(wrong_type_token)
        assert result is None


class TestSessionCleanup:
    """Test session cleanup and maintenance."""

    def test_cleanup_expired_sessions(self, test_user, db):
        """Test cleaning up expired sessions."""
        import uuid

        # Create multiple sessions with different expiry times
        active_session = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        expired_session1 = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        expired_session2 = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        db.add_all([active_session, expired_session1, expired_session2])
        db.commit()

        # Clean up expired sessions
        cleaned = auth_service.cleanup_expired_sessions(db)
        assert cleaned == 2

        # Verify only active session remains
        remaining = db.query(UserSession).count()
        assert remaining == 1

        remaining_session = db.query(UserSession).first()
        assert remaining_session.id == active_session.id

    def test_cleanup_with_no_expired_sessions(self, test_user, db):
        """Test cleanup when there are no expired sessions."""
        import uuid

        # Create only active sessions
        for i in range(3):
            session = UserSession(
                user_id=test_user.id,
                session_token=uuid.uuid4().hex,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            db.add(session)
        db.commit()

        cleaned = auth_service.cleanup_expired_sessions(db)
        assert cleaned == 0

        # All sessions should remain
        assert db.query(UserSession).count() == 3

    def test_cleanup_empty_database(self, db):
        """Test cleanup with no sessions at all."""
        cleaned = auth_service.cleanup_expired_sessions(db)
        assert cleaned == 0


class TestSessionLogout:
    """Test session logout and invalidation."""

    def test_logout_invalidates_session(self, test_user, db):
        """Test that logout properly invalidates a session."""
        # Create session
        access_token, refresh_token = auth_service.create_user_session(db, test_user)

        # Verify session exists
        token_hash = auth_service.hash_token(refresh_token)
        session = (
            db.query(UserSession)
            .filter(UserSession.refresh_token_hash == token_hash)
            .first()
        )
        assert session is not None

        # Logout
        result = auth_service.logout(db, refresh_token)
        assert result is True

        # Verify session is gone
        session = (
            db.query(UserSession)
            .filter(UserSession.refresh_token_hash == token_hash)
            .first()
        )
        assert session is None

    def test_logout_with_invalid_token(self, db):
        """Test logout with invalid refresh token."""
        result = auth_service.logout(db, "invalid_token")
        assert result is False

    def test_logout_all_sessions(self, test_user, db):
        """Test logging out all sessions for a user."""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            _, refresh_token = auth_service.create_user_session(db, test_user)
            sessions.append(refresh_token)

        # Verify all sessions exist
        assert db.query(UserSession).filter(UserSession.user_id == test_user.id).count() == 3

        # Logout all
        count = auth_service.logout_all(db, test_user.id)
        assert count == 3

        # Verify all sessions are gone
        assert db.query(UserSession).filter(UserSession.user_id == test_user.id).count() == 0

    def test_refresh_after_logout_fails(self, test_user, db):
        """Test that refresh token cannot be used after logout."""
        # Create session
        access_token, refresh_token = auth_service.create_user_session(db, test_user)

        # Verify refresh works
        result = auth_service.refresh_access_token(db, refresh_token)
        assert result is not None

        # Logout
        auth_service.logout(db, refresh_token)

        # Try to refresh after logout
        result = auth_service.refresh_access_token(db, refresh_token)
        assert result is None


class TestSessionLifecycle:
    """Test complete session lifecycle scenarios."""

    def test_full_session_lifecycle(self, test_user, db, client, internal_secret):
        """Test complete session lifecycle: create -> use -> refresh -> logout."""
        # Step 1: Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": test_user.id,
                "ttl_seconds": 3600,
            },
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Step 2: Validate session works
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},
        )
        assert validate_response.status_code == 200

        # Step 3: Logout
        logout_response = client.post(
            "/internal/auth/session/delete",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},
        )
        assert logout_response.status_code == 200

        # Step 4: Verify session no longer works
        validate_after_logout = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},
        )
        assert validate_after_logout.status_code == 401

    def test_session_with_user_agent_tracking(self, test_user, db):
        """Test session creation with user agent tracking."""
        user_agent = "Mozilla/5.0 (Test Browser)"
        ip_address = "192.168.1.1"

        access_token, refresh_token = auth_service.create_user_session(
            db, test_user, user_agent=user_agent, ip_address=ip_address
        )

        # Verify session has tracking info
        token_hash = auth_service.hash_token(refresh_token)
        session = (
            db.query(UserSession)
            .filter(UserSession.refresh_token_hash == token_hash)
            .first()
        )

        assert session.user_agent == user_agent
        assert session.ip_address == ip_address

    def test_multiple_concurrent_sessions(self, test_user, db, client, internal_secret):
        """Test that user can have multiple concurrent sessions."""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            response = client.post(
                "/internal/auth/session/create",
                headers={"X-Internal-Secret": internal_secret},
                json={
                    "user_id": test_user.id,
                    "ttl_seconds": 3600,
                },
            )
            assert response.status_code == 200
            session_ids.append(response.json()["session_id"])

        # Verify all sessions work
        for session_id in session_ids:
            validate_response = client.post(
                "/internal/auth/session/validate",
                headers={"X-Internal-Secret": internal_secret},
                json={"session_id": str(session_id)},
            )
            assert validate_response.status_code == 200

        # Logout one session
        logout_response = client.post(
            "/internal/auth/session/delete",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_ids[0])},
        )
        assert logout_response.status_code == 200

        # Verify first session is gone
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_ids[0])},
        )
        assert validate_response.status_code == 401

        # Verify other sessions still work
        for session_id in session_ids[1:]:
            validate_response = client.post(
                "/internal/auth/session/validate",
                headers={"X-Internal-Secret": internal_secret},
                json={"session_id": str(session_id)},
            )
            assert validate_response.status_code == 200
