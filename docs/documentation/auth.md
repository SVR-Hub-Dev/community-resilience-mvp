# Authentication & Authorization System

## Overview

The Community Resilience MVP implements a **hybrid authentication system** designed to support both browser-based users and programmatic access. The system uses:

- **Primary**: Derived JWT tokens from SvelteKit for browser sessions  
- **Secondary**: API keys for CLI/automation tools
- **Legacy Support**: OAuth JWTs and refresh tokens (maintained for backwards compatibility)

### Key Design Principles

1. **Security First**: API keys cannot be used from browser contexts to prevent XSS attacks
2. **Separation of Concerns**: Browser authentication handled by SvelteKit, backend validates tokens
3. **Role-Based Access Control (RBAC)**: Three-tier permission system (Admin, Editor, Viewer)
4. **Session Authority**: SvelteKit is the authoritative session manager, backend validates via internal API

---

## User Roles & Permissions

### Role Hierarchy

```text
ADMIN (highest privileges)
  ├─ User management (create, edit, delete users)
  ├─ Role assignment (promote/demote users)
  ├─ All EDITOR capabilities
  └─ All VIEWER capabilities

EDITOR
  ├─ Create/upload documents
  ├─ Create/edit knowledge entries
  ├─ Create/edit community events
  ├─ Create/edit community assets
  ├─ All VIEWER capabilities
  
VIEWER (default for new users)
  └─ Read-only access to all content
```

### Default Role Assignment

- **OAuth Registration**: New users get `VIEWER` role
- **Password Registration**: New users get `VIEWER` role  
- **seed_admin.py**: Creates users with `ADMIN` role
- **Admin UI**: Admins can change any user's role

---

## Architecture Components

### User Model

```python
class User(Base):
    id: int
    email: str                        # Unique identifier
    name: str                         # Display name
    role: str                         # admin/editor/viewer

    # Password Authentication
    password_hash: str | None         # bcrypt hash (NULL for OAuth-only)

    # OAuth Support
    oauth_provider: str | None        # google/github/microsoft
    oauth_id: str | None              # Provider's user ID
    avatar_url: str | None

    # 2FA Support
    totp_secret: str | None           # Base32-encoded TOTP secret
    totp_enabled: bool

    # Status
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Relationships
    api_keys: List[APIKey]
    sessions: List[Session]
```

### API Key Model

```python
class APIKey(Base):
    id: int
    user_id: int
    key_hash: str                     # SHA-256 hash
    key_prefix: str                   # First 12 chars (e.g., "cr_abc123...")
    name: str
    description: str | None
    scopes: List[str] | None          # Future: granular permissions
    last_used_at: datetime | None     # Audit trail
    expires_at: datetime | None
    is_active: bool
    created_at: datetime
```

**Key Format**: `cr_<random_24_chars>` (example: `cr_sk3t7M1b5VKGs1l4ZzLUHIdKCIx`)

### Session Model

```python
class Session(Base):
    id: int
    user_id: int
    session_token: str                # UUID identifier
    refresh_token_hash: str | None    # Legacy OAuth refresh token
    user_agent: str | None
    ip_address: str | None            # IPv6 supported
    expires_at: datetime
    is_active: bool
    created_at: datetime
```

---

## Authentication Flows

### Browser Authentication (Primary Method)

**Components**:

- SvelteKit manages sessions (session authority)
- Backend validates sessions via internal API
- Derived JWTs for API authentication

**Login Flow**:

```text
1. User submits credentials (password or OAuth)
2. SvelteKit calls POST /internal/auth/verify-password
3. Backend returns user_id + role
4. SvelteKit calls POST /internal/auth/session/create
5. Backend creates Session record, returns session_id
6. SvelteKit sets session_id cookie (HttpOnly, Secure, SameSite=Lax)
7. SvelteKit mints derived JWT with claims: {sub: user_id, role: role, exp: 24h}
8. User makes API request with Authorization: Bearer <derived_jwt>
9. Backend verifies JWT signature (DERIVED_JWT_SECRET)
10. Backend extracts user_id from 'sub' claim
11. Backend loads User from database, checks is_active
12. Request authorized with user's role
```

**Key Files**:

- `frontend/src/hooks.server.ts` - Session validation on each request
- `backend/auth/derived.py` - Derived JWT verification
- `backend/auth/dependencies.py` - `get_current_user_from_derived_jwt()`

**Security**:

- API keys are **rejected** on browser routes
- Cookies are HttpOnly (prevent XSS theft)
- JWT signed with separate secret (`DERIVED_JWT_SECRET`)
- Sessions stored in database for audit trail

### API Key Authentication (Programmatic Access)

**Flow**:

```text
1. CLI tool makes request with Authorization: Bearer cr_...
2. Backend dependency `get_current_user()` verifies:
   a. Hashes API key (SHA-256)
   b. Queries APIKey table WHERE key_hash = <hash> AND is_active = true
   c. Checks expires_at (if set)
   d. Updates last_used_at timestamp
   e. Loads User record via user_id
   f. Checks user.is_active
3. Request authorized with user's role
```

**Key Files**:

- `backend/auth/service.py` - `verify_api_key()` method
- `backend/auth/dependencies.py` - `get_current_user()` (accepts API keys)

**Security Notes**:

- Keys hashed with SHA-256 (irreversible)
- Prefix allows identification without full key
- CLI routes use `require_viewer_or_api_key()` dependency
- Browser routes use `require_viewer()` (rejects API keys)

---

## Role-Based Access Control

### FastAPI Dependencies

**Browser-Only Routes** (API keys rejected):

```python
from auth.dependencies import require_admin, require_editor, require_viewer

@app.get("/admin/users")
def list_users(user: User = Depends(require_admin)):
    # Only admins with derived JWTs
    ...

@app.post("/documents/upload")  
def upload_document(user: User = Depends(require_editor)):
    # Editors and admins with derived JWTs
    ...

@app.get("/knowledge")
def get_knowledge(user: User = Depends(require_viewer)):
    # All authenticated browser users
    ...
```

**CLI/Automation Routes** (API keys accepted):

```python
from auth.dependencies import require_editor_or_api_key

@app.post("/sync/documents")
def sync_documents(user: User = Depends(require_editor_or_api_key)):
    # CLI tools with API keys OR browser users with JWTs
    ...
```

### Frontend Route Protection

**Server-Side** (`+page.server.ts`):

```typescript
import { redirect } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ locals }) => {
    // Require authentication
    if (!locals.user) {
        throw redirect(302, '/auth/login?redirect=/events');
    }

    // Require specific role
    const canEdit = locals.user.role === 'admin' || locals.user.role === 'editor';

    return { canEdit };
};
```

**Client-Side UI** (`+page.svelte`):

```svelte
<script lang="ts">
    let { data } = $props();
    let canEdit = $derived(data.canEdit);
</script>

{#if canEdit}
    <button class="btn">Add Entry</button>
{:else}
    <div class="info-banner">
        📖 Viewing mode - Contact an editor to add entries
    </div>
{/if}
```

---

## Role Provisioning

### Initial Admin Setup

**Script**: `backend/scripts/seed_admin.py`

```bash
python scripts/seed_admin.py \
    --email admin@example.com \
    --name "Admin User" \
    --key-name "Initial Admin Key"
```

**What it does**:

1. Creates User with `role='admin'` (or promotes existing user)
2. Generates API key: `cr_<random_24_chars>`
3. Prints API key (shown only once - **save it!**)

**Example Output**:

```text
============================================================
Admin user setup complete!
============================================================

Email: admin@example.com
Name: Admin User
Role: admin

API Key (save this - it won't be shown again):

  cr_sk3t7M1b5VKGs1l4ZzLUHIdKCIx

============================================================
Use this key in the Authorization header:
  Authorization: Bearer cr_sk3t7M1b5VKGs1l4ZzLUHIdKCIx
============================================================
```

**Usage**:

```bash
# Store in .env
ADMIN_API_KEY=cr_sk3t7M1b5VKGs1l4ZzLUHIdKCIx

# Use in requests
curl -H "Authorization: Bearer $ADMIN_API_KEY" \
  http://localhost:8000/admin/users
```

### Managing Users via Admin UI

**Route**: `/admin/users` (admin role required)

**Features**:

1. **View all users** - Table with email, role, OAuth provider, status, join date
2. **Edit roles** - Change between viewer/editor/admin
3. **Activate/deactivate** - Toggle `is_active` status
4. **Delete users** - Remove non-admin users

**Process**:

1. Navigate to `/admin/users` (must be logged in as admin)
2. Click "Edit" button on user row
3. Select new role: `viewer`, `editor`, or `admin`
4. Toggle "Account is active" checkbox
5. Click "Save Changes"

**Restrictions**:

- Cannot edit your own account
- Cannot delete admin users  
- Cannot delete yourself
- Cannot delete API-only users (created via seed_admin.py)

**Backend Endpoints**:

```python
# List users
GET /admin/users?limit=100

# Update role/status
PATCH /admin/users/{user_id}
{
    "role": "editor",
    "is_active": true
}

# Delete user
DELETE /admin/users/{user_id}
```

### OAuth User Registration

When users sign in via OAuth (Google, GitHub, Microsoft):

1. **New user**: Assigned `VIEWER` role (default)
2. **Existing user** (by email): OAuth identity linked, role preserved
3. **Existing OAuth user**: Role preserved

**Backend Logic**:

```python
@router.post("/oauth/find-or-create")
def internal_oauth_find_or_create(payload: OAuthUserIn, ...):
    # 1. Find by (provider, provider_id)
    user = find_by_oauth_identity(payload.provider, payload.provider_id)
    if user:
        return user  # Keeps existing role

    # 2. Find by email and link
    user = find_by_email(payload.email)
    if user:
        link_oauth_identity(user, payload)
        return user  # Keeps existing role

    # 3. Create new user
    user = User(
        email=payload.email,
        name=payload.name,
        role=UserRole.VIEWER.value,  # Default for new users
        oauth_provider=payload.provider,
        oauth_id=payload.provider_id,
    )
    return user
```

---

## Password Authentication

### Registration

**Frontend**: `/auth/register`  
**Backend**: `POST /internal/auth/register`

```python
def register_user(db, email: str, password: str, name: str) -> User:
    # Check uniqueness
    if user_exists(email):
        raise ValueError("Email already registered")

    # Create user
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),  # bcrypt, 12 rounds
        role=UserRole.VIEWER.value,             # Default
    )
    db.add(user)
    db.commit()
    return user
```

**Password Requirements**:

- Minimum 8 characters (frontend validation)
- No complexity requirements (research shows they reduce security)

### Login

**Frontend**: `/auth/login`  
**Backend**: `POST /internal/auth/verify-password`

```python
@router.post("/verify-password")
def internal_verify_password(payload: PasswordVerifyIn, ...):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        return PasswordVerifyOut(success=False)

    # Check 2FA
    if user.totp_enabled:
        totp_token = create_totp_pending_token(user.id)
        return PasswordVerifyOut(
            success=True,
            totp_required=True,
            totp_token=totp_token,
        )

    # Return user info
    return PasswordVerifyOut(
        success=True,
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
```

---

## Two-Factor Authentication (2FA)

### TOTP Setup

Users can enable TOTP-based 2FA (Google Authenticator, Authy, 1Password compatible).

**Process**:

1. Navigate to security settings
2. Backend generates TOTP secret (`pyotp.random_base32()`)
3. Display QR code with provisioning URI:

   ```text
   otpauth://totp/Community%20Resilience:user@example.com?
   secret=<base32_secret>&issuer=Community%20Resilience
   ```

4. User scans QR code with authenticator app
5. User enters 6-digit verification code
6. If valid: `user.totp_enabled = True`, `user.totp_secret = <secret>`

### Login with 2FA

**Flow**:

1. User enters email/password
2. Backend returns `totp_required=True` + temporary token (5min JWT)
3. Frontend shows TOTP code input
4. User enters 6-digit code
5. Backend verifies: `pyotp.TOTP(secret).verify(code, valid_window=1)`
6. Session created on success

---

## Session Management

### Session Lifecycle

**Creation**:

```python
session = Session(
    user_id=user_id,
    session_token=uuid.uuid4().hex,
    expires_at=now() + timedelta(hours=24),
    is_active=True,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
)
```

**Validation** (on each request):

```python
session = db.query(Session).filter(
    Session.session_token == session_id,
    Session.is_active == True,
    Session.expires_at > now(),
).first()

user = db.query(User).filter(
    User.id == session.user_id,
    User.is_active == True,
).first()
```

**Deletion** (logout):

```python
db.query(Session).filter(
    Session.session_token == session_id
).delete()
```

**Cookie Details**:

- Name: `session_id`
- HttpOnly: Yes (prevent XSS)
- Secure: Yes in production (HTTPS only)
- SameSite: Lax (CSRF protection)
- Path: `/`
- Max-Age: 24 hours

---

## Password Reset

### Request Reset

**Frontend**: `/auth/forgot-password`  
**Backend**: `POST /internal/auth/password-reset/request`

**Process**:

1. User enters email
2. Backend generates `secrets.token_urlsafe(32)`
3. Store hash in `PasswordResetToken` (expires in 1 hour)
4. Send email with link: `{FRONTEND_URL}/auth/reset-password?token={token}`
5. Always return success (prevent email enumeration)

### Confirm Reset

**Frontend**: `/auth/reset-password?token=...`  
**Backend**: `POST /internal/auth/password-reset/confirm`

**Process**:

1. User enters new password
2. Backend hashes token, finds valid `PasswordResetToken`
3. Update `user.password_hash = hash_password(new_password)`
4. Mark token as `is_used = True`
5. **Invalidate ALL sessions** (security measure)
6. User must log in again

---

## OAuth Integration

### Supported Providers

- **Google OAuth 2.0**
- **GitHub OAuth**
- **Microsoft Identity Platform**

### OAuth Flow

**Handled in SvelteKit** (`frontend/src/routes/auth/oauth/`):

```text
1. User clicks "Sign in with Google"
2. Redirect to Google OAuth consent screen
3. User authorizes
4. Google redirects: /auth/oauth/callback?code=...
5. Exchange code for access_token
6. Fetch user profile from Google API
7. Call POST /internal/auth/oauth/find-or-create:
   {
     provider: "google",
     provider_id: "1234567890",
     email: "user@gmail.com",
     name: "User Name",
     avatar_url: "https://..."
   }
8. Backend finds or creates user (default role: viewer)
9. Call POST /internal/auth/session/create
10. Set session_id cookie + mint derived JWT
11. Redirect to /
```

**Environment Variables**:

```bash
# Google
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# GitHub
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Microsoft
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
```

---

## Security Features

### 1. Token Security

**Derived JWTs**:

- HS256 symmetric signing
- Separate secret (`DERIVED_JWT_SECRET`)
- 24-hour expiration (not refreshable)
- Rejected on API key-compatible routes

**API Keys**:

- SHA-256 hashed (one-way)
- Prefix for identification (`cr_*****`)
- Optional expiration
- Revocable (`is_active = False`)
- Audit trail (`last_used_at`)

### 2. Password Security

- **Hashing**: bcrypt with 12 rounds
- **Min Length**: 8 characters
- **No Complexity Rules**: Research shows they reduce security
- **Reset Tokens**: One-time use, 1-hour expiration, 32-byte random

### 3. Session Security

- **HttpOnly cookies**: Prevent XSS theft
- **Secure flag**: HTTPS only in production
- **SameSite=Lax**: CSRF protection
- **Expiration**: 24 hours default
- **Invalidation**: On logout, password reset

### 4. RBAC Enforcement

- **Server-side only**: No client-side role checks
- **Every request**: Role verified on each API call
- **403 Forbidden**: Insufficient permissions
- **Browser/CLI separation**: API keys blocked on browser routes

### 5. Audit Trail

**Logged Events**:

- API key usage (timestamp)
- Session creation (IP, user agent)
- Password resets
- Authentication attempts

**Log Format**:

- Structured JSON
- Masked tokens (first 8 + last 8 chars)
- No sensitive data

---

## Environment Variables

**Required**:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/community_resilience
JWT_SECRET_KEY=<random_64_chars>
DERIVED_JWT_SECRET=<random_64_chars>
INTERNAL_AUTH_SECRET=<random_64_chars>
FRONTEND_URL=http://localhost:5173
```

**Optional**:

```bash
# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...

# JWT Config
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# API Keys
API_KEY_PREFIX=cr_

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
EMAIL_FROM=noreply@example.com
```

---

## Common Scenarios

### 1. New User Registers (Password)

```text
1. Visit /auth/register → Enter email/password/name
2. POST /internal/auth/register → Create User (role=viewer)
3. Redirect to /auth/login
4. Login (see scenario 2)
```

### 2. User Logs In (Password)

```text
1. Visit /auth/login → Enter email/password
2. POST /internal/auth/verify-password → Returns user_id + role
3. POST /internal/auth/session/create → Returns session_id
4. Set session_id cookie + mint derived JWT
5. Redirect to /
```

### 3. User Logs In (OAuth)

```text
1. Click "Sign in with Google"
2. OAuth flow → Get profile
3. POST /internal/auth/oauth/find-or-create → Find or create user
4. POST /internal/auth/session/create → Returns session_id
5. Set cookie + JWT → Redirect to /
```

### 4. Admin Promotes User to Editor

```text
1. Navigate to /admin/users
2. Click "Edit" on user
3. Select "editor" from dropdown
4. PATCH /admin/users/{id} {role: "editor"}
5. User gets editor permissions on next login
```

### 5. CLI Tool Uses API Key

```text
1. Run seed_admin.py → Get API key
2. Store in .env: ADMIN_API_KEY=cr_...
3. Request with Authorization: Bearer cr_...
4. Backend verifies hash → Loads user → Checks role
5. Request authorized
```

### 6. User Forgets Password

```text
1. Visit /auth/forgot-password → Enter email
2. POST /password-reset/request → Generate token
3. Email sent with reset link
4. Click link → Enter new password
5. POST /password-reset/confirm → Update password + invalidate sessions
6. Redirect to /auth/login
```

---

## Troubleshooting

### "Not authenticated" in browser

**Possible Causes**:

- Session cookie missing/expired
- Derived JWT invalid/expired
- User account deactivated

**Debug**:

1. Check browser cookies for `session_id`
2. Check network tab for `Authorization` header
3. Check backend logs: `auth.derived_only.*`
4. Verify `DERIVED_JWT_SECRET` matches in both .env files

### "API keys are not accepted for this endpoint"

**Cause**: Using API key on browser-only route

**Solution**:

- Browser routes: `require_viewer()` (rejects API keys)
- CLI routes: `require_viewer_or_api_key()` (accepts keys)
- Use correct endpoint for your use case

### "Invalid session" after login

**Possible Causes**:

- `INTERNAL_AUTH_SECRET` mismatch
- Session expired/deleted
- Database connection issue

**Debug**:

1. Verify `INTERNAL_AUTH_SECRET` in both .env files
2. Check logs: `internal.session.validate.*`
3. Query `sessions` table directly

### User promoted but still viewer permissions

**Cause**: Old JWT still in use (hasn't expired yet)

**Solution**:

- Log out and log back in (gets new JWT with new role)
- Or wait for JWT to expire (24 hours default)

---

## API Reference

**Internal Auth Endpoints** (`/internal/auth/*`):

- `POST /internal/auth/verify-password` - Verify email/password
- `POST /internal/auth/verify-totp` - Verify 2FA code
- `POST /internal/auth/session/create` - Create session
- `POST /internal/auth/session/validate` - Validate session
- `POST /internal/auth/session/delete` - Logout
- `POST /internal/auth/oauth/find-or-create` - OAuth user creation
- `POST /internal/auth/password-reset/request` - Request password reset
- `POST /internal/auth/password-reset/confirm` - Confirm password reset

**Admin Endpoints** (`/admin/*`):

- `GET /admin/users?limit=100` - List users (admin only)
- `PATCH /admin/users/{user_id}` - Update user role/status (admin only)
- `DELETE /admin/users/{user_id}` - Delete user (admin only)

---

## Further Reading

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SvelteKit Hooks](https://kit.svelte.dev/docs/hooks)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Auth Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
