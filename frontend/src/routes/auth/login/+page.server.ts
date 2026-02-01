import { fail, redirect } from '@sveltejs/kit';
import { dev } from '$app/environment';
import type { Actions, PageServerLoad } from './$types';
import { backend, BackendError } from '$lib/server/backend';

const SESSION_COOKIE_NAME = 'session_id';
const SESSION_TTL_SECONDS = 7 * 24 * 60 * 60; // 7 days

export const load: PageServerLoad = async ({ locals }) => {
	// Redirect if already logged in
	if (locals.user) {
		throw redirect(302, '/');
	}
	return {};
};

export const actions: Actions = {
	login: async ({ request, cookies }) => {
		const data = await request.formData();
		const email = data.get('email')?.toString();
		const password = data.get('password')?.toString();

		if (!email || !password) {
			return fail(400, {
				error: 'Email and password are required',
				email: email || ''
			});
		}

		try {
			const result = await backend.verifyPassword(email, password);

			if (!result.success) {
				return fail(401, {
					error: 'Invalid email or password',
					email
				});
			}

			// Check if TOTP is required
			if (result.totp_required && result.totp_token) {
				return {
					requiresTotp: true,
					totpToken: result.totp_token,
					email
				};
			}

			// Create session and set cookie
			if (result.user_id) {
				const { session_id } = await backend.createSession(result.user_id, SESSION_TTL_SECONDS);

				cookies.set(SESSION_COOKIE_NAME, session_id, {
					path: '/',
					httpOnly: true,
					secure: !dev,
					sameSite: 'lax',
					maxAge: SESSION_TTL_SECONDS
				});

				throw redirect(302, '/');
			}

			return fail(500, {
				error: 'Login failed unexpectedly',
				email
			});
		} catch (err) {
			if (err instanceof Response) {
				// This is a redirect, re-throw it
				throw err;
			}
			if (err instanceof BackendError) {
				console.error('Backend error during login:', err.message);
				return fail(500, {
					error: 'Unable to connect to authentication service',
					email
				});
			}
			console.error('Unexpected error during login:', err);
			return fail(500, {
				error: 'An unexpected error occurred',
				email
			});
		}
	},

	verifyTotp: async ({ request, cookies }) => {
		const data = await request.formData();
		const totpToken = data.get('totp_token')?.toString();
		const code = data.get('code')?.toString();
		const email = data.get('email')?.toString() || '';

		if (!totpToken || !code) {
			return fail(400, {
				error: 'Verification code is required',
				requiresTotp: true,
				totpToken: totpToken || '',
				email
			});
		}

		try {
			const result = await backend.verifyTotp(totpToken, code);

			if (!result.success) {
				return fail(401, {
					error: 'Invalid verification code',
					requiresTotp: true,
					totpToken,
					email
				});
			}

			// Create session and set cookie
			if (result.user_id) {
				const { session_id } = await backend.createSession(result.user_id, SESSION_TTL_SECONDS);

				cookies.set(SESSION_COOKIE_NAME, session_id, {
					path: '/',
					httpOnly: true,
					secure: !dev,
					sameSite: 'lax',
					maxAge: SESSION_TTL_SECONDS
				});

				throw redirect(302, '/');
			}

			return fail(500, {
				error: 'Login failed unexpectedly',
				requiresTotp: true,
				totpToken,
				email
			});
		} catch (err) {
			if (err instanceof Response) {
				throw err;
			}
			if (err instanceof BackendError) {
				console.error('Backend error during TOTP verification:', err.message);
				return fail(500, {
					error: 'Unable to connect to authentication service',
					requiresTotp: true,
					totpToken: totpToken || '',
					email
				});
			}
			console.error('Unexpected error during TOTP verification:', err);
			return fail(500, {
				error: 'An unexpected error occurred',
				requiresTotp: true,
				totpToken: totpToken || '',
				email
			});
		}
	}
};
