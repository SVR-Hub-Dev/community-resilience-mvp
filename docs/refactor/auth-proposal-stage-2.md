# Authentication Proposal (Stage 2)

## Safe Migration Path to SvelteKit + better-auth

**Status:** Design Proposal  
**Prerequisite:** Stage 1 – Normalized Auth Model  
**Scope:** Incremental, reversible migration  
**Constraint:** No downtime, no FastAPI breakage

---

## 1. Purpose of This Document

This document defines a **safe, incremental migration path** from the current
authentication implementation to a **SvelteKit-centered auth authority using better-auth**.

The migration is designed to be:

- Non-breaking
- Reversible at each step
- Testable locally
- Deployable gradually to cloud environments

---

## 2. Migration Principles

### 2.1 Invariants (Must Always Hold)

- `User`, `Session`, and `APIKey` tables remain valid
- RBAC semantics do not change
- Existing users can continue to log in
- FastAPI endpoints remain callable
- Offline login remains possible

### 2.2 One-Way Doors to Avoid

- Replacing sessions with stateless JWTs prematurely
- Moving OAuth callbacks into FastAPI
- Sharing cookies across services
- Making OAuth mandatory for any user

---

## 3. Migration Overview (High-Level)

```text
Current State
 ├─ Mixed auth responsibilities
 ├─ Tokens in localStorage / cookies
 ├─ OAuth complexity
 └─ FastAPI partially auth-aware

↓ (Incremental steps)

Target State
 ├─ SvelteKit = auth authority
 ├─ better-auth manages sessions
 ├─ FastAPI = resource server
 └─ Clear internal token boundary
```

Each step below can be deployed independently.

---

## 4. Step-by-Step Migration Plan

### Step 0 — Baseline & Observability (No Behavior Change)

**Goal:** Prepare the system for safe refactoring.

Actions:

- Document current login flows
- Identify where sessions/tokens are created
- Add logging around:
  - login success/failure
  - session creation
  - token validation

Rollback: Not required (read-only changes).

---

### Step 1 — Centralize Session Validation in SvelteKit

**Goal:** Make SvelteKit the *consumer* of session state.

Actions:

- Ensure `hooks.server.ts` validates sessions on every request
- Populate `locals.user` exclusively from session data
- Remove client-side auth state assumptions

FastAPI:

- Continues validating existing tokens
- No behavior change yet

Rollback:

- Restore previous auth checks

---

### Step 2 — Shift Session Ownership to SvelteKit

**Goal:** Make SvelteKit the *producer* of sessions.

Actions:

- Route all browser logins through SvelteKit
- On successful login:
  - Create `Session` records
  - Set HTTP-only session cookies
- Disable session creation in FastAPI (if present)

FastAPI:

- Treats sessions as opaque / external

Rollback:

- Re-enable FastAPI session creation if needed

---

### Step 3 — Introduce Derived Internal Tokens

**Goal:** Decouple browser sessions from backend APIs.

Actions:

- After validating a session, mint a short-lived JWT:
  - `sub = user.id`
  - `role`
  - short expiry
- Send token via `Authorization: Bearer` to FastAPI
- Implement verification middleware in FastAPI

FastAPI:

- Accepts derived tokens
- Continues accepting existing mechanisms during transition

Rollback:

- Disable derived token usage
- Fall back to existing auth headers

---

### Step 4 — Narrow API Key Responsibilities

**Goal:** Prevent misuse of API keys.

Actions:

- Audit current API key usage
- Restrict API keys to:
  - automation
  - CLI tools
  - external integrations
- Remove API keys from browser or internal flows

Rollback:

- Temporarily re-allow broader scopes if needed

---

### Step 5 — Normalize OAuth Entry via SvelteKit

**Goal:** Eliminate cross-domain OAuth issues.

Actions:

- Move all OAuth callbacks into SvelteKit
- Link OAuth identities to existing users
- Ensure OAuth login results in standard sessions

FastAPI:

- Never handles OAuth callbacks
- Never sees OAuth tokens

Rollback:

- Disable OAuth providers without affecting baseline login

---

### Step 6 — Enforce better-auth as the Auth Interface

**Goal:** Consolidate auth logic.

Actions:

- Replace custom auth utilities with better-auth APIs
- Align password, session, and MFA flows
- Retire legacy token storage patterns

Rollback:

- Temporarily bridge legacy auth utilities

---

## 5. Offline Safety During Migration

At every step:

- Email/password login remains functional
- Existing sessions remain valid
- OAuth is additive, never required
- Local Docker deployments continue to work

Offline capability is preserved by design.

---

## 6. Validation Checklist (Per Step)

Before moving to the next step:

- Existing users can log in
- New users can log in
- Sessions persist across reloads
- RBAC checks behave identically
- FastAPI endpoints still authorize correctly
- OAuth failure does not block access

---

## 7. End State Characteristics

After completing Stage 2:

- Auth logic is centralized
- Cross-domain cookie issues are eliminated
- FastAPI is security-simpler
- better-auth is the single auth abstraction
- The system is ready for future enhancements

---

## 8. Deferred Work (Explicitly Out of Scope)

- OAuth multi-provider tables
- Passkeys / WebAuthn
- Session sharding
- Multi-tenant auth
- External IdP federation

---

## 9. Outcome of Stage 2

This migration path ensures:

- Low risk
- Clear rollback points
- No forced big-bang rewrite
- Compatibility with both local and cloud deployments

---

**Next document:**  
*Stage 3 — Auth Flow Diagrams (Local vs Online) Using Existing Tables*
