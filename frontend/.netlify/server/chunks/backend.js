import { b as private_env } from "./shared-server.js";
const API_URL = private_env.API_URL || "http://localhost:8000";
const INTERNAL_AUTH_SECRET = private_env.INTERNAL_AUTH_SECRET;
class BackendError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
    this.name = "BackendError";
  }
}
async function internalFetch(endpoint, body) {
  if (!INTERNAL_AUTH_SECRET) {
    throw new BackendError("INTERNAL_AUTH_SECRET not configured", 500);
  }
  const url = `${API_URL}/internal/auth${endpoint}`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Secret": INTERNAL_AUTH_SECRET
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new BackendError(`Backend error: ${response.status} - ${errorText}`, response.status);
  }
  return response.json();
}
const backend = {
  /**
   * Verify email/password credentials.
   * Returns user info if valid, or TOTP challenge if 2FA is enabled.
   */
  async verifyPassword(email, password) {
    return internalFetch("/verify-password", { email, password });
  },
  /**
   * Verify TOTP code after password verification.
   * Returns user info if valid.
   */
  async verifyTotp(totpToken, code) {
    return internalFetch("/verify-totp", {
      totp_token: totpToken,
      code
    });
  },
  /**
   * Create a session for the given user.
   * Returns the session_id to be stored in a cookie.
   */
  async createSession(userId, ttlSeconds = 604800) {
    return internalFetch("/session/create", {
      user_id: userId,
      ttl_seconds: ttlSeconds
    });
  },
  /**
   * Validate a session and return the associated user.
   * Throws if session is invalid or expired.
   */
  async validateSession(sessionId) {
    return internalFetch("/session/validate", { session_id: sessionId });
  },
  /**
   * Delete a session (logout).
   */
  async deleteSession(sessionId) {
    return internalFetch("/session/delete", { session_id: sessionId });
  },
  /**
   * Find or create a user from OAuth identity.
   */
  async oauthFindOrCreate(data) {
    return internalFetch("/oauth/find-or-create", data);
  },
  /**
   * Request a password reset email for the given email address.
   */
  async requestPasswordReset(email) {
    return internalFetch("/password-reset/request", { email });
  },
  /**
   * Reset password using a reset token.
   */
  async resetPassword(token, newPassword) {
    return internalFetch("/password-reset/confirm", { token, new_password: newPassword });
  }
};
export {
  BackendError as B,
  backend as b
};
