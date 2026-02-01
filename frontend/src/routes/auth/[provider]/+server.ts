import { redirect, error } from '@sveltejs/kit';
import { dev } from '$app/environment';
import type { RequestHandler } from './$types';
import { isValidProvider, generateState, buildAuthorizationUrl } from '$lib/server/oauth';

const STATE_COOKIE_NAME = 'oauth_state';
const STATE_COOKIE_MAX_AGE = 60 * 10; // 10 minutes

export const GET: RequestHandler = async ({ params, url, cookies }) => {
	const { provider } = params;

	// Validate provider
	if (!isValidProvider(provider)) {
		throw error(400, `Invalid OAuth provider: ${provider}`);
	}

	// Generate state for CSRF protection
	const state = generateState();

	// Store state in a short-lived cookie
	cookies.set(STATE_COOKIE_NAME, state, {
		path: '/',
		httpOnly: true,
		secure: !dev,
		sameSite: 'lax',
		maxAge: STATE_COOKIE_MAX_AGE
	});

	// Build the callback URL
	const redirectUri = `${url.origin}/auth/${provider}/callback`;

	// Build authorization URL - this can throw if client ID is missing
	const authUrl = buildAuthorizationUrl(provider, redirectUri, state);

	// Redirect to OAuth provider
	redirect(302, authUrl);
};
