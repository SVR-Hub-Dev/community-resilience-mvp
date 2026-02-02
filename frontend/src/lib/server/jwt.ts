/**
 * Server-only JWT minting utility for derived tokens.
 * These tokens are used for SvelteKit → FastAPI communication.
 */

import { SignJWT } from 'jose';
import { env } from '$env/dynamic/private';

const DERIVED_JWT_SECRET = env.DERIVED_JWT_SECRET;
const DERIVED_JWT_ISSUER = env.DERIVED_JWT_ISSUER || 'sveltekit';
const DERIVED_JWT_EXPIRY = '5m'; // Short-lived tokens

export interface DerivedTokenPayload {
	sub: string; // user id as string
	role: string;
}

/**
 * Mint a short-lived derived JWT for SvelteKit → FastAPI calls.
 * This token is never exposed to the browser.
 */
export async function mintDerivedToken(user: { id: number; role: string }): Promise<string> {
	if (!DERIVED_JWT_SECRET) {
		throw new Error('DERIVED_JWT_SECRET not configured');
	}

	const secret = new TextEncoder().encode(DERIVED_JWT_SECRET);

	const token = await new SignJWT({
		sub: String(user.id),
		role: user.role
	})
		.setProtectedHeader({ alg: 'HS256' })
		.setIssuedAt()
		.setIssuer(DERIVED_JWT_ISSUER)
		.setExpirationTime(DERIVED_JWT_EXPIRY)
		.sign(secret);

	return token;
}
