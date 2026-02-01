# Authentication Architecture

## Overview

This document describes the server-side authentication architecture implemented for the Community Resilience platform.

### Key Principles

1. **SvelteKit is the sole auth authority** - All authentication flows (login, OAuth, session management) are handled by SvelteKit
2. **FastAPI is a resource server only** - It validates derived JWTs minted by SvelteKit but does not manage authentication
3. **HTTP-only session cookies** - Browser sessions use secure HTTP-only cookies, never exposing tokens to JavaScript
4. **API keys for CLI/automation** - API keys are restricted to non-browser routes for programmatic access

---

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                              Browser                                     │
│  ┌─────────────────┐                           ┌──────────────────────┐ │
│  │   Login Form    │──────────────────────────▶│  SvelteKit Server    │ │
│  │   OAuth Button  │   Form POST / OAuth       │  (Auth Authority)    │ │
│  └─────────────────┘                           └──────────┬───────────┘ │
│                                                           │             │
│                     HTTP-only session_id cookie           │             │
│  ◀────────────────────────────────────────────────────────┘             │
│                                                                         │
│  ┌─────────────────┐   Derived JWT in           ┌──────────────────────┐│
│  │  Page Request   │   Authorization header     │     FastAPI          ││
│  │  (SSR/API)      │──────────────────────────▶│  (Resource Server)   ││
│  └─────────────────┘   (minted by SvelteKit)    └──────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI / Automation                               │
│  ┌─────────────────┐   API Key (cr_xxx)         ┌──────────────────────┐│
│  │  API Request    │──────────────────────────▶│     FastAPI          ││
│  │                 │                            │  (Resource Server)   ││
│  └─────────────────┘                            └──────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flows

### Email/Password Login

1. User submits login form to `/auth/login` (SvelteKit form action)
2. SvelteKit calls FastAPI internal endpoint `/internal/auth/verify-password`
3. If TOTP required, SvelteKit shows TOTP form
4. On success, SvelteKit calls `/internal/auth/session/create`
5. SvelteKit sets HTTP-only `session_id` cookie
6. User is redirected to home page

### OAuth Login (Google/GitHub)

1. User clicks OAuth button, redirected to `/auth/[provider]`
2. SvelteKit generates state, stores in cookie, redirects to provider
3. Provider authenticates user, redirects to `/auth/[provider]/callback`
4. SvelteKit:
   - Verifies state matches cookie
   - Exchanges code for access token (direct to provider)
   - Fetches user info from provider
   - Calls FastAPI `/internal/auth/oauth/find-or-create`
   - Creates session, sets cookie
5. User is redirected to home page

### Session Validation

1. Browser makes request to any SvelteKit page
2. `hooks.server.ts` reads `session_id` cookie
3. Calls FastAPI `/internal/auth/session/validate`
4. Sets `event.locals.user` with validated user data
5. Page loads with `$page.data.user` available

### API Calls (Browser → FastAPI)

1. SvelteKit server receives page/API request
2. If `locals.user` exists, mints a short-lived derived JWT
3. Derived JWT sent to FastAPI in `Authorization: Bearer` header
4. FastAPI validates JWT signature and expiry
5. FastAPI rejects requests using API keys on browser-facing routes

### Logout

1. User clicks logout, navigated to `/logout`
2. SvelteKit reads `session_id` from cookie
3. Calls FastAPI `/internal/auth/session/delete`
4. Clears `session_id` cookie
5. Redirects to login page

---

## File Structure

### Backend (FastAPI)

```text
backend/auth/
├── __init__.py           # Exports all auth components
├── dependencies.py       # Auth dependencies for routes
├── derived.py           # Derived JWT verification
├── models.py            # User, Session, APIKey models
├── router.py            # Auth endpoints
├── schemas.py           # Request/response schemas
└── service.py           # Auth business logic
```

### Frontend (SvelteKit)

```text
frontend/src/
├── app.d.ts             # Type definitions (App.Locals)
├── hooks.server.ts      # Session validation middleware
├── lib/
│   ├── auth.svelte.ts   # Auth helper utilities
│   ├── server/
│   │   └── backend.ts   # Internal API client
│   └── types.ts         # Shared types
└── routes/
    ├── +layout.server.ts    # Provides user to all pages
    ├── +layout.svelte       # Uses $page.data.user
    ├── auth/
    │   ├── login/
    │   │   ├── +page.server.ts   # Login form actions
    │   │   └── +page.svelte      # Login UI
    │   ├── register/
    │   │   ├── +page.server.ts   # Registration form action
    │   │   └── +page.svelte      # Registration UI
    │   └── [provider]/
    │       ├── +server.ts        # OAuth initiation
    │       └── callback/
    │           └── +server.ts    # OAuth callback
    └── logout/
        └── +server.ts            # Logout handler
```

---

## Backend Endpoints

### Internal Endpoints (SvelteKit → FastAPI)

These endpoints require `X-Internal-Secret` header matching `INTERNAL_AUTH_SECRET`.

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/internal/auth/verify-password` | POST | Validate email/password |
| `/internal/auth/verify-totp` | POST | Validate TOTP code |
| `/internal/auth/session/create` | POST | Create new session |
| `/internal/auth/session/validate` | POST | Validate existing session |
| `/internal/auth/session/delete` | POST | Delete session (logout) |
| `/internal/auth/oauth/find-or-create` | POST | Find or create OAuth user |

### Public Endpoints

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/auth/register` | POST | Register new user |
| `/auth/me` | GET | Get current user info |

---

## Dependencies

### Browser-Only Dependencies (No API Keys)

These reject requests using API keys, only accepting derived JWTs from SvelteKit:

```python
from auth.dependencies import require_admin, require_editor, require_viewer

@router.get("/protected")
async def protected_route(user: User = Depends(require_viewer)):
    return {"user": user.email}
```

### CLI/Automation Dependencies (API Keys Allowed)

These accept both API keys and derived JWTs:

```python
from auth.dependencies import require_admin_or_api_key, require_editor_or_api_key, require_viewer_or_api_key

@router.post("/api/documents")
async def create_document(user: User = Depends(require_editor_or_api_key)):
    return {"created_by": user.email}
```

---

## Environment Variables

### Backend (.env)

```bash
# Internal authentication secret (shared with frontend)
INTERNAL_AUTH_SECRET=<generate-random-secret>

# JWT configuration
JWT_SECRET=<generate-random-secret>
JWT_ALGORITHM=HS256

# Database
DATABASE_URL=postgresql://user:pass@localhost/db
```

### Frontend (.env)

```bash
# Backend URL
API_URL=http://localhost:8000

# Internal authentication secret (same as backend)
INTERNAL_AUTH_SECRET=<same-as-backend>

# OAuth providers (optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
```

---

## Security Considerations

### Session Cookie Security

- `httpOnly: true` - Not accessible via JavaScript
- `secure: true` (production) - Only sent over HTTPS
- `sameSite: 'lax'` - CSRF protection
- 7-day expiration with server-side session validation

### Derived JWT Security

- Short-lived (5 minute expiration)
- Only minted by SvelteKit server, never exposed to browser
- Signed with shared `INTERNAL_AUTH_SECRET`

### API Key Isolation

- API keys prefixed with `cr_` for identification
- Browser-facing routes explicitly reject API keys
- Only CLI/automation routes accept API keys

### Internal Endpoint Security

- Protected by `X-Internal-Secret` header
- Only accessible from SvelteKit server
- Should not be exposed to public internet in production

---

## OAuth Provider Setup

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Set authorized redirect URI:
   a. `https://yourdomain.com/auth/google/callback` - (`https://your-app.vercel.app/auth/google/callback`)
   b. `http://localhost:5173/auth/google/callback`
4. Copy Client ID and Client Secret to environment variables

### GitHub OAuth

GitHub classic OAuth apps only support one callback URL per app. Create separate apps for development and production:

**Dev App:**

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Name: `your-app-dev`
4. Homepage URL: `http://localhost:5173`
5. Callback URL: `http://localhost:5173/auth/github/callback`
6. Copy Client ID and Client Secret to your local `.env` file

**Prod App:**

1. Click "New OAuth App" again
2. Name: `your-app`
3. Homepage URL: `https://your-app.vercel.app`
4. Callback URL: `https://your-app.vercel.app/auth/github/callback`
5. Add Client ID and Client Secret to Vercel environment variables

Both apps use the same env var names (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`) - just different values per environment. The code automatically uses the correct credentials based on where it runs.

### Microsoft OAuth

1. Go to [Azure Portal - App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click "New registration"
3. Enter app name and select supported account types:
   - "Accounts in any organizational directory and personal Microsoft accounts" for broadest access
   - "Accounts in this organizational directory only" for single-tenant
4. Set redirect URI:
   a. `https://yourdomain.com/auth/microsoft/callback`- (`https://your-app.vercel.app/auth/microsoft/callback`)
   b. `http://localhost:5173/auth/microsoft/callback`
5. After creation, go to "Certificates & secrets" → "New client secret"
6. Copy Application (client) ID and the client secret value to environment variables

**Note:** Microsoft uses different token/userinfo endpoints depending on tenant configuration:

- Multi-tenant: `https://login.microsoftonline.com/common/oauth2/v2.0/...`
- Single-tenant: `https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/...`

---

## Frontend Usage

### Accessing User Data

```svelte
<script lang="ts">
  import { page } from '$app/stores';
  import { getAuthHelpers } from '$lib/auth.svelte';

  // Reactive auth state from server-provided user data
  let auth = $derived(getAuthHelpers($page.data.user));
</script>

{#if auth.isAuthenticated}
  <p>Welcome, {auth.user.name}</p>
  {#if auth.isAdmin}
    <a href="/admin">Admin Panel</a>
  {/if}
{:else}
  <a href="/auth/login">Sign In</a>
{/if}
```

### Form Actions (Login/Register)

```svelte
<script lang="ts">
  import { enhance } from '$app/forms';

  let isLoading = $state(false);
</script>

<form method="POST" use:enhance={() => {
  isLoading = true;
  return async ({ update }) => {
    isLoading = false;
    await update();
  };
}}
  <input type="email" name="email" required />
  <input type="password" name="password" required />
  <button type="submit" disabled={isLoading}>
    {isLoading ? 'Signing in...' : 'Sign In'}
  </button>
</form>
```

### Frontend Logout

```svelte
<script lang="ts">
  function handleLogout() {
    window.location.href = '/logout';
  }
</script>

<button onclick={handleLogout}>Sign Out</button>
```

---

## Testing Checklist

- [ ] Email/password login
- [ ] TOTP verification (if enabled)
- [ ] Registration with auto-login
- [ ] Session persistence across page refreshes
- [ ] Logout clears session
- [ ] Expired session redirects to login
- [ ] OAuth login (Google)
- [ ] OAuth login (GitHub)
- [ ] OAuth login (Microsoft)
- [ ] OAuth account linking (same email)
- [ ] API key authentication (CLI only)
- [ ] API key rejection on browser routes
- [ ] Role-based access control
- [ ] Protected route redirects when unauthenticated

---

## Migration from Legacy Auth

The legacy client-side authentication has been deprecated. If migrating:

1. Remove localStorage token storage
2. Replace `getAuthState()` with `getAuthHelpers($page.data.user)`
3. Convert client-side API calls to form actions
4. Use `window.location.href = '/logout'` instead of `clearAuth()`
5. Remove any `Authorization` header logic from browser code
