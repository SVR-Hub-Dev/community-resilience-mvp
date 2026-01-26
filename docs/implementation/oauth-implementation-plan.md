# OAuth Implementation Plan

## Overview

Add OAuth 2.0 social login (Google, GitHub) as an alternative authentication method alongside existing API key authentication.

## Prerequisites

- Existing auth infrastructure in `auth/` directory
- Database models already support OAuth (User table can link to OAuth providers)
- FastAPI OAuth dependencies available

---

## Phase 1: OAuth Provider Setup

### 1.1 Register OAuth Applications

#### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable "Google+ API"
4. Create OAuth 2.0 credentials
5. Set authorized redirect URIs:
   - Development: `http://localhost:8000/auth/callback/google`
   - Production: `https://yourdomain.com/auth/callback/google`
6. Note down Client ID and Client Secret

#### GitHub OAuth

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create new OAuth App
3. Set callback URL:
   - Development: `http://localhost:8000/auth/callback/github`
   - Production: `https://yourdomain.com/auth/callback/github`
4. Note down Client ID and Client Secret

### 1.2 Update Environment Variables

````bash
# ...existing code...

# OAuth Configuration
OAUTH_GOOGLE_CLIENT_ID=your_google_client_id
OAUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret
OAUTH_GITHUB_CLIENT_ID=your_github_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_github_client_secret

# Session secret for JWT tokens
SECRET_KEY=generate_random_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440  # 24 hours

# Frontend URL for redirects
FRONTEND_URL=http://localhost:5173

# ...existing code...
````

---

## Phase 2: Database Schema Updates

### 2.1 Create Migration for OAuth Tables

````python
"""Add OAuth support tables

Revision ID: 003
Revises: 002
Create Date: 2026-01-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # Add OAuth provider info to users table
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(512), nullable=True))
    
    # Create index for OAuth lookups
    op.create_index('ix_users_oauth_provider_id', 'users', ['oauth_provider', 'oauth_id'])
    
    # Create sessions table for JWT tokens
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('user_agent', sa.String(512)),
        sa.Column('ip_address', sa.String(45))
    )
    
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_expires_at', 'user_sessions', ['expires_at'])

def downgrade():
    op.drop_table('user_sessions')
    op.drop_column('users', 'oauth_provider')
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'avatar_url')
````

---

## Phase 3: Update Auth Models

### 3.1 Enhance User Model

````python
# ...existing code...

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default=UserRole.VIEWER.value, nullable=False)
    
    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'github', None
    oauth_id = Column(String(255), nullable=True)  # Provider's user ID
    avatar_url = Column(String(512), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))
    user_agent = Column(String(512))
    ip_address = Column(String(45))
    
    # Relationships
    user = relationship("User", back_populates="sessions")

# ...existing code...
````

---

## Phase 4: Implement OAuth Service

### 4.1 Create OAuth Configuration

````python
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

config = Config('.env')

oauth = OAuth()

# Google OAuth
oauth.register(
    name='google',
    client_id=config('OAUTH_GOOGLE_CLIENT_ID', default=''),
    client_secret=config('OAUTH_GOOGLE_CLIENT_SECRET', default=''),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# GitHub OAuth
oauth.register(
    name='github',
    client_id=config('OAUTH_GITHUB_CLIENT_ID', default=''),
    client_secret=config('OAUTH_GITHUB_CLIENT_SECRET', default=''),
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    refresh_token_url=None,
    client_kwargs={'scope': 'user:email'}
)
````

### 4.2 Enhance Auth Service with JWT

````python
from datetime import datetime, timedelta
from jose import JWTError, jwt
import hashlib
from config import settings

# ...existing code...

class AuthService:
    # ...existing code...
    
    def create_session_token(self, user_id: str) -> tuple[str, str]:
        """Create JWT session token and return (token, token_hash)"""
        expiration = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
        
        payload = {
            "sub": str(user_id),
            "exp": expiration,
            "iat": datetime.utcnow(),
            "type": "session"
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        return token, token_hash
    
    def verify_session_token(self, token: str) -> str | None:
        """Verify JWT token and return user_id if valid"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "session":
                return None
            return payload.get("sub")
        except JWTError:
            return None
    
    def get_or_create_oauth_user(
        self, 
        db, 
        email: str, 
        name: str, 
        provider: str, 
        oauth_id: str,
        avatar_url: str = None
    ) -> User:
        """Get existing OAuth user or create new one"""
        # Check if user exists with this OAuth provider
        user = db.query(User).filter(
            User.oauth_provider == provider,
            User.oauth_id == oauth_id
        ).first()
        
        if user:
            # Update user info
            user.name = name
            user.email = email
            if avatar_url:
                user.avatar_url = avatar_url
            db.commit()
            db.refresh(user)
            return user
        
        # Check if user exists with same email (link accounts)
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.oauth_provider = provider
            user.oauth_id = oauth_id
            if avatar_url:
                user.avatar_url = avatar_url
            db.commit()
            db.refresh(user)
            return user
        
        # Create new user
        user = User(
            email=email,
            name=name,
            oauth_provider=provider,
            oauth_id=oauth_id,
            avatar_url=avatar_url,
            role=UserRole.VIEWER.value  # Default role for OAuth users
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def create_user_session(
        self,
        db,
        user_id: str,
        user_agent: str = None,
        ip_address: str = None
    ) -> tuple[str, UserSession]:
        """Create a new user session and return (token, session)"""
        token, token_hash = self.create_session_token(user_id)
        
        session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES),
            user_agent=user_agent,
            ip_address=ip_address
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return token, session

auth_service = AuthService()
````

---

## Phase 5: Update Dependencies

### 5.1 Add OAuth Dependency

````python
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from db import get_db_session
from auth.service import auth_service
from auth.models import User, UserRole
import hashlib

# ...existing code...

security_bearer = HTTPBearer(auto_error=False)

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: Session = Depends(get_db_session)
) -> User | None:
    """Get current user from API key or session token (optional)"""
    if not credentials:
        return None
    
    token = credentials.credentials
    
    # Try API key first
    user = auth_service.get_user_by_api_key(db, token)
    if user:
        return user
    
    # Try session token
    user_id = auth_service.verify_session_token(token)
    if user_id:
        # Verify session exists and is not expired
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session = db.query(UserSession).filter(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if session:
            # Update last used
            session.last_used_at = datetime.utcnow()
            db.commit()
            
            return db.query(User).filter(User.id == user_id).first()
    
    return None

async def get_current_user(
    user: User | None = Depends(get_current_user_optional)
) -> User:
    """Get current user from API key or session token (required)"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# ...existing code...
````

---

## Phase 6: Implement OAuth Routes

### 6.1 Add OAuth Endpoints

````python
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from db import get_db_session
from auth.oauth import oauth
from auth.service import auth_service
from auth.dependencies import get_current_user
from auth.models import User
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# ...existing code...

@router.get("/login/{provider}")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login flow"""
    if provider not in ['google', 'github']:
        raise HTTPException(status_code=400, detail="Invalid OAuth provider")
    
    redirect_uri = request.url_for('oauth_callback', provider=provider)
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)

@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """Handle OAuth callback"""
    if provider not in ['google', 'github']:
        raise HTTPException(status_code=400, detail="Invalid OAuth provider")
    
    try:
        # Get access token
        token = await oauth.create_client(provider).authorize_access_token(request)
        
        # Get user info from provider
        if provider == 'google':
            user_info = token.get('userinfo')
            email = user_info.get('email')
            name = user_info.get('name')
            oauth_id = user_info.get('sub')
            avatar_url = user_info.get('picture')
        elif provider == 'github':
            resp = await oauth.github.get('user', token=token)
            user_info = resp.json()
            email = user_info.get('email')
            name = user_info.get('name') or user_info.get('login')
            oauth_id = str(user_info.get('id'))
            avatar_url = user_info.get('avatar_url')
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by OAuth provider")
        
        # Get or create user
        user = auth_service.get_or_create_oauth_user(
            db, email, name, provider, oauth_id, avatar_url
        )
        
        # Create session
        user_agent = request.headers.get('user-agent')
        ip_address = request.client.host if request.client else None
        session_token, _ = auth_service.create_user_session(db, str(user.id), user_agent, ip_address)
        
        # Redirect to frontend with token
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback?token={session_token}"
        return RedirectResponse(url=frontend_url)
        
    except Exception as e:
        # Redirect to frontend with error
        frontend_url = f"{settings.FRONTEND_URL}/auth/callback?error=oauth_failed"
        return RedirectResponse(url=frontend_url)

@router.post("/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Logout and invalidate session token"""
    auth_header = request.headers.get('authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Delete session
        db.query(UserSession).filter(UserSession.token_hash == token_hash).delete()
        db.commit()
    
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "oauth_provider": user.oauth_provider,
        "avatar_url": user.avatar_url
    }

# ...existing code...
````

---

## Phase 7: Update Configuration

### 7.1 Add OAuth Settings

````python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ...existing code...
    
    # OAuth Configuration
    OAUTH_GOOGLE_CLIENT_ID: str = ""
    OAUTH_GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_GITHUB_CLIENT_ID: str = ""
    OAUTH_GITHUB_CLIENT_SECRET: str = ""
    
    # JWT Configuration
    SECRET_KEY: str = "change-this-to-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    
    # Frontend URL
    FRONTEND_URL: str = "http://localhost:5173"
    
    # ...existing code...

settings = Settings()
````

---

## Phase 8: Update Requirements

### 8.1 Add OAuth Dependencies

````python
# ...existing code...

# OAuth
authlib==1.3.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
````

---

## Phase 9: Frontend Integration

### 9.1 Create OAuth Login Component

````svelte
<script>
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  function loginWithGoogle() {
    window.location.href = `${API_URL}/auth/login/google`;
  }
  
  function loginWithGitHub() {
    window.location.href = `${API_URL}/auth/login/github`;
  }
</script>

<div class="oauth-buttons">
  <button on:click={loginWithGoogle} class="btn-oauth btn-google">
    <svg class="icon"><!-- Google icon SVG --></svg>
    Continue with Google
  </button>
  
  <button on:click={loginWithGitHub} class="btn-oauth btn-github">
    <svg class="icon"><!-- GitHub icon SVG --></svg>
    Continue with GitHub
  </button>
</div>

<style>
  .oauth-buttons {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-width: 300px;
  }
  
  .btn-oauth {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.5rem;
    border: 1px solid #ddd;
    border-radius: 0.5rem;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-oauth:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
</style>
````

### 9.2 Create OAuth Callback Handler

````svelte
<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  
  onMount(() => {
    const token = $page.url.searchParams.get('token');
    const error = $page.url.searchParams.get('error');
    
    if (token) {
      // Store token in localStorage
      localStorage.setItem('auth_token', token);
      
      // Redirect to dashboard
      goto('/dashboard');
    } else if (error) {
      // Handle error
      goto('/login?error=' + error);
    }
  });
</script>

<div class="loading">
  <p>Completing login...</p>
</div>
````

---

## Phase 10: Testing & Deployment

### 10.1 Testing Checklist

- [ ] Google OAuth login flow
- [ ] GitHub OAuth login flow
- [ ] Session token validation
- [ ] Session expiration
- [ ] Logout functionality
- [ ] API key authentication still works
- [ ] Role-based access control
- [ ] Account linking (same email, different providers)
- [ ] Token refresh on expiration
- [ ] Security: CSRF protection, XSS prevention

### 10.2 Deployment Steps

1. **Generate secure SECRET_KEY**:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update production environment variables**

3. **Run database migration**:

   ```bash
   alembic upgrade head
   ```

4. **Update OAuth redirect URIs** in Google/GitHub console to production URLs

5. **Test OAuth flow** in production environment

---

## Summary

This plan implements OAuth authentication alongside existing API key authentication, providing users with multiple login options while maintaining backward compatibility. The hybrid system supports both programmatic access (API keys) and human users (OAuth).
