<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { api } from '$lib/api';
	import { setAuth } from '$lib/auth.svelte';

	let status = $state<'loading' | 'success' | 'error'>('loading');
	let errorMessage = $state<string | null>(null);

	onMount(async () => {
		const params = $page.url.searchParams;
		const accessToken = params.get('access_token');
		const refreshToken = params.get('refresh_token');
		const expiresIn = params.get('expires_in');
		const error = params.get('error');

		if (error) {
			status = 'error';
			errorMessage = decodeURIComponent(error);
			return;
		}

		if (!accessToken || !refreshToken) {
			status = 'error';
			errorMessage = 'Missing authentication tokens';
			return;
		}

		try {
			// Store tokens temporarily to make the API call
			const tempTokens = {
				access_token: accessToken,
				refresh_token: refreshToken,
				token_type: 'bearer',
				expires_in: parseInt(expiresIn || '1800')
			};

			// Set auth with temporary tokens to enable the API call
			// We'll update with real user data after fetching
			setAuth(
				{
					id: 0,
					email: '',
					name: '',
					role: 'viewer',
					oauth_provider: null,
					avatar_url: null,
					is_active: true,
					created_at: '',
					updated_at: ''
				},
				tempTokens
			);

			// Fetch user info
			const user = await api.auth.getMe();

			// Update with real user data
			setAuth(user, tempTokens);

			status = 'success';

			// Redirect to home after a brief delay
			setTimeout(() => {
				goto('/');
			}, 1500);
		} catch (e) {
			status = 'error';
			errorMessage = e instanceof Error ? e.message : 'Failed to complete authentication';
		}
	});
</script>

<svelte:head>
	<title>Signing In... - Community Resilience</title>
</svelte:head>

<div class="callback-container">
	<div class="callback-card">
		{#if status === 'loading'}
			<div class="status-icon loading">
				<span class="spinner"></span>
			</div>
			<h1>Signing you in...</h1>
			<p>Please wait while we complete your authentication.</p>
		{:else if status === 'success'}
			<div class="status-icon success">
				<svg viewBox="0 0 24 24" width="48" height="48">
					<path
						fill="currentColor"
						d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"
					/>
				</svg>
			</div>
			<h1>Welcome!</h1>
			<p>You've been signed in successfully. Redirecting...</p>
		{:else if status === 'error'}
			<div class="status-icon error">
				<svg viewBox="0 0 24 24" width="48" height="48">
					<path
						fill="currentColor"
						d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
					/>
				</svg>
			</div>
			<h1>Authentication Failed</h1>
			<p>{errorMessage || 'Something went wrong during sign in.'}</p>
			<a href="/auth/login" class="retry-button">Try Again</a>
		{/if}
	</div>
</div>

<style>
	.callback-container {
		min-height: calc(100vh - 200px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
	}

	.callback-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 3rem;
		width: 100%;
		max-width: 400px;
		text-align: center;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	}

	.status-icon {
		margin-bottom: 1.5rem;
	}

	.status-icon.loading {
		display: flex;
		justify-content: center;
	}

	.status-icon .spinner {
		width: 48px;
		height: 48px;
		border: 3px solid var(--border);
		border-top-color: var(--primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.status-icon.success {
		color: #10b981;
	}

	.status-icon.error {
		color: #ef4444;
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0 0 0.75rem 0;
		color: var(--text);
	}

	p {
		color: var(--text-muted);
		margin: 0;
		font-size: 0.9375rem;
	}

	.retry-button {
		display: inline-block;
		margin-top: 1.5rem;
		padding: 0.75rem 1.5rem;
		background: var(--primary);
		color: white;
		text-decoration: none;
		border-radius: 8px;
		font-weight: 500;
		transition: background 0.15s ease;
	}

	.retry-button:hover {
		background: var(--primary-dark, #2563eb);
	}
</style>
