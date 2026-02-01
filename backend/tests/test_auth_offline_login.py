"""
Test offline login (email/password + TOTP).

Tests Phase 7 checklist item: "Test offline login (email/password + TOTP)"
from docs/refactor/auth_implementation_plan.md
"""

import pytest
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
    # Only create auth-related tables needed for tests
    # Skip APIKey table as it uses PostgreSQL ARRAY type
    User.__table__.create(bind=engine, checkfirst=True)
    UserSession.__table__.create(bind=engine, checkfirst=True)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up auth tables
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
    """Create a test user with password authentication."""
    password = "TestPassword123!"
    password_hash = auth_service.hash_password(password)

    user = User(
        email="test@example.com",
        name="Test User",
        role="viewer",
        password_hash=password_hash,
        totp_enabled=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Return user and password for testing
    user.plain_password = password
    return user


@pytest.fixture
def test_user_with_totp(db):
    """Create a test user with TOTP enabled."""
    password = "TestPassword123!"
    password_hash = auth_service.hash_password(password)
    totp_secret = auth_service.generate_totp_secret()

    user = User(
        email="totp@example.com",
        name="TOTP User",
        role="viewer",
        password_hash=password_hash,
        totp_secret=totp_secret,
        totp_enabled=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Return user, password, and secret for testing
    user.plain_password = password
    user.plain_totp_secret = totp_secret
    return user


@pytest.fixture
def internal_secret():
    """Get the internal auth secret from settings."""
    settings = Settings()
    return settings.internal_auth_secret


class TestPasswordAuthentication:
    """Test basic email/password authentication without TOTP."""

    def test_verify_password_success(self, client, test_user, internal_secret):
        """Test successful password verification for user without TOTP."""
        response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user.email,
                "password": test_user.plain_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role
        assert data["totp_required"] is False
        assert data["totp_token"] is None

    def test_verify_password_wrong_password(self, client, test_user, internal_secret):
        """Test password verification with incorrect password."""
        response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user.email,
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["user_id"] is None

    def test_verify_password_nonexistent_user(self, client, internal_secret):
        """Test password verification for non-existent user."""
        response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_verify_password_inactive_user(self, client, test_user, db, internal_secret):
        """Test password verification for inactive user."""
        # Deactivate the user
        test_user.is_active = False
        db.commit()

        response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user.email,
                "password": test_user.plain_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_verify_password_missing_internal_secret(self, client, test_user):
        """Test that endpoint requires internal secret."""
        response = client.post(
            "/internal/auth/verify-password",
            json={
                "email": test_user.email,
                "password": test_user.plain_password,
            },
        )

        assert response.status_code == 401


class TestTOTPAuthentication:
    """Test TOTP (two-factor authentication) flow."""

    def test_verify_password_with_totp_enabled(
        self, client, test_user_with_totp, internal_secret
    ):
        """Test that password verification returns TOTP challenge when TOTP is enabled."""
        response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user_with_totp.email,
                "password": test_user_with_totp.plain_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["totp_required"] is True
        assert data["totp_token"] is not None
        assert data["user_id"] is None  # User info not returned until TOTP verified

    def test_verify_totp_success(self, client, test_user_with_totp, internal_secret):
        """Test successful TOTP verification."""
        # First, verify password to get TOTP token
        password_response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user_with_totp.email,
                "password": test_user_with_totp.plain_password,
            },
        )
        totp_token = password_response.json()["totp_token"]

        # Generate a valid TOTP code
        import pyotp

        totp = pyotp.TOTP(test_user_with_totp.plain_totp_secret)
        valid_code = totp.now()

        # Verify TOTP
        totp_response = client.post(
            "/internal/auth/verify-totp",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "totp_token": totp_token,
                "code": valid_code,
            },
        )

        assert totp_response.status_code == 200
        data = totp_response.json()
        assert data["success"] is True
        assert data["user_id"] == test_user_with_totp.id
        assert data["email"] == test_user_with_totp.email
        assert data["role"] == test_user_with_totp.role

    def test_verify_totp_invalid_code(
        self, client, test_user_with_totp, internal_secret
    ):
        """Test TOTP verification with invalid code."""
        # First, verify password to get TOTP token
        password_response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user_with_totp.email,
                "password": test_user_with_totp.plain_password,
            },
        )
        totp_token = password_response.json()["totp_token"]

        # Use an invalid TOTP code
        totp_response = client.post(
            "/internal/auth/verify-totp",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "totp_token": totp_token,
                "code": "000000",
            },
        )

        assert totp_response.status_code == 200
        data = totp_response.json()
        assert data["success"] is False

    def test_verify_totp_expired_token(
        self, client, test_user_with_totp, internal_secret
    ):
        """Test TOTP verification with expired pending token."""
        # Create an expired TOTP token manually
        import jwt
        from datetime import datetime, timedelta, timezone

        expired_payload = {
            "sub": str(test_user_with_totp.id),
            "type": "totp_pending",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        }
        expired_token = jwt.encode(
            expired_payload,
            auth_service.secret_key,
            algorithm=auth_service.algorithm,
        )

        # Try to verify with expired token
        totp_response = client.post(
            "/internal/auth/verify-totp",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "totp_token": expired_token,
                "code": "123456",
            },
        )

        assert totp_response.status_code == 200
        data = totp_response.json()
        assert data["success"] is False

    def test_verify_totp_invalid_token(self, client, internal_secret):
        """Test TOTP verification with invalid token."""
        totp_response = client.post(
            "/internal/auth/verify-totp",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "totp_token": "invalid_token",
                "code": "123456",
            },
        )

        assert totp_response.status_code == 200
        data = totp_response.json()
        assert data["success"] is False


class TestSessionManagement:
    """Test session creation and management for offline login."""

    def test_create_session_after_login(self, client, test_user, db, internal_secret):
        """Test creating a session after successful authentication."""
        # Verify password first
        auth_response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user.email,
                "password": test_user.plain_password,
            },
        )
        assert auth_response.json()["success"] is True

        # Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": test_user.id,
                "ttl_seconds": 3600,
            },
        )

        assert session_response.status_code == 200
        data = session_response.json()
        assert "session_id" in data

        # Verify session exists in database
        session = (
            db.query(UserSession)
            .filter(UserSession.user_id == test_user.id)
            .first()
        )
        assert session is not None
        assert session.is_active is True

    def test_validate_session(self, client, test_user, db, internal_secret):
        """Test validating an active session."""
        # Create session directly
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": test_user.id,
                "ttl_seconds": 3600,
            },
        )
        session_id = session_response.json()["session_id"]

        # Validate session
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},  # Convert to string
        )

        if validate_response.status_code != 200:
            print(f"Session ID: {session_id}, Type: {type(session_id)}")
            print(f"Validation response: {validate_response.status_code}")
            print(f"Response body: {validate_response.text}")

        assert validate_response.status_code == 200
        data = validate_response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role

    def test_validate_expired_session(self, client, test_user, db, internal_secret):
        """Test that expired sessions are rejected."""
        # Create an expired session directly in database
        import uuid

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
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": expired_session.session_token},
        )

        assert validate_response.status_code == 401

    def test_delete_session_logout(self, client, test_user, db, internal_secret):
        """Test session deletion (logout)."""
        # Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": test_user.id,
                "ttl_seconds": 3600,
            },
        )
        session_id = session_response.json()["session_id"]

        # Delete session
        delete_response = client.post(
            "/internal/auth/session/delete",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},  # Convert to string
        )

        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True

        # Verify session is gone
        session = (
            db.query(UserSession)
            .filter(UserSession.user_id == test_user.id)
            .first()
        )
        assert session is None


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing produces different hashes for same password."""
        password = "TestPassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

        # Both should verify correctly
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)

    def test_verify_password_incorrect(self):
        """Test that incorrect password fails verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        password_hash = auth_service.hash_password(password)

        assert not auth_service.verify_password(wrong_password, password_hash)


class TestTOTPGeneration:
    """Test TOTP secret generation and QR code generation."""

    def test_generate_totp_secret(self):
        """Test TOTP secret generation."""
        secret1 = auth_service.generate_totp_secret()
        secret2 = auth_service.generate_totp_secret()

        # Secrets should be base32 encoded
        assert len(secret1) > 0
        assert len(secret2) > 0
        assert secret1 != secret2

    def test_totp_provisioning_uri(self):
        """Test TOTP provisioning URI generation."""
        secret = auth_service.generate_totp_secret()
        email = "test@example.com"

        uri = auth_service.get_totp_provisioning_uri(secret, email)

        assert uri.startswith("otpauth://totp/")
        # Email is URL-encoded in the URI
        assert "test%40example.com" in uri or email in uri
        assert "Community%20Resilience" in uri or "Community Resilience" in uri

    def test_totp_qr_code_generation(self):
        """Test TOTP QR code SVG generation."""
        secret = auth_service.generate_totp_secret()
        email = "test@example.com"
        uri = auth_service.get_totp_provisioning_uri(secret, email)

        svg = auth_service.generate_totp_qr_svg(uri)

        assert svg.startswith("<?xml") or svg.startswith("<svg")
        assert len(svg) > 100


class TestCompleteOfflineLoginFlow:
    """Integration tests for complete offline login flows."""

    def test_complete_login_without_totp(self, client, test_user, internal_secret):
        """Test complete login flow: password -> session."""
        # Step 1: Verify password
        auth_response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user.email,
                "password": test_user.plain_password,
            },
        )

        assert auth_response.status_code == 200
        auth_data = auth_response.json()
        assert auth_data["success"] is True
        assert auth_data["totp_required"] is False

        # Step 2: Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": auth_data["user_id"],
                "ttl_seconds": 86400,
            },
        )

        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Step 3: Validate session
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},  # Convert to string
        )

        assert validate_response.status_code == 200
        assert validate_response.json()["id"] == test_user.id

    def test_complete_login_with_totp(
        self, client, test_user_with_totp, internal_secret
    ):
        """Test complete login flow: password -> TOTP -> session."""
        # Step 1: Verify password (returns TOTP challenge)
        password_response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user_with_totp.email,
                "password": test_user_with_totp.plain_password,
            },
        )

        assert password_response.status_code == 200
        password_data = password_response.json()
        assert password_data["success"] is True
        assert password_data["totp_required"] is True
        totp_token = password_data["totp_token"]

        # Step 2: Verify TOTP
        import pyotp

        totp = pyotp.TOTP(test_user_with_totp.plain_totp_secret)
        valid_code = totp.now()

        totp_response = client.post(
            "/internal/auth/verify-totp",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "totp_token": totp_token,
                "code": valid_code,
            },
        )

        assert totp_response.status_code == 200
        totp_data = totp_response.json()
        assert totp_data["success"] is True

        # Step 3: Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": totp_data["user_id"],
                "ttl_seconds": 86400,
            },
        )

        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Step 4: Validate session
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},  # Convert to string
        )

        assert validate_response.status_code == 200
        assert validate_response.json()["id"] == test_user_with_totp.id

    def test_complete_logout_flow(self, client, test_user, internal_secret):
        """Test complete logout flow: create session -> validate -> logout."""
        # Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": test_user.id,
                "ttl_seconds": 3600,
            },
        )
        session_id = session_response.json()["session_id"]

        # Validate session works
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},  # Convert to string
        )
        assert validate_response.status_code == 200

        # Logout
        logout_response = client.post(
            "/internal/auth/session/delete",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},  # Convert to string
        )
        assert logout_response.status_code == 200
        assert logout_response.json()["deleted"] is True

        # Validate session now fails
        validate_after_logout = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},  # Convert to string
        )
        assert validate_after_logout.status_code == 401
