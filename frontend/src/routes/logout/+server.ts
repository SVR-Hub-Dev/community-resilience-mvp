import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { backend } from '$lib/server/backend';

const SESSION_COOKIE_NAME = 'session_id';

export const GET: RequestHandler = async ({ cookies }) => {
	const sessionId = cookies.get(SESSION_COOKIE_NAME);

	if (sessionId) {
		// Try to delete the session from the backend
		try {
			await backend.deleteSession(sessionId);
		} catch (err) {
			// Log but don't fail - we still want to clear the cookie
			console.error('Failed to delete session from backend:', err);
		}
	}

	// Always clear the session cookie
	cookies.delete(SESSION_COOKIE_NAME, { path: '/' });

	// Redirect to login page
	throw redirect(302, '/auth/login');
};

export const POST: RequestHandler = async ({ cookies }) => {
	// Support POST as well for form submissions
	const sessionId = cookies.get(SESSION_COOKIE_NAME);

	if (sessionId) {
		try {
			await backend.deleteSession(sessionId);
		} catch (err) {
			console.error('Failed to delete session from backend:', err);
		}
	}

	cookies.delete(SESSION_COOKIE_NAME, { path: '/' });
	throw redirect(302, '/auth/login');
};
