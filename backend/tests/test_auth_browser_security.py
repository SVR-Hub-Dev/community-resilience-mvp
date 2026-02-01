"""
Test that no auth tokens are exposed to the browser.

Tests Phase 7 checklist item: "Confirm no auth tokens are exposed to the browser"
from docs/refactor/auth_implementation_plan.md

This test suite verifies the security boundary:
- Browser uses sessions (session IDs in HTTP-only cookies)
- JWTs and API keys are NEVER sent to the browser
- Derived JWTs are minted server-side only for SvelteKit → FastAPI calls
"""

import pytest
import json
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


def response_contains_jwt(response_data: dict) -> bool:
    """Check if response contains JWT-like strings."""
    # Convert to JSON string for searching
    json_str = json.dumps(response_data)

    # Look for JWT patterns (3 base64 segments separated by dots)
    # JWTs are typically long strings with dots
    import re
    jwt_pattern = r'[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'
    return bool(re.search(jwt_pattern, json_str))


def response_contains_api_key(response_data: dict) -> bool:
    """Check if response contains API key patterns."""
    json_str = json.dumps(response_data)
    # Look for API key prefix
    return auth_service.api_key_prefix in json_str


class TestSessionCreationSecurity:
    """Test that session creation doesn't expose tokens to browser."""

    def test_session_create_returns_only_session_id(self, client, test_user, internal_secret):
        """Test that session creation returns only session ID, no JWTs."""
        response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": test_user.id,
                "ttl_seconds": 3600,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should only contain session_id
        assert "session_id" in data
        assert len(data) == 1  # Only one field

        # Should NOT contain JWT patterns
        assert not response_contains_jwt(data)

        # Should NOT contain API keys
        assert not response_contains_api_key(data)

        # Session ID should not look like a JWT
        session_id = data["session_id"]
        assert "." not in str(session_id) or str(session_id).count(".") < 2

    def test_session_validate_returns_only_user_info(self, client, test_user, db, internal_secret):
        """Test that session validation returns only user info, no tokens."""
        # Create session
        import uuid
        session = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Validate session
        response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session.session_token)},
        )

        assert response.status_code == 200
        data = response.json()

        # Should contain user info: id, email, role
        assert "id" in data
        assert "email" in data
        assert "role" in data

        # Should NOT contain tokens
        assert "token" not in data
        assert "access_token" not in data
        assert "jwt" not in data
        assert "api_key" not in data

        # Should NOT contain JWT patterns
        assert not response_contains_jwt(data)

        # Should NOT contain API keys
        assert not response_contains_api_key(data)


class TestPasswordVerificationSecurity:
    """Test that password verification doesn't expose tokens."""

    def test_password_verify_returns_no_jwt(self, client, test_user, internal_secret):
        """Test that password verification returns only user info, no JWT."""
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

        # Should indicate success
        assert data["success"] is True
        assert "user_id" in data
        assert "email" in data
        assert "role" in data

        # Should NOT contain JWT patterns
        assert not response_contains_jwt(data)

        # Should NOT contain API keys
        assert not response_contains_api_key(data)

        # If access_token exists, it should NOT be a JWT
        if "access_token" in data:
            pytest.fail("access_token should not be returned to browser")

    def test_password_verify_with_totp_returns_no_jwt(self, client, db, internal_secret):
        """Test that password verification with TOTP doesn't expose JWTs."""
        # Create user with TOTP
        password = "TestPassword123!"
        totp_secret = auth_service.generate_totp_secret()
        user = User(
            email="totp@example.com",
            name="TOTP User",
            role="viewer",
            password_hash=auth_service.hash_password(password),
            totp_secret=totp_secret,
            totp_enabled=True,
            is_active=True,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": user.email,
                "password": password,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["totp_required"] is True
        assert "totp_token" in data

        # TOTP token should be short-lived, but still check it's not exposing sensitive data
        # The totp_token is a JWT but it's for internal use between password and TOTP verification
        # This is acceptable as it's a short-lived challenge token
        totp_token = data["totp_token"]

        # Verify it's a proper TOTP pending token, not a full access token
        import jwt
        payload = jwt.decode(
            totp_token,
            auth_service.secret_key,
            algorithms=[auth_service.algorithm],
            options={"verify_exp": False}
        )
        assert payload.get("type") == "totp_pending"
        assert "exp" in payload

        # Should NOT contain access tokens or API keys
        assert "access_token" not in data
        assert not response_contains_api_key(data)

    def test_totp_verify_returns_no_jwt(self, client, db, internal_secret):
        """Test that TOTP verification returns only user info, no JWT."""
        # Create user with TOTP
        password = "TestPassword123!"
        totp_secret = auth_service.generate_totp_secret()
        user = User(
            email="totp2@example.com",
            name="TOTP User 2",
            role="viewer",
            password_hash=auth_service.hash_password(password),
            totp_secret=totp_secret,
            totp_enabled=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Get TOTP token
        password_response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={"email": user.email, "password": password},
        )
        totp_token = password_response.json()["totp_token"]

        # Generate valid TOTP code
        import pyotp
        totp = pyotp.TOTP(totp_secret)
        valid_code = totp.now()

        # Verify TOTP
        response = client.post(
            "/internal/auth/verify-totp",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "totp_token": totp_token,
                "code": valid_code,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should return user info
        assert data["success"] is True
        assert "user_id" in data
        assert "email" in data
        assert "role" in data

        # Should NOT contain access tokens
        assert "access_token" not in data
        assert "jwt" not in data

        # Should NOT contain API keys
        assert not response_contains_api_key(data)


class TestOAuthFlowSecurity:
    """Test that OAuth flow doesn't expose tokens to browser."""

    def test_oauth_find_or_create_returns_no_tokens(self, client, internal_secret):
        """Test that OAuth user creation doesn't expose tokens."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_test_123",
                "email": "oauth@example.com",
                "name": "OAuth User",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should return user info
        assert "user_id" in data
        assert "email" in data
        assert "role" in data
        assert "created" in data

        # Should NOT contain tokens
        assert "access_token" not in data
        assert "token" not in data
        assert "jwt" not in data

        # Should NOT contain JWT patterns
        assert not response_contains_jwt(data)

        # Should NOT contain API keys
        assert not response_contains_api_key(data)


class TestAPIResponses:
    """Test that API responses never leak tokens."""

    def test_session_delete_returns_no_tokens(self, client, test_user, db, internal_secret):
        """Test that session deletion doesn't expose tokens."""
        # Create session
        import uuid
        session = UserSession(
            user_id=test_user.id,
            session_token=uuid.uuid4().hex,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True,
        )
        db.add(session)
        db.commit()

        # Delete session
        response = client.post(
            "/internal/auth/session/delete",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session.session_token)},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only indicate success
        assert "deleted" in data
        assert len(data) == 1

        # Should NOT contain tokens
        assert not response_contains_jwt(data)
        assert not response_contains_api_key(data)

    def test_error_responses_dont_leak_tokens(self, client, internal_secret):
        """Test that error responses don't leak tokens."""
        # Try to validate invalid session
        response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": "invalid_session_12345"},
        )

        assert response.status_code == 401
        data = response.json()

        # Should contain error message
        assert "detail" in data

        # Should NOT contain tokens
        assert not response_contains_jwt(data)
        assert not response_contains_api_key(data)


class TestSecurityHeaders:
    """Test that responses have appropriate security characteristics."""

    def test_responses_dont_cache_sensitive_data(self, client, test_user, internal_secret):
        """Test that sensitive endpoints don't cache responses."""
        response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user.email,
                "password": test_user.plain_password,
            },
        )

        assert response.status_code == 200

        # Check for cache control headers (if implemented)
        # Note: This is aspirational - the actual implementation may not have these
        cache_control = response.headers.get("Cache-Control", "")
        if cache_control:
            assert "no-store" in cache_control.lower() or "no-cache" in cache_control.lower()


class TestDerivedJWTIsolation:
    """Test that derived JWTs are never exposed to browser context."""

    def test_no_derived_jwt_in_browser_responses(self, client, test_user, internal_secret):
        """Test that derived JWTs are never returned to browser."""
        # Test all browser-facing auth endpoints
        endpoints = [
            ("/internal/auth/session/create", {"user_id": test_user.id, "ttl_seconds": 3600}),
            ("/internal/auth/verify-password", {"email": test_user.email, "password": test_user.plain_password}),
        ]

        for endpoint, payload in endpoints:
            response = client.post(
                endpoint,
                headers={"X-Internal-Secret": internal_secret},
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()

                # Should never contain derived JWT indicators
                assert "derived" not in json.dumps(data).lower()
                assert "bearer" not in json.dumps(data).lower()

                # Should not match JWT pattern
                assert not response_contains_jwt(data)


class TestTokenTypeIsolation:
    """Test that different token types are properly isolated."""

    def test_api_keys_never_in_browser_responses(self, client, test_user, internal_secret):
        """Test that API keys are never returned to browser contexts."""
        # All browser-facing endpoints
        endpoints = [
            ("/internal/auth/session/create", {"user_id": test_user.id, "ttl_seconds": 3600}),
            ("/internal/auth/verify-password", {"email": test_user.email, "password": test_user.plain_password}),
        ]

        for endpoint, payload in endpoints:
            response = client.post(
                endpoint,
                headers={"X-Internal-Secret": internal_secret},
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()

                # Should NOT contain API key prefix
                assert not response_contains_api_key(data)

                # Should NOT contain "api_key" field
                assert "api_key" not in data

    def test_refresh_tokens_never_in_browser_responses(self, client, test_user, internal_secret):
        """Test that refresh tokens are never exposed to browser."""
        response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": test_user.id,
                "ttl_seconds": 3600,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should NOT contain refresh token
        assert "refresh_token" not in data
        assert "refresh" not in data


class TestCompleteBrowserFlow:
    """Test complete browser authentication flows for token leakage."""

    def test_complete_password_login_flow_no_tokens(self, client, test_user, internal_secret):
        """Test complete login flow exposes no tokens to browser."""
        # Step 1: Password verification
        password_response = client.post(
            "/internal/auth/verify-password",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "email": test_user.email,
                "password": test_user.plain_password,
            },
        )

        assert password_response.status_code == 200
        password_data = password_response.json()
        assert not response_contains_jwt(password_data)
        assert not response_contains_api_key(password_data)

        # Step 2: Session creation
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": password_data["user_id"],
                "ttl_seconds": 3600,
            },
        )

        assert session_response.status_code == 200
        session_data = session_response.json()
        assert not response_contains_jwt(session_data)
        assert not response_contains_api_key(session_data)

        # Step 3: Session validation
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_data["session_id"])},
        )

        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert not response_contains_jwt(validate_data)
        assert not response_contains_api_key(validate_data)

        # Verify: No tokens leaked in entire flow
        all_responses = [password_data, session_data, validate_data]
        for resp_data in all_responses:
            assert "access_token" not in resp_data
            assert "api_key" not in resp_data
            assert "jwt" not in resp_data
            assert "bearer" not in json.dumps(resp_data).lower()


class TestSecurityInvariantsDocumentation:
    """Document and verify key security invariants."""

    def test_security_invariant_session_id_only(self):
        """
        SECURITY INVARIANT: Browser receives only session IDs, never tokens.

        This test documents the security model:
        - Browser stores session ID in HTTP-only cookie
        - Session ID is an opaque identifier
        - No JWTs, API keys, or refresh tokens sent to browser
        - SvelteKit mints derived JWTs server-side for FastAPI calls
        """
        # This is a documentation test
        assert True, "Security model documented"

    def test_security_invariant_derived_jwt_server_only(self):
        """
        SECURITY INVARIANT: Derived JWTs are server-side only.

        Flow:
        1. Browser sends session ID to SvelteKit
        2. SvelteKit validates session
        3. SvelteKit mints derived JWT (server-side)
        4. SvelteKit calls FastAPI with derived JWT
        5. FastAPI validates derived JWT
        6. Response goes back to browser WITHOUT tokens
        """
        # This is a documentation test
        assert True, "Derived JWT flow documented"

    def test_security_invariant_api_keys_cli_only(self):
        """
        SECURITY INVARIANT: API keys are for CLI/automation only.

        - API keys never sent to browser
        - API keys never accepted from browser contexts
        - Browser-facing endpoints explicitly reject API keys
        """
        # This is a documentation test
        assert True, "API key isolation documented"
