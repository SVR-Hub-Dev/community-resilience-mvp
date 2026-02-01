# Authentication Proposal (Stage 1)

## Normalizing Existing Models for better-auth Compatibility

**Status:** Proposal (Non-breaking)  
**Scope:** Authentication & Authorization Architecture  
**Applies to:** SvelteKit (better-auth) + FastAPI backend  
**Out of scope:** Migration execution, OAuth UX, infra provisioning

---

## 1. Purpose of This Document

This document proposes a **normalized authentication design** that:

- Uses the existing SQLAlchemy models without breaking FastAPI
- Aligns with **better-auth** and modern **SvelteKit server-first architecture**
- Supports:
  - Offline-first local operation
  - Online OAuth-enhanced authentication
  - Secure service-to-service calls
- Establishes a clean separation of concerns

This is a **design-only proposal**. No schema migrations are required at this stage.

---

## 2. Current Backend Models (Authoritative)

The following models are treated as **authoritative inputs**:

- `User`
- `Session`
- `APIKey`

No tables are removed or renamed in this stage.

---

## 3. Normalized Auth Concepts (Conceptual Model)

This proposal introduces **conceptual normalization** without immediate schema changes.

### 3.1 Identity (User)

The `User` table represents a **canonical identity**, regardless of how the user authenticates.

Key properties:

- `email` — identity anchor
- `role` — authorization (RBAC)
- `is_active` — account status

Authentication attributes are **capabilities**, not identity definitions.

---

### 3.2 Authentication Methods (Conceptual)

Authentication methods are **orthogonal** to identity.

| Method | Backing Columns | Availability |
| ---- | -------------- | ------------ |
| Email + Password | `password_hash` | Always |
| TOTP | `totp_secret`, `totp_enabled` | Optional |
| OAuth | `oauth_provider`, `oauth_id` | Online-only |

> OAuth is treated as **linked identity proof**, not as a primary identity.

---

### 3.3 Sessions

The `Session` table represents **browser login state**.

Interpretation:

- A session is created after *any* successful authentication method
- Session validity is enforced server-side
- Sessions are owned and validated by **SvelteKit**, not FastAPI

This aligns directly with better-auth’s session model.

---

### 3.4 API Keys

The `APIKey` table is preserved with a **narrowed responsibility**:

Intended uses:

- CLI tools
- Automation
- External integrations
- Long-lived non-browser access

Explicitly not used for:

- Browser authentication
- OAuth
- SvelteKit ↔ FastAPI internal calls

---

## 4. Service Responsibility Boundaries

### 4.1 SvelteKit (Auth Authority)

SvelteKit is the **sole authentication authority**.

Responsibilities:

- User login (all methods)
- Session creation & invalidation
- Authorization (RBAC)
- OAuth provider integration
- MFA enforcement
- Deriving internal service tokens

---

### 4.2 FastAPI (Resource Server)

FastAPI is a **resource server**, not an auth provider.

Responsibilities:

- Validate derived Bearer tokens
- Enforce RBAC using claims
- Never handle:
  - Cookies
  - OAuth callbacks
  - Passwords
  - Sessions

---

## 5. Internal Authentication (Derived Tokens)

For SvelteKit → FastAPI calls:

- A short-lived JWT is minted after session validation
- Token contains:
  - `sub` (user id)
  - `role`
  - optional scopes
  - short expiration
- Token is sent via `Authorization: Bearer`

This avoids:

- Cookie sharing across domains
- Reusing API keys internally
- OAuth token leakage

---

## 6. Offline vs Online Behavior (Design Invariant)

| Capability | Offline | Online |
| -------- | ------ | ------ |
| Email/Password | ✅ | ✅ |
| TOTP | ✅ | ✅ |
| OAuth | ❌ | ✅ |
| Sessions | ✅ | ✅ |
| Authorization | ✅ | ✅ |

Offline capability is preserved without branching authorization logic.

---

## 7. Non-Breaking Guarantees

This proposal **does not**:

- Require schema migrations
- Break FastAPI endpoints
- Remove OAuth support
- Change RBAC semantics
- Introduce new tables

All changes are **behavioral and architectural**.

---

## 8. Explicit Non-Goals (Stage 1)

- Splitting OAuth identities into a separate table
- Passkeys / WebAuthn
- Session statelessness
- Multi-tenant auth
- Provider-specific UX

These are deferred to later stages.

---

## 9. Outcome of Stage 1

After adopting this proposal:

- Auth responsibilities are clearly owned
- better-auth can be integrated cleanly
- Offline and online behavior is predictable
- FastAPI remains stable and isolated
- Future migration paths are unblocked

---

**Next document:**  
*Stage 2 — Designing a Safe Migration Path (Incremental, Reversible)*  
