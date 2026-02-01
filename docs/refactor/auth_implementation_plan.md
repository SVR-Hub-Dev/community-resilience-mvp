# Comprehensive Authentication Implementation Plan

This document translates the **Stage 1–3 Authentication Proposals** into an executable, implementation-ready plan. It is designed to be followed sequentially and respects all architectural invariants defined in the proposals.

---

## 0. Non‑Negotiable Invariants

These rules must hold at all times:

- **Canonical identity** is `users.id`
- **SvelteKit is the sole auth authority**
- **FastAPI is a resource server only**
- **Browser auth uses sessions, not tokens**
- **Internal service calls use derived JWTs**
- **API keys are never used by browsers**
- **Offline mode never changes auth logic**

Any implementation violating these invariants is incorrect by design.

---

## 1. FastAPI Responsibilities (Minimal Surface)

### 1.1 Derived JWT Verification

Implement a single authentication middleware/dependency that:

- Accepts `Authorization: Bearer <jwt>`
- Verifies signature, expiry, and issuer
- Extracts:
  - `sub` → user id
  - `role`
  - optional scopes

Constraints:

- No cookies
- No session lookup
- No token minting

This middleware enforces RBAC and nothing else.

---

### 1.2 API Key Authentication (Isolated)

Preserve the existing API key mechanism with **strict scoping**:

- Allowed only for:
  - CLI tools
  - automation
  - external integrations
- Explicitly disallowed for:
  - browser requests
  - SvelteKit → FastAPI calls

---

## 2. SvelteKit as Auth Authority

### 2.1 better-auth Initialization

Create a single server-side auth module that:

- Configures better-auth
- Enables email/password auth
- Enables optional TOTP
- Enables OAuth providers (additive only)
- Persists sessions in the existing `sessions` table

No frontend code imports this module directly.

---

### 2.2 Global Session Resolution (`hooks.server.ts`)

On **every request**:

1. Validate the session via better-auth
2. Load the associated `User`
3. Populate:

```ts
locals.user = {
  id,
  email,
  role
}
```

If the session is invalid:

- `locals.user` is undefined
- Protected routes fail closed

This makes SvelteKit the single consumer and interpreter of session state.

---

## 3. Frontend Authentication Flows (Server‑First)

### 3.1 Email / Password (+ TOTP) Login

- Implemented as **server actions**
- No client-side auth state

Flow:

1. Browser submits credentials
2. Server verifies password
3. Server verifies TOTP if enabled
4. Session is created
5. HTTP-only cookie is set
6. User is redirected

---

### 3.2 OAuth Login (Online Only)

Flow:

1. Server initiates OAuth redirect
2. Provider authenticates user
3. SvelteKit callback:
   - Resolve user by `(provider, provider_id)`
   - Else by `email`
   - Else create user
4. Create standard session

Failure behavior:

- No session created
- Email/password login remains available

---

### 3.3 Logout

- Implemented as a server action
- Deletes the session record
- Clears the cookie
- Redirects

---

## 4. SvelteKit → FastAPI Communication

### 4.1 Derived Token Minting

After session validation:

- Mint a **short-lived JWT** containing:
  - `sub = user.id`
  - `role`
  - short expiration

Rules:

- Tokens are server-only
- Never exposed to the browser

---

### 4.2 Server-Side Fetch Wrapper

Create a server-only helper that:

1. Requires `locals.user`
2. Attaches `Authorization: Bearer <derived token>`
3. Calls FastAPI

This preserves the browser → SvelteKit → FastAPI trust boundary.

---

## 5. Offline Mode Guarantees

Offline capability requires **no special logic**:

- Email/password auth works offline
- TOTP works offline
- Sessions remain valid
- OAuth is skipped automatically

Offline and online paths share identical authorization logic.

---

## 6. Safe Migration Execution Order

Execute strictly in order:

1. Add logging and observability only
2. Centralize session validation in SvelteKit
3. Shift session creation to SvelteKit
4. Introduce derived JWTs (dual-accept temporarily)
5. Restrict API key usage
6. Move OAuth callbacks into SvelteKit
7. Remove legacy auth utilities

Each step is:

- Independently deployable
- Reversible
- Testable locally

---

## 7. Explicit Non‑Goals

This plan intentionally does **not** include:

- Schema migrations
- Identity table splits
- Stateless sessions
- Passkeys / WebAuthn
- Multi-tenant auth

These remain deferred by design.

---

## 8. End State

When complete:

- Authentication authority is unambiguous
- Offline and online behavior converge
- FastAPI’s security surface is minimal
- better-auth is the single abstraction
- Future auth evolution is unblocked

---

**Document status:** Implementation-ready

---

## Appendix A: Execution Checklists by Migration Phase

The following checklists decompose the migration into concrete, verifiable steps. Each phase is **deployable independently** and should be completed in order.

---

### Phase 0 — Baseline & Observability (No Behavior Change)

**Goal:** Gain confidence and visibility without changing auth behavior.

Checklist:

- [ ] Add structured logging around existing auth entry points
- [ ] Log session creation, validation, and destruction events
- [ ] Log API key usage with route + caller metadata
- [ ] Add request correlation IDs (if not already present)
- [ ] Deploy with zero user-visible changes

Exit criteria:

- You can answer: *who authenticated, how, and where* for any request

---

### Phase 1 — Centralize Session Validation in SvelteKit

**Goal:** Make SvelteKit the sole interpreter of session state.

Checklist:

- [ ] Implement `hooks.server.ts` session resolution
- [ ] Integrate better-auth session validation
- [ ] Populate `locals.user` on every request
- [ ] Ensure protected routes fail closed when `locals.user` is undefined
- [ ] Remove direct session reads from page/server code

Exit criteria:

- All authorization decisions in SvelteKit depend only on `locals.user`

---

### Phase 2 — Shift Session Creation to SvelteKit

**Goal:** Ensure all sessions are minted in one place.

Checklist:

- [ ] Implement email/password login as server actions
- [ ] Implement optional TOTP verification
- [ ] Ensure sessions are created only via better-auth
- [ ] Remove legacy login/session creation paths
- [ ] Verify logout deletes session records and cookies

Exit criteria:

- No code outside SvelteKit can create or mutate sessions

---

### Phase 3 — Introduce Derived JWTs (Dual-Accept)

**Goal:** Decouple FastAPI from session storage.

Checklist:

- [ ] Define derived JWT claim schema (`sub`, `role`, `exp`)
- [ ] Implement JWT minting in SvelteKit (server-only)
- [ ] Add FastAPI JWT verification middleware
- [ ] Allow FastAPI to accept *both* legacy auth and derived JWTs
- [ ] Instrument logs to distinguish auth mechanisms

Exit criteria:

- FastAPI can fully authorize requests using derived JWTs alone

---

### Phase 4 — Lock Down API Keys

**Goal:** Eliminate API keys from browser-facing flows.

Checklist:

- [ ] Audit all API key usage
- [ ] Restrict API keys to explicit routes only
- [ ] Add guards preventing API key auth on browser routes
- [ ] Verify SvelteKit → FastAPI calls never use API keys

Exit criteria:

- API keys are used exclusively for automation and external clients

---

### Phase 5 — Move OAuth Fully into SvelteKit

**Goal:** Normalize OAuth as just another session creation path.

Checklist:

- [ ] Implement OAuth initiation as server actions
- [ ] Implement OAuth callbacks in SvelteKit routes
- [ ] Map OAuth identities to `users.id`
- [ ] Ensure OAuth failure does not block email/password login
- [ ] Remove OAuth handling from FastAPI

Exit criteria:

- FastAPI has zero OAuth awareness

---

### Phase 6 — Remove Legacy Auth Utilities

**Goal:** Reduce system complexity and attack surface.

Checklist:

- [ ] Remove deprecated auth helpers
- [ ] Remove legacy session verification code
- [ ] Remove unused environment variables and secrets
- [ ] Update documentation to reflect final architecture

Exit criteria:

- Only one auth path exists for each flow

---

### Phase 7 — Final Validation

**Goal:** Prove the system is stable, offline-capable, and future-proof.

Checklist:

- [x] Test offline login (email/password + TOTP)
- [x] Test online OAuth login
- [x] Test session expiry and renewal
- [x] Test FastAPI authorization with derived JWTs
- [x] Confirm no auth tokens are exposed to the browser

Exit criteria:

- Auth behavior is identical online and offline (minus OAuth)
- Trust boundaries are explicit and enforced

---

**Status:** Ready for execution
