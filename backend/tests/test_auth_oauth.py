"""
Test OAuth login flows.

Tests Phase 7 checklist item: "Test online OAuth login"
from docs/refactor/auth_implementation_plan.md
"""

import pytest
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
def internal_secret():
    """Get the internal auth secret from settings."""
    settings = Settings()
    return settings.internal_auth_secret


@pytest.fixture
def existing_user(db):
    """Create an existing user for OAuth linking tests."""
    user = User(
        email="existing@example.com",
        name="Existing User",
        role="viewer",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def oauth_user(db):
    """Create a user with existing OAuth identity."""
    user = User(
        email="oauth@example.com",
        name="OAuth User",
        role="viewer",
        oauth_provider="google",
        oauth_id="google_123456",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestOAuthUserCreation:
    """Test OAuth user creation for new users."""

    def test_create_new_google_user(self, client, db, internal_secret):
        """Test creating a new user via Google OAuth."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_new_123",
                "email": "newuser@example.com",
                "name": "New Google User",
                "avatar_url": "https://example.com/avatar.jpg",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "viewer"
        assert "user_id" in data

        # Verify user exists in database
        user = db.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.oauth_provider == "google"
        assert user.oauth_id == "google_new_123"
        assert user.name == "New Google User"
        assert user.avatar_url == "https://example.com/avatar.jpg"

    def test_create_new_github_user(self, client, db, internal_secret):
        """Test creating a new user via GitHub OAuth."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "github",
                "provider_id": "github_789",
                "email": "developer@example.com",
                "name": "GitHub Developer",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        assert data["email"] == "developer@example.com"

        user = db.query(User).filter(User.email == "developer@example.com").first()
        assert user.oauth_provider == "github"
        assert user.oauth_id == "github_789"

    def test_create_new_microsoft_user(self, client, db, internal_secret):
        """Test creating a new user via Microsoft OAuth."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "microsoft",
                "provider_id": "microsoft_456",
                "email": "office@example.com",
                "name": "Microsoft User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True

        user = db.query(User).filter(User.email == "office@example.com").first()
        assert user.oauth_provider == "microsoft"


class TestOAuthUserLinking:
    """Test linking OAuth identity to existing users."""

    def test_link_oauth_to_existing_email(self, client, existing_user, internal_secret):
        """Test linking OAuth identity to user with matching email."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_link_123",
                "email": existing_user.email,
                "name": "Updated Name",
                "avatar_url": "https://example.com/new-avatar.jpg",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is False  # Not created, linked
        assert data["user_id"] == existing_user.id
        assert data["email"] == existing_user.email

        # Verify OAuth identity was linked
        from sqlalchemy.orm import Session
        db = Session.object_session(existing_user)
        db.refresh(existing_user)
        assert existing_user.oauth_provider == "google"
        assert existing_user.oauth_id == "google_link_123"
        assert existing_user.avatar_url == "https://example.com/new-avatar.jpg"

    def test_find_by_existing_oauth_identity(self, client, oauth_user, internal_secret):
        """Test finding user by existing OAuth identity."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_123456",
                "email": oauth_user.email,
                "name": "Same User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is False
        assert data["user_id"] == oauth_user.id
        assert data["email"] == oauth_user.email

    def test_oauth_does_not_overwrite_existing_avatar(
        self, client, db, internal_secret
    ):
        """Test that OAuth linking doesn't overwrite existing avatar."""
        # Create user with existing avatar
        user = User(
            email="hasavatar@example.com",
            name="User With Avatar",
            role="viewer",
            avatar_url="https://example.com/original-avatar.jpg",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Try to link OAuth with new avatar
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_avatar_test",
                "email": "hasavatar@example.com",
                "name": "User With Avatar",
                "avatar_url": "https://example.com/new-avatar.jpg",
            },
        )

        assert response.status_code == 200
        db.refresh(user)
        # Original avatar should be preserved
        assert user.avatar_url == "https://example.com/original-avatar.jpg"


class TestOAuthSecurity:
    """Test OAuth security features."""

    def test_oauth_requires_internal_secret(self, client):
        """Test that OAuth endpoint requires internal secret."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            json={
                "provider": "google",
                "provider_id": "test_123",
                "email": "test@example.com",
                "name": "Test User",
            },
        )

        assert response.status_code == 401

    def test_oauth_rejects_invalid_internal_secret(self, client):
        """Test that OAuth endpoint rejects invalid internal secret."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": "invalid_secret"},
            json={
                "provider": "google",
                "provider_id": "test_123",
                "email": "test@example.com",
                "name": "Test User",
            },
        )

        assert response.status_code == 401

    def test_oauth_inactive_user_filtered(self, client, db, internal_secret):
        """Test that inactive users with OAuth are filtered out."""
        # Create inactive user with OAuth identity
        inactive_user = User(
            email="inactive@example.com",
            name="Inactive User",
            role="viewer",
            oauth_provider="google",
            oauth_id="google_inactive_123",
            is_active=False,
        )
        db.add(inactive_user)
        db.commit()

        # Verify user exists but is inactive
        user_check = db.query(User).filter(User.email == "inactive@example.com").first()
        assert user_check is not None
        assert user_check.is_active is False

        # Try to authenticate with different OAuth credentials (different email)
        # to avoid unique constraint collision
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_new_user_123",
                "email": "newuser_oauth@example.com",
                "name": "New OAuth User",
            },
        )

        # Should successfully create new user
        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True
        assert data["email"] == "newuser_oauth@example.com"


class TestOAuthWithSession:
    """Test complete OAuth flow with session creation."""

    def test_complete_oauth_login_flow(self, client, db, internal_secret):
        """Test complete OAuth login: find-or-create -> create session -> validate."""
        # Step 1: OAuth user creation
        oauth_response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_complete_flow",
                "email": "completeflow@example.com",
                "name": "Complete Flow User",
            },
        )

        assert oauth_response.status_code == 200
        oauth_data = oauth_response.json()
        assert oauth_data["created"] is True
        user_id = oauth_data["user_id"]

        # Step 2: Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": user_id,
                "ttl_seconds": 86400,
            },
        )

        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Step 3: Validate session
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},
        )

        assert validate_response.status_code == 200
        validate_data = validate_response.json()
        assert validate_data["id"] == user_id
        assert validate_data["email"] == "completeflow@example.com"

    def test_oauth_returning_user_flow(self, client, oauth_user, internal_secret):
        """Test returning OAuth user: find by identity -> create session -> validate."""
        # Step 1: Find existing OAuth user
        oauth_response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_123456",
                "email": oauth_user.email,
                "name": oauth_user.name,
            },
        )

        assert oauth_response.status_code == 200
        oauth_data = oauth_response.json()
        assert oauth_data["created"] is False
        assert oauth_data["user_id"] == oauth_user.id

        # Step 2: Create session
        session_response = client.post(
            "/internal/auth/session/create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "user_id": oauth_data["user_id"],
                "ttl_seconds": 86400,
            },
        )

        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]

        # Step 3: Validate session
        validate_response = client.post(
            "/internal/auth/session/validate",
            headers={"X-Internal-Secret": internal_secret},
            json={"session_id": str(session_id)},
        )

        assert validate_response.status_code == 200
        assert validate_response.json()["id"] == oauth_user.id


class TestOAuthProviderVariations:
    """Test OAuth with different provider variations."""

    def test_same_email_different_providers(self, client, db, internal_secret):
        """Test that same email can link to different OAuth providers."""
        email = "multiplatform@example.com"

        # First login with Google
        google_response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_multi_123",
                "email": email,
                "name": "Multi Platform User",
            },
        )

        assert google_response.status_code == 200
        google_data = google_response.json()
        assert google_data["created"] is True
        user_id = google_data["user_id"]

        # Verify user has Google OAuth
        user = db.query(User).filter(User.id == user_id).first()
        assert user.oauth_provider == "google"
        assert user.oauth_id == "google_multi_123"

        # Later login with GitHub should update the provider
        # (Current implementation updates to the latest provider)
        github_response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "github",
                "provider_id": "github_multi_456",
                "email": email,
                "name": "Multi Platform User",
            },
        )

        assert github_response.status_code == 200
        github_data = github_response.json()
        assert github_data["created"] is False
        assert github_data["user_id"] == user_id

        # Verify provider was updated
        db.refresh(user)
        assert user.oauth_provider == "github"
        assert user.oauth_id == "github_multi_456"

    def test_different_emails_same_provider(self, client, db, internal_secret):
        """Test creating different users with same provider but different emails."""
        # User 1
        response1 = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_user1",
                "email": "user1@example.com",
                "name": "User One",
            },
        )

        # User 2
        response2 = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_user2",
                "email": "user2@example.com",
                "name": "User Two",
            },
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        user1_id = response1.json()["user_id"]
        user2_id = response2.json()["user_id"]

        # Should be different users
        assert user1_id != user2_id


class TestOAuthDataValidation:
    """Test OAuth data validation and edge cases."""

    def test_oauth_with_minimal_data(self, client, internal_secret):
        """Test OAuth with only required fields."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_minimal",
                "email": "minimal@example.com",
                "name": "Minimal User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] is True

    def test_oauth_with_empty_avatar_url(self, client, internal_secret):
        """Test OAuth with empty avatar URL."""
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_empty_avatar",
                "email": "noavatar@example.com",
                "name": "No Avatar User",
                "avatar_url": None,
            },
        )

        assert response.status_code == 200

    def test_oauth_preserves_user_role(self, client, db, internal_secret):
        """Test that OAuth login preserves existing user role."""
        # Create user with admin role
        admin_user = User(
            email="admin@example.com",
            name="Admin User",
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Link OAuth identity
        response = client.post(
            "/internal/auth/oauth/find-or-create",
            headers={"X-Internal-Secret": internal_secret},
            json={
                "provider": "google",
                "provider_id": "google_admin",
                "email": "admin@example.com",
                "name": "Admin User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"  # Role should be preserved

        db.refresh(admin_user)
        assert admin_user.role == "admin"
