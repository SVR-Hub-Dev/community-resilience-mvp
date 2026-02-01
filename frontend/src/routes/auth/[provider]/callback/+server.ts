import { redirect, error } from '@sveltejs/kit';
import { dev } from '$app/environment';
import type { RequestHandler } from './$types';
import {
	isValidProvider,
	exchangeCodeForToken,
	fetchUserInfo,
	type OAuthProvider
} from '$lib/server/oauth';
import { backend } from '$lib/server/backend';

const STATE_COOKIE_NAME = 'oauth_state';
const SESSION_COOKIE_NAME = 'session_id';
const SESSION_TTL_SECONDS = 7 * 24 * 60 * 60; // 7 days

export const GET: RequestHandler = async ({ params, url, cookies }) => {
	const { provider } = params;

	// Validate provider
	if (!isValidProvider(provider)) {
		throw error(400, `Invalid OAuth provider: ${provider}`);
	}

	const typedProvider = provider as OAuthProvider;

	// Get the authorization code and state from query params
	const code = url.searchParams.get('code');
	const state = url.searchParams.get('state');
	const errorParam = url.searchParams.get('error');
	const errorDescription = url.searchParams.get('error_description');

	// Handle OAuth errors from provider
	if (errorParam) {
		console.error(`OAuth error from ${provider}: ${errorParam} - ${errorDescription}`);
		throw redirect(302, `/auth/login?error=${encodeURIComponent(errorDescription || errorParam)}`);
	}

	if (!code || !state) {
		throw redirect(302, '/auth/login?error=Missing authorization code or state');
	}

	// Verify state matches cookie (CSRF protection)
	const storedState = cookies.get(STATE_COOKIE_NAME);
	cookies.delete(STATE_COOKIE_NAME, { path: '/' });

	if (!storedState || storedState !== state) {
		console.error('OAuth state mismatch - possible CSRF attack');
		throw redirect(302, '/auth/login?error=Invalid state parameter');
	}

	try {
		// Build the redirect URI (must match what was used in initiation)
		const redirectUri = `${url.origin}/auth/${provider}/callback`;

		// Exchange authorization code for access token
		const tokenResponse = await exchangeCodeForToken(typedProvider, code, redirectUri);

		// Fetch user info from provider
		const userInfo = await fetchUserInfo(typedProvider, tokenResponse.access_token);

		// Find or create user in our backend
		const oauthResult = await backend.oauthFindOrCreate({
			provider: userInfo.provider,
			provider_id: userInfo.provider_id,
			email: userInfo.email,
			name: userInfo.name,
			avatar_url: userInfo.avatar_url
		});

		// Create session
		const { session_id } = await backend.createSession(oauthResult.user_id, SESSION_TTL_SECONDS);

		// Set session cookie
		cookies.set(SESSION_COOKIE_NAME, session_id, {
			path: '/',
			httpOnly: true,
			secure: !dev,
			sameSite: 'lax',
			maxAge: SESSION_TTL_SECONDS
		});

		// Redirect to home
		throw redirect(302, '/');
	} catch (err) {
		if (err instanceof Response) {
			// This is a redirect, re-throw it
			throw err;
		}

		console.error(`OAuth callback error for ${provider}:`, err);

		const errorMessage =
			err instanceof Error ? err.message : 'Authentication failed. Please try again.';

		throw redirect(302, `/auth/login?error=${encodeURIComponent(errorMessage)}`);
	}
};
