import type { Handle } from '@sveltejs/kit';
import { backend } from '$lib/server/backend';

const SESSION_COOKIE_NAME = 'session_id';

export const handle: Handle = async ({ event, resolve }) => {
	const sessionId = event.cookies.get(SESSION_COOKIE_NAME);

	if (sessionId) {
		try {
			const user = await backend.validateSession(sessionId);
			event.locals.user = {
				id: user.id,
				email: user.email || '',
				role: user.role || 'viewer'
			};
		} catch (err) {
			// Session is invalid or expired - clear the cookie
			event.cookies.delete(SESSION_COOKIE_NAME, { path: '/' });
			event.locals.user = null;
		}
	} else {
		event.locals.user = null;
	}

	return resolve(event);
};
