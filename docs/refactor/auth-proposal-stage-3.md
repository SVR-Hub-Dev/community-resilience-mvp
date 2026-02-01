# Authentication Proposal (Stage 3)

## Auth Flow Diagrams (Local vs Online) Using Existing Tables

**Status:** Design Specification  
**Prerequisites:**  

- Stage 1 – Normalized Auth Model  
- Stage 2 – Safe Migration Path  

**Scope:** Runtime authentication and authorization flows  
**Audience:** Backend / full-stack developers, future maintainers

---

## 1. Purpose of This Document

This document **explicitly sketches authentication and authorization flows**
using the **existing database tables**:

- `users`
- `sessions`
- `api_keys`

It contrasts:

- **Local / Offline authentication**
- **Online / OAuth-enhanced authentication**

The goal is to make it unambiguous:

- Which service is responsible at each step
- Which tables are read or written
- Where trust boundaries exist

---

## 2. Common Concepts Used in All Flows

### 2.1 Canonical Identity

- Identity is always a `User`
- `users.id` is the ultimate authority
- `email` is the human-facing anchor

Authentication method does **not** change identity.

---

### 2.2 Session Semantics

- A session represents a browser login
- Stored in the `sessions` table
- Referenced by an HTTP-only cookie
- Validated on **every request** by SvelteKit

---

### 2.3 Service Trust Boundary

| Boundary | Mechanism |
| ------ | --------- |
| Browser → SvelteKit | HTTP-only session cookie |
| SvelteKit → FastAPI | Short-lived Bearer token |
| External systems | API keys |

Cookies never cross service boundaries.

---

## 3. Flow A — Local / Offline Login (Email + Password [+ TOTP])

### Preconditions

- Internet unavailable or irrelevant
- User exists in `users`
- `password_hash` is set

---

### Step-by-Step Flow

```text
Browser
  │
  │ 1. POST /login (email, password)
  ▼
SvelteKit
  │
  │ 2. Verify password_hash
  │ 3. (Optional) Verify TOTP
  │
  │ 4. Create session
  │
  ▼
Database
  ├─ users      (READ)
  └─ sessions   (INSERT)
```

---

### Result

- HTTP-only session cookie set
- `locals.user` populated
- User is authenticated offline

---

### Tables Touched

| Table | Operation |
| --- | --------- |
| `users` | SELECT |
| `sessions` | INSERT |

---

## 4. Flow B — Authenticated Request (Browser → FastAPI)

This flow is identical **online or offline**.

---

### Flow B Step-by-Step Flow

```text
Browser
  │
  │ 1. Request page / action
  ▼
SvelteKit
  │
  │ 2. Validate session cookie
  │ 3. Load user + role
  │
  │ 4. Mint derived token
  │
  ▼
FastAPI
  │
  │ 5. Validate token
  │ 6. Enforce RBAC
```

---

### Flow B Tables Touched

| Table | Operation |
| --- | --------- |
| `sessions` | SELECT |
| `users` | SELECT |
| `api_keys` | (Not used) |

---

## 5. Flow C — Online Login via OAuth

### Flow C Preconditions

- Internet available
- OAuth provider enabled
- OAuth provider returns `(provider, provider_id, email)`

---

### Flow C Step-by-Step Flow

```text
Browser
  │
  │ 1. Redirect to OAuth provider
  ▼
OAuth Provider
  │
  │ 2. User authenticates
  ▼
SvelteKit (callback)
  │
  │ 3. Resolve or create user
  │ 4. Link oauth_provider / oauth_id
  │ 5. Create session
  │
  ▼
Database
  ├─ users      (SELECT / INSERT / UPDATE)
  └─ sessions   (INSERT)
```

---

### User Resolution Logic

1. Match on `(oauth_provider, oauth_id)`
2. Else match on `email`
3. Else create new user

Password and TOTP remain valid even if OAuth is used.

---

### Flow C Tables Touched

| Table | Operation |
| --- | --------- |
| `users` | SELECT / INSERT / UPDATE |
| `sessions` | INSERT |

---

## 6. Flow D — OAuth Unavailable (Graceful Degradation)

If OAuth fails:

- No session is created
- Email/password login remains available
- Existing sessions remain valid

**No special-case logic required.**

---

## 7. Flow E — Logout

### Flow E Step-by-Step Flow

```text
Browser
  │
  │ 1. POST /logout
  ▼
SvelteKit
  │
  │ 2. Delete session
  ▼
Database
  └─ sessions (DELETE)
```

---

### Flow E  Result

- Cookie cleared
- Session invalidated
- Tokens minted from this session become invalid

---

## 8. Flow F — API Key Authentication (Non-Browser)

### Flow F Preconditions

- API key created
- Used outside browser context

---

### Flow F Step-by-Step Flow

```text
Client / Script
  │
  │ Authorization: ApiKey <key>
  ▼
FastAPI
  │
  │ 1. Hash + lookup key
  │ 2. Enforce scopes
```

---

### Flow F Tables Touched

| Table | Operation |
| --- | --------- |
| `api_keys` | SELECT |
| `users` | SELECT |

Sessions are **not involved**.

---

## 9. Comparative Summary

| Flow | Offline | OAuth | Sessions | API Keys |
| -- | ------ | ----- | -------- | -------- |
| Local Login | ✅ | ❌ | ✅ | ❌ |
| OAuth Login | ❌ | ✅ | ✅ | ❌ |
| Browser Request | ✅ | Optional | ✅ | ❌ |
| Automation | ✅ | ❌ | ❌ | ✅ |

---

## 10. Design Guarantees

This design guarantees:

- Single identity model
- Predictable offline behavior
- OAuth never blocks access
- Clear trust boundaries
- Minimal surface for auth bugs

---

## 11. Outcome of Stage 3

After this stage:

- Auth behavior is fully documented
- Table usage is explicit
- Future contributors can reason about flows
- Migration and implementation risk is reduced

---

<!-- markdownlint-disable MD036 -->
**End of Proposal Series**
