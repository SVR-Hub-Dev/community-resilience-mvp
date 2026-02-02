/**
 * Server-side API wrapper for calling FastAPI with derived JWT authentication.
 * This module should only be imported in server-side code.
 *
 * Usage:
 *   import { createApiClient } from '$lib/server/api';
 *   const api = createApiClient(locals.user);
 *   const data = await api.get('/knowledge');
 */

import { env } from '$env/dynamic/private';
import { mintDerivedToken } from './jwt';

const API_URL = env.API_URL || 'http://localhost:8000';

export class ApiError extends Error {
	constructor(
		message: string,
		public status: number,
		public data?: unknown
	) {
		super(message);
		this.name = 'ApiError';
	}
}

interface User {
	id: number;
	role: string;
}

interface ApiClient {
	get<T>(path: string): Promise<T>;
	post<T>(path: string, body?: unknown): Promise<T>;
	put<T>(path: string, body?: unknown): Promise<T>;
	patch<T>(path: string, body?: unknown): Promise<T>;
	delete<T>(path: string): Promise<T>;
}

/**
 * Create an authenticated API client for server-side FastAPI calls.
 * Automatically attaches a derived JWT token.
 */
export function createApiClient(user: User | null): ApiClient {
	async function fetchWithAuth<T>(
		path: string,
		options: RequestInit = {}
	): Promise<T> {
		const url = `${API_URL}${path}`;
		const headers: Record<string, string> = {
			'Content-Type': 'application/json',
			...(options.headers as Record<string, string>)
		};

		// Attach derived JWT if user is authenticated
		if (user) {
			const token = await mintDerivedToken(user);
			headers['Authorization'] = `Bearer ${token}`;
		}

		const response = await fetch(url, {
			...options,
			headers
		});

		if (!response.ok) {
			let errorData: unknown;
			try {
				errorData = await response.json();
			} catch {
				errorData = await response.text();
			}
			throw new ApiError(
				`API error: ${response.status}`,
				response.status,
				errorData
			);
		}

		// Handle 204 No Content
		if (response.status === 204) {
			return {} as T;
		}

		return response.json();
	}

	return {
		get<T>(path: string): Promise<T> {
			return fetchWithAuth<T>(path, { method: 'GET' });
		},
		post<T>(path: string, body?: unknown): Promise<T> {
			return fetchWithAuth<T>(path, {
				method: 'POST',
				body: body ? JSON.stringify(body) : undefined
			});
		},
		put<T>(path: string, body?: unknown): Promise<T> {
			return fetchWithAuth<T>(path, {
				method: 'PUT',
				body: body ? JSON.stringify(body) : undefined
			});
		},
		patch<T>(path: string, body?: unknown): Promise<T> {
			return fetchWithAuth<T>(path, {
				method: 'PATCH',
				body: body ? JSON.stringify(body) : undefined
			});
		},
		delete<T>(path: string): Promise<T> {
			return fetchWithAuth<T>(path, { method: 'DELETE' });
		}
	};
}

/**
 * Create an unauthenticated API client for public endpoints.
 */
export function createPublicApiClient(): ApiClient {
	return createApiClient(null);
}
