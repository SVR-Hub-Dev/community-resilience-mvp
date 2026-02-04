/**
 * API Proxy Route
 *
 * Proxies requests from the frontend to the FastAPI backend.
 * For authenticated requests, mints a derived JWT to authenticate with the backend.
 *
 * This route handles all API calls that go through /api/*, forwarding them
 * to the backend with proper authentication.
 */

import { error, type RequestHandler } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { mintDerivedToken } from '$lib/server/jwt';

const API_URL = env.API_URL || 'http://localhost:8000';

/**
 * Generic handler for all HTTP methods
 */
async function handleRequest(event: Parameters<RequestHandler>[0]): Promise<Response> {
	const { params, request, locals } = event;
	const path = params.path || '';
	const targetUrl = `${API_URL}/${path}${event.url.search}`;

	// Build headers, starting with content-type if present
	const headers: Record<string, string> = {};

	const contentType = request.headers.get('content-type');
	if (contentType) {
		headers['Content-Type'] = contentType;
	}

	// If user is authenticated, mint a derived JWT
	if (locals.user) {
		try {
			const derivedToken = await mintDerivedToken({
				id: locals.user.id,
				role: locals.user.role
			});
			headers['Authorization'] = `Bearer ${derivedToken}`;
		} catch (err) {
			console.error('Failed to mint derived token:', err);
			throw error(500, 'Authentication service unavailable');
		}
	}

	// Forward the request body for methods that have one
	let body: BodyInit | null = null;
	if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
		// Check if this is a multipart form (file upload)
		if (contentType?.includes('multipart/form-data')) {
			body = await request.formData();
			// Don't set Content-Type for FormData - fetch will set it with boundary
			delete headers['Content-Type'];
		} else {
			body = await request.text();
		}
	}

	try {
		const response = await fetch(targetUrl, {
			method: request.method,
			headers,
			body
		});

		// Return the response with appropriate headers
		const responseHeaders = new Headers();

		// Copy relevant headers from backend response
		const contentTypeHeader = response.headers.get('content-type');
		if (contentTypeHeader) {
			responseHeaders.set('Content-Type', contentTypeHeader);
		}

		return new Response(response.body, {
			status: response.status,
			statusText: response.statusText,
			headers: responseHeaders
		});
	} catch (err) {
		console.error('API proxy error:', err);
		throw error(502, 'Backend service unavailable');
	}
}

export const GET: RequestHandler = handleRequest;
export const POST: RequestHandler = handleRequest;
export const PUT: RequestHandler = handleRequest;
export const PATCH: RequestHandler = handleRequest;
export const DELETE: RequestHandler = handleRequest;
