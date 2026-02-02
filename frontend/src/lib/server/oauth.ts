/**
 * OAuth provider configuration and utilities.
 * Server-only module for OAuth flow handling.
 */

import { env } from '$env/dynamic/private';

export type OAuthProvider = 'google' | 'github' | 'microsoft';

interface OAuthConfig {
	clientId: string;
	clientSecret: string;
	authUrl: string;
	tokenUrl: string;
	userInfoUrl: string;
	scopes: string[];
}

const OAUTH_CONFIGS: Record<OAuthProvider, () => OAuthConfig> = {
	google: () => ({
		clientId: env.GOOGLE_CLIENT_ID || '',
		clientSecret: env.GOOGLE_CLIENT_SECRET || '',
		authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
		tokenUrl: 'https://oauth2.googleapis.com/token',
		userInfoUrl: 'https://openidconnect.googleapis.com/v1/userinfo',
		scopes: ['openid', 'email', 'profile']
	}),
	github: () => ({
		clientId: env.GITHUB_CLIENT_ID || '',
		clientSecret: env.GITHUB_CLIENT_SECRET || '',
		authUrl: 'https://github.com/login/oauth/authorize',
		tokenUrl: 'https://github.com/login/oauth/access_token',
		userInfoUrl: 'https://api.github.com/user',
		scopes: ['read:user', 'user:email']
	}),
	microsoft: () => ({
		clientId: env.MICROSOFT_CLIENT_ID || '',
		clientSecret: env.MICROSOFT_CLIENT_SECRET || '',
		authUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
		tokenUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
		userInfoUrl: 'https://graph.microsoft.com/v1.0/me',
		scopes: ['openid', 'email', 'profile', 'User.Read']
	})
};

export function isValidProvider(provider: string): provider is OAuthProvider {
	return ['google', 'github', 'microsoft'].includes(provider);
}

export function getOAuthConfig(provider: OAuthProvider): OAuthConfig {
	return OAUTH_CONFIGS[provider]();
}

export function generateState(): string {
	const array = new Uint8Array(32);
	crypto.getRandomValues(array);
	return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export function buildAuthorizationUrl(
	provider: OAuthProvider,
	redirectUri: string,
	state: string
): string {
	const config = getOAuthConfig(provider);

	if (!config.clientId) {
		throw new Error(`OAuth client ID not configured for ${provider}`);
	}

	const params = new URLSearchParams({
		client_id: config.clientId,
		redirect_uri: redirectUri,
		response_type: 'code',
		scope: config.scopes.join(' '),
		state
	});

	// Provider-specific parameters
	if (provider === 'google') {
		params.set('access_type', 'offline');
		params.set('prompt', 'consent');
	}

	return `${config.authUrl}?${params.toString()}`;
}

export interface TokenResponse {
	access_token: string;
	token_type: string;
	expires_in?: number;
	refresh_token?: string;
	scope?: string;
}

export async function exchangeCodeForToken(
	provider: OAuthProvider,
	code: string,
	redirectUri: string
): Promise<TokenResponse> {
	const config = getOAuthConfig(provider);

	const params = new URLSearchParams({
		client_id: config.clientId,
		client_secret: config.clientSecret,
		code,
		redirect_uri: redirectUri,
		grant_type: 'authorization_code'
	});

	const headers: Record<string, string> = {
		'Content-Type': 'application/x-www-form-urlencoded'
	};

	// GitHub requires Accept header for JSON response
	if (provider === 'github') {
		headers['Accept'] = 'application/json';
	}

	const response = await fetch(config.tokenUrl, {
		method: 'POST',
		headers,
		body: params.toString()
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`Token exchange failed: ${response.status} - ${errorText}`);
	}

	return response.json();
}

export interface OAuthUserInfo {
	provider: OAuthProvider;
	provider_id: string;
	email: string;
	name: string;
	avatar_url?: string;
}

export async function fetchUserInfo(
	provider: OAuthProvider,
	accessToken: string
): Promise<OAuthUserInfo> {
	const config = getOAuthConfig(provider);

	const response = await fetch(config.userInfoUrl, {
		headers: {
			Authorization: `Bearer ${accessToken}`,
			Accept: 'application/json'
		}
	});

	if (!response.ok) {
		const errorText = await response.text();
		throw new Error(`User info fetch failed: ${response.status} - ${errorText}`);
	}

	const data = await response.json();

	// Normalize user info based on provider
	switch (provider) {
		case 'google':
			return {
				provider,
				provider_id: data.sub,
				email: data.email,
				name: data.name || data.email.split('@')[0],
				avatar_url: data.picture
			};
		case 'github': {
			// GitHub may not return email in the user endpoint if it's private
			let email = data.email;
			if (!email) {
				email = await fetchGitHubPrimaryEmail(accessToken);
			}
			return {
				provider,
				provider_id: String(data.id),
				email,
				name: data.name || data.login,
				avatar_url: data.avatar_url
			};
		}
		case 'microsoft':
			return {
				provider,
				provider_id: data.id,
				email: data.mail || data.userPrincipalName,
				name: data.displayName || data.userPrincipalName.split('@')[0],
				avatar_url: undefined // Microsoft Graph requires separate call for photo
			};
	}
}

async function fetchGitHubPrimaryEmail(accessToken: string): Promise<string> {
	const response = await fetch('https://api.github.com/user/emails', {
		headers: {
			Authorization: `Bearer ${accessToken}`,
			Accept: 'application/json'
		}
	});

	if (!response.ok) {
		throw new Error('Failed to fetch GitHub emails');
	}

	const emails = await response.json();
	const primary = emails.find((e: { primary: boolean }) => e.primary);
	if (!primary) {
		throw new Error('No primary email found on GitHub account');
	}
	return primary.email;
}
