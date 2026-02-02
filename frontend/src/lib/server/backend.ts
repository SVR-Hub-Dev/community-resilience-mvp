/**
 * Server-only module for calling FastAPI internal auth endpoints.
 * This module should only be imported in server-side code (+page.server.ts, +server.ts, hooks.server.ts).
 */

import { env } from '$env/dynamic/private';

const API_URL = env.API_URL || 'http://localhost:8000';
const INTERNAL_AUTH_SECRET = env.INTERNAL_AUTH_SECRET;

// Type definitions for API responses
export interface UserInfo {
	id: number;
	email: string | null;
	role: string | null;
}

export interface PasswordVerifyResult {
	success: boolean;
	user_id?: number;
	email?: string;
	role?: string;
	totp_required: boolean;
	totp_token?: string;
}

export interface SessionCreateResult {
	session_id: string;
}

export interface SessionDeleteResult {
	deleted: boolean;
}

export interface OAuthUserResult {
	user_id: number;
	email: string;
	role: string;
	created: boolean;
}

class BackendError extends Error {
	constructor(
		message: string,
		public status: number
	) {
		super(message);
		this.name = 'BackendError';
	}
}

async function internalFetch<T>(endpoint: string, body: unknown): Promise<T> {
	if (!INTERNAL_AUTH_SECRET) {
		throw new BackendError('INTERNAL_AUTH_SECRET not configured', 500);
	}

	const url = `${API_URL}/internal/auth${endpoint}`;

	const response = await fetch(url, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-Internal-Secret': INTERNAL_AUTH_SECRET
		},
		body: JSON.stringify(body)
	});

	if (!response.ok) {
		const errorText = await response.text().catch(() => 'Unknown error');
		throw new BackendError(`Backend error: ${response.status} - ${errorText}`, response.status);
	}

	return response.json();
}

export const backend = {
	/**
	 * Verify email/password credentials.
	 * Returns user info if valid, or TOTP challenge if 2FA is enabled.
	 */
	async verifyPassword(email: string, password: string): Promise<PasswordVerifyResult> {
		return internalFetch<PasswordVerifyResult>('/verify-password', { email, password });
	},

	/**
	 * Verify TOTP code after password verification.
	 * Returns user info if valid.
	 */
	async verifyTotp(totpToken: string, code: string): Promise<PasswordVerifyResult> {
		return internalFetch<PasswordVerifyResult>('/verify-totp', {
			totp_token: totpToken,
			code
		});
	},

	/**
	 * Create a session for the given user.
	 * Returns the session_id to be stored in a cookie.
	 */
	async createSession(userId: number, ttlSeconds = 604800): Promise<SessionCreateResult> {
		return internalFetch<SessionCreateResult>('/session/create', {
			user_id: userId,
			ttl_seconds: ttlSeconds
		});
	},

	/**
	 * Validate a session and return the associated user.
	 * Throws if session is invalid or expired.
	 */
	async validateSession(sessionId: string): Promise<UserInfo> {
		return internalFetch<UserInfo>('/session/validate', { session_id: sessionId });
	},

	/**
	 * Delete a session (logout).
	 */
	async deleteSession(sessionId: string): Promise<SessionDeleteResult> {
		return internalFetch<SessionDeleteResult>('/session/delete', { session_id: sessionId });
	},

	/**
	 * Find or create a user from OAuth identity.
	 */
	async oauthFindOrCreate(data: {
		provider: string;
		provider_id: string;
		email: string;
		name: string;
		avatar_url?: string;
	}): Promise<OAuthUserResult> {
		return internalFetch<OAuthUserResult>('/oauth/find-or-create', data);
	},

	/**
	 * Request a password reset email for the given email address.
	 */
	async requestPasswordReset(email: string): Promise<void> {
		return internalFetch<void>('/password-reset/request', { email });
	},

	/**
	 * Reset password using a reset token.
	 */
	async resetPassword(token: string, newPassword: string): Promise<void> {
		return internalFetch<void>('/password-reset/confirm', { token, new_password: newPassword });
	}
};

export { BackendError };
