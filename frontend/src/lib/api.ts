import type {
	QueryResponse,
	KnowledgeEntry,
	FeedbackRequest,
	CommunityEvent,
	CommunityAsset,
	HealthStatus,
	User,
	TokenPair,
	OAuthRedirect,
	APIKey,
	APIKeyCreated,
	Session,
	LoginResponse,
	AuthResponse,
	TOTPSetupResponse,
	DocumentUploadResponse,
	DocumentStatusResponse,
	DocumentProcessingStats,
	KGEntity,
	KGEntityDetail,
	KGEntityList,
	KGStats,
	KGNetworkData,
	SupportTicket,
	TicketDetail,
	TicketListResponse,
	TicketResponse,
	TicketPriority,
	ContactSubmission,
	ContactListResponse
} from './types';
import {
	getAccessToken,
	getRefreshToken,
	updateAccessToken,
	clearAuth
} from './auth.svelte';

// Use VITE_API_URL env var for production, fall back to /api for local dev (proxied by Vite)
const API_BASE = import.meta.env.VITE_API_URL || '/api';

// Track if we're currently refreshing to prevent multiple refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token using the refresh token.
 * Returns true if successful, false otherwise.
 */
async function refreshAccessToken(): Promise<boolean> {
	const refreshToken = getRefreshToken();
	if (!refreshToken) {
		return false;
	}

	try {
		const response = await fetch(`${API_BASE}/auth/refresh`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ refresh_token: refreshToken })
		});

		if (!response.ok) {
			return false;
		}

		const data: TokenPair = await response.json();
		updateAccessToken(data.access_token);
		return true;
	} catch {
		return false;
	}
}

/**
 * Core fetch wrapper with authentication and token refresh.
 */
async function fetchApi<T>(
	endpoint: string,
	options?: RequestInit,
	skipAuth = false
): Promise<T> {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options?.headers as Record<string, string>)
	};

	// Add auth header if we have a token
	const token = getAccessToken();
	if (token && !skipAuth) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	let response = await fetch(`${API_BASE}${endpoint}`, {
		...options,
		headers,
		credentials: 'include'
	});

	// If 401 and we have a refresh token, try to refresh
	if (response.status === 401 && !skipAuth) {
		// Prevent multiple simultaneous refresh attempts
		if (!isRefreshing) {
			isRefreshing = true;
			refreshPromise = refreshAccessToken();
		}

		const refreshed = await refreshPromise;
		isRefreshing = false;
		refreshPromise = null;

		if (refreshed) {
			// Retry the original request with new token
			const newToken = getAccessToken();
			if (newToken) {
				headers['Authorization'] = `Bearer ${newToken}`;
			}
			response = await fetch(`${API_BASE}${endpoint}`, {
				...options,
				headers
			});
		} else {
			// Refresh failed, clear auth and redirect to login
			clearAuth();
			if (typeof window !== 'undefined') {
				window.location.href = '/auth/login';
			}
			throw new Error('Session expired. Please log in again.');
		}
	}

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Request failed' }));
		throw new Error(error.detail || `HTTP ${response.status}`);
	}

	// Handle empty responses (204 No Content)
	const text = await response.text();
	if (!text) {
		return {} as T;
	}
	return JSON.parse(text);
}

/**
 * Fetch without authentication (for public endpoints like health check).
 */
async function fetchPublic<T>(endpoint: string, options?: RequestInit): Promise<T> {
	return fetchApi<T>(endpoint, options, true);
}

/**
 * Upload a file via multipart form data with authentication.
 * Does not set Content-Type — the browser sets it with the boundary.
 */
async function fetchUpload<T>(endpoint: string, formData: FormData): Promise<T> {
	const headers: Record<string, string> = {};
	const token = getAccessToken();
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(`${API_BASE}${endpoint}`, {
		method: 'POST',
		headers,
		body: formData,
		credentials: 'include'
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
		throw new Error(error.detail || `HTTP ${response.status}`);
	}

	return response.json();
}

export const api = {
	// ========================================================================
	// Query endpoint
	// ========================================================================
	query: (text: string): Promise<QueryResponse> =>
		fetchApi('/query', {
			method: 'POST',
			body: JSON.stringify({ text })
		}),

	// ========================================================================
	// Knowledge endpoints
	// ========================================================================
	getKnowledge: (): Promise<KnowledgeEntry[]> => fetchApi('/knowledge'),

	getKnowledgeById: (id: number): Promise<KnowledgeEntry> => fetchApi(`/knowledge/${id}`),

	createKnowledge: (entry: Omit<KnowledgeEntry, 'id' | 'created_at'>): Promise<{ status: string; id: number }> =>
		fetchApi('/ingest', {
			method: 'POST',
			body: JSON.stringify(entry)
		}),

	updateKnowledge: (
		id: number,
		entry: Partial<KnowledgeEntry>
	): Promise<{ status: string; id: number }> =>
		fetchApi(`/knowledge/${id}`, {
			method: 'PUT',
			body: JSON.stringify(entry)
		}),

	deleteKnowledge: (id: number): Promise<{ status: string; id: number }> =>
		fetchApi(`/knowledge/${id}`, {
			method: 'DELETE'
		}),

	// ========================================================================
	// Feedback endpoint
	// ========================================================================
	submitFeedback: (feedback: FeedbackRequest): Promise<{ status: string }> =>
		fetchApi('/feedback', {
			method: 'POST',
			body: JSON.stringify(feedback)
		}),

	// ========================================================================
	// Events endpoints
	// ========================================================================
	getEvents: (): Promise<CommunityEvent[]> => fetchApi('/events'),

	createEvent: (
		event: Omit<CommunityEvent, 'id' | 'timestamp'>
	): Promise<{ status: string; id: number }> =>
		fetchApi('/events', {
			method: 'POST',
			body: JSON.stringify(event)
		}),

	// ========================================================================
	// Assets endpoints
	// ========================================================================
	getAssets: (): Promise<CommunityAsset[]> => fetchApi('/assets'),

	createAsset: (
		asset: Omit<CommunityAsset, 'id' | 'updated_at'>
	): Promise<{ status: string; id: number }> =>
		fetchApi('/assets', {
			method: 'POST',
			body: JSON.stringify(asset)
		}),

	// ========================================================================
	// Document endpoints
	// ========================================================================
	documents: {
		upload: (
			file: File,
			options?: {
				title?: string;
				description?: string;
				tags?: string;
				location?: string;
				hazard_type?: string;
				source?: string;
			}
		): Promise<DocumentUploadResponse> => {
			const formData = new FormData();
			formData.append('file', file);
			if (options?.title) formData.append('title', options.title);
			if (options?.description) formData.append('description', options.description);
			if (options?.tags) formData.append('tags', options.tags);
			if (options?.location) formData.append('location', options.location);
			if (options?.hazard_type) formData.append('hazard_type', options.hazard_type);
			if (options?.source) formData.append('source', options.source);
			return fetchUpload('/documents/upload', formData);
		},

		getStatus: (id: number): Promise<DocumentStatusResponse> =>
			fetchApi(`/documents/${id}/status`),

		getProcessingStats: (): Promise<DocumentProcessingStats> =>
			fetchApi('/documents/processing/stats')
	},

	// ========================================================================
	// Knowledge Graph endpoints
	// ========================================================================
	knowledgeGraph: {
		getEntities: (params?: {
			entity_type?: string;
			search?: string;
			limit?: number;
			offset?: number;
		}): Promise<KGEntityList> => {
			const searchParams = new URLSearchParams();
			if (params?.entity_type) searchParams.set('entity_type', params.entity_type);
			if (params?.search) searchParams.set('search', params.search);
			if (params?.limit) searchParams.set('limit', params.limit.toString());
			if (params?.offset) searchParams.set('offset', params.offset.toString());
			const query = searchParams.toString();
			return fetchApi(`/kg/entities${query ? `?${query}` : ''}`);
		},

		getEntity: (id: number): Promise<KGEntityDetail> =>
			fetchApi(`/kg/entities/${id}`),

		searchEntities: (
			q: string,
			entityTypes?: string[]
		): Promise<{ results: KGEntity[]; count: number }> => {
			const params = new URLSearchParams({ q });
			entityTypes?.forEach((t) => params.append('entity_types', t));
			return fetchApi(`/kg/entities/search?${params}`);
		},

		getStatistics: (): Promise<KGStats> => fetchApi('/kg/statistics'),

		getCoverageGaps: (
			entityType: string,
			relationship: string,
			targetType: string
		): Promise<{ gaps: KGEntity[]; count: number }> =>
			fetchApi(
				`/kg/coverage-gaps?entity_type=${entityType}&required_relationship=${relationship}&target_type=${targetType}`
			),

		getEntityNetwork: (id: number, maxDepth?: number): Promise<KGNetworkData> =>
			fetchApi(`/kg/entities/${id}/network${maxDepth ? `?max_depth=${maxDepth}` : ''}`),

		createEntity: (data: {
			entity_type: string;
			name: string;
			entity_subtype?: string;
			attributes?: Record<string, unknown>;
			location_text?: string;
		}): Promise<{ status: string; id: number }> =>
			fetchApi('/kg/entities', {
				method: 'POST',
				body: JSON.stringify(data)
			}),

		updateEntity: (
			id: number,
			data: {
				name?: string;
				entity_subtype?: string;
				attributes?: Record<string, unknown>;
				location_text?: string;
				confidence_score?: number;
			}
		): Promise<{ status: string; id: number }> =>
			fetchApi(`/kg/entities/${id}`, {
				method: 'PUT',
				body: JSON.stringify(data)
			}),

		deleteEntity: (id: number): Promise<{ status: string; id: number }> =>
			fetchApi(`/kg/entities/${id}`, {
				method: 'DELETE'
			}),

		getTypes: (): Promise<{
			entity_types: string[];
			relationship_types: string[];
		}> => fetchApi('/kg/types')
	},

	// ========================================================================
	// Health check (public)
	// ========================================================================
	getHealth: (): Promise<HealthStatus> => fetchPublic('/health'),

	// ========================================================================
	// Authentication endpoints
	// ========================================================================
	auth: {
		/**
		 * Register with email and password.
		 */
		register: (data: { email: string; password: string; name: string }): Promise<AuthResponse> =>
			fetchPublic('/auth/register', {
				method: 'POST',
				body: JSON.stringify(data)
			}),

		/**
		 * Login with email and password.
		 */
		login: (data: { email: string; password: string }): Promise<LoginResponse> =>
			fetchPublic('/auth/login', {
				method: 'POST',
				body: JSON.stringify(data)
			}),

		/**
		 * Complete login with TOTP code.
		 */
		loginTotp: (data: { totp_token: string; code: string }): Promise<LoginResponse> =>
			fetchPublic('/auth/login/totp', {
				method: 'POST',
				body: JSON.stringify(data)
			}),

		/**
		 * Set up TOTP (returns QR code and secret).
		 */
		setupTotp: (): Promise<TOTPSetupResponse> =>
			fetchApi('/auth/totp/setup', { method: 'POST' }),

		/**
		 * Verify TOTP setup with initial code.
		 */
		verifyTotpSetup: (code: string): Promise<{ message: string }> =>
			fetchApi('/auth/totp/verify-setup', {
				method: 'POST',
				body: JSON.stringify({ code })
			}),

		/**
		 * Set or change password.
		 */
		setPassword: (data: { new_password: string; current_password?: string }): Promise<{ message: string }> =>
			fetchApi('/auth/password', {
				method: 'PUT',
				body: JSON.stringify(data)
			}),

		/**
		 * Disable TOTP.
		 */
		disableTotp: (): Promise<{ message: string }> =>
			fetchApi('/auth/totp', { method: 'DELETE' }),

		/**
		 * Get OAuth login URL for a provider.
		 */
		getLoginUrl: (provider: 'google' | 'github' | 'microsoft'): Promise<OAuthRedirect> =>
			fetchPublic(`/auth/login/${provider}`),

		/**
		 * Refresh access token.
		 */
		refresh: (refreshToken: string): Promise<TokenPair> =>
			fetchPublic('/auth/refresh', {
				method: 'POST',
				body: JSON.stringify({ refresh_token: refreshToken })
			}),

		/**
		 * Logout (invalidate refresh token).
		 */
		logout: (refreshToken: string): Promise<{ message: string }> =>
			fetchApi('/auth/logout', {
				method: 'POST',
				body: JSON.stringify({ refresh_token: refreshToken })
			}),

		/**
		 * Logout from all sessions.
		 */
		logoutAll: (): Promise<{ message: string }> =>
			fetchApi('/auth/logout-all', {
				method: 'POST'
			}),

		/**
		 * Get current user.
		 */
		getMe: (): Promise<User> => fetchApi('/auth/me'),

		/**
		 * Update current user profile.
		 */
		updateMe: (data: { name?: string; avatar_url?: string }): Promise<User> =>
			fetchApi('/auth/me', {
				method: 'PUT',
				body: JSON.stringify(data)
			}),

		/**
		 * List current user's sessions.
		 */
		getSessions: (): Promise<{ sessions: Session[]; total: number }> =>
			fetchApi('/auth/me/sessions'),

		/**
		 * List current user's API keys.
		 */
		getApiKeys: (): Promise<{ api_keys: APIKey[]; total: number }> =>
			fetchApi('/auth/api-keys'),

		/**
		 * Create a new API key.
		 */
		createApiKey: (data: {
			name: string;
			description?: string;
			scopes?: string[];
			expires_in_days?: number;
		}): Promise<APIKeyCreated> =>
			fetchApi('/auth/api-keys', {
				method: 'POST',
				body: JSON.stringify(data)
			}),

		/**
		 * Revoke an API key.
		 */
		revokeApiKey: (id: number): Promise<{ message: string }> =>
			fetchApi(`/auth/api-keys/${id}`, {
				method: 'DELETE'
			}),

		// Admin endpoints
		admin: {
			/**
			 * List all users (admin only).
			 */
			getUsers: (params?: {
				skip?: number;
				limit?: number;
				is_active?: boolean;
				role?: string;
			}): Promise<{ users: User[]; total: number }> => {
				const searchParams = new URLSearchParams();
				if (params?.skip) searchParams.set('skip', params.skip.toString());
				if (params?.limit) searchParams.set('limit', params.limit.toString());
				if (params?.is_active !== undefined)
					searchParams.set('is_active', params.is_active.toString());
				if (params?.role) searchParams.set('role', params.role);
				const query = searchParams.toString();
				return fetchApi(`/auth/users${query ? `?${query}` : ''}`);
			},

			/**
			 * Get a specific user (admin only).
			 */
			getUser: (id: number): Promise<User> => fetchApi(`/auth/users/${id}`),

			/**
			 * Update a user (admin only).
			 */
			updateUser: (
				id: number,
				data: { name?: string; role?: string; is_active?: boolean }
			): Promise<User> =>
				fetchApi(`/auth/users/${id}`, {
					method: 'PUT',
					body: JSON.stringify(data)
				}),

			/**
			 * Delete a user (admin only).
			 */
			deleteUser: (id: number): Promise<{ message: string }> =>
				fetchApi(`/auth/users/${id}`, {
					method: 'DELETE'
				})
		}
	},

	// ========================================================================
	// Support System endpoints
	// ========================================================================

	/**
	 * Submit a contact form (public, no auth required).
	 */
	submitContact: (data: {
		name: string;
		email: string;
		subject: string;
		message: string;
	}): Promise<{ success: boolean; message: string }> =>
		fetchPublic('/contact', {
			method: 'POST',
			body: JSON.stringify(data)
		}),

	support: {
		/**
		 * List current user's tickets.
		 */
		getTickets: (params?: {
			status?: string;
			limit?: number;
			offset?: number;
		}): Promise<TicketListResponse> => {
			const searchParams = new URLSearchParams();
			if (params?.status) searchParams.set('status', params.status);
			if (params?.limit) searchParams.set('limit', params.limit.toString());
			if (params?.offset) searchParams.set('offset', params.offset.toString());
			const query = searchParams.toString();
			return fetchApi(`/support/tickets${query ? `?${query}` : ''}`);
		},

		/**
		 * Create a new support ticket.
		 */
		createTicket: (data: {
			subject: string;
			description: string;
			priority?: TicketPriority;
		}): Promise<SupportTicket> =>
			fetchApi('/support/tickets', {
				method: 'POST',
				body: JSON.stringify(data)
			}),

		/**
		 * Get a specific ticket.
		 */
		getTicket: (id: number): Promise<TicketDetail> =>
			fetchApi(`/support/tickets/${id}`),

		/**
		 * Add a response to a ticket.
		 */
		addResponse: (
			ticketId: number,
			data: { message: string; is_internal?: boolean }
		): Promise<TicketResponse> =>
			fetchApi(`/support/tickets/${ticketId}/responses`, {
				method: 'POST',
				body: JSON.stringify(data)
			}),

		// Admin endpoints
		admin: {
			/**
			 * List all tickets (admin only).
			 */
			getTickets: (params?: {
				status?: string;
				priority?: string;
				assigned_to?: number;
				limit?: number;
				offset?: number;
			}): Promise<TicketListResponse> => {
				const searchParams = new URLSearchParams();
				if (params?.status) searchParams.set('status', params.status);
				if (params?.priority) searchParams.set('priority', params.priority);
				if (params?.assigned_to) searchParams.set('assigned_to', params.assigned_to.toString());
				if (params?.limit) searchParams.set('limit', params.limit.toString());
				if (params?.offset) searchParams.set('offset', params.offset.toString());
				const query = searchParams.toString();
				return fetchApi(`/admin/support/tickets${query ? `?${query}` : ''}`);
			},

			/**
			 * Get a specific ticket (admin).
			 */
			getTicket: (id: number): Promise<TicketDetail> =>
				fetchApi(`/admin/support/tickets/${id}`),

			/**
			 * Update a ticket (admin only).
			 */
			updateTicket: (
				id: number,
				data: { status?: string; priority?: string; assigned_to?: number }
			): Promise<SupportTicket> =>
				fetchApi(`/admin/support/tickets/${id}`, {
					method: 'PUT',
					body: JSON.stringify(data)
				}),

			/**
			 * Add admin response to a ticket.
			 */
			addResponse: (
				ticketId: number,
				data: { message: string; is_internal?: boolean }
			): Promise<TicketResponse> =>
				fetchApi(`/admin/support/tickets/${ticketId}/responses`, {
					method: 'POST',
					body: JSON.stringify(data)
				}),

			/**
			 * List contact form submissions (admin only).
			 */
			getContacts: (params?: {
				is_read?: boolean;
				limit?: number;
				offset?: number;
			}): Promise<ContactListResponse> => {
				const searchParams = new URLSearchParams();
				if (params?.is_read !== undefined)
					searchParams.set('is_read', params.is_read.toString());
				if (params?.limit) searchParams.set('limit', params.limit.toString());
				if (params?.offset) searchParams.set('offset', params.offset.toString());
				const query = searchParams.toString();
				return fetchApi(`/admin/support/contacts${query ? `?${query}` : ''}`);
			},

			/**
			 * Mark a contact as read (admin only).
			 */
			markContactRead: (id: number): Promise<{ status: string }> =>
				fetchApi(`/admin/support/contacts/${id}/read`, {
					method: 'PUT'
				})
		}
	}
};
