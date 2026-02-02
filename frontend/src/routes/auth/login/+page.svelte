<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData } = $props();

	let isLoading = $state(false);
	let isOnline = $state(true);
	let showPassword = $state(false);

	// Determine if we're in TOTP step based on form response
	let totpRequired = $derived(form?.requiresTotp === true);
	let totpToken = $derived(form?.totpToken || '');
	let email = $derived(form?.email || '');
	// Check for error from form action or from URL (OAuth errors)
	let error = $derived(form?.error || page.url.searchParams.get('error') || null);

	// Track online/offline status
	onMount(() => {
		isOnline = navigator.onLine;

		const handleOnline = () => {
			isOnline = true;
		};
		const handleOffline = () => {
			isOnline = false;
		};

		window.addEventListener('online', handleOnline);
		window.addEventListener('offline', handleOffline);

		return () => {
			window.removeEventListener('online', handleOnline);
			window.removeEventListener('offline', handleOffline);
		};
	});

	function handleEnhance() {
		isLoading = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isLoading = false;
		};
	}

	function loginWithProvider(provider: 'google' | 'github' | 'microsoft') {
		isLoading = true;
		// Navigate to the OAuth initiation endpoint
		window.location.href = `/auth/${provider}`;
	}
</script>

<svelte:head>
	<title>Sign In - Community Resilience</title>
</svelte:head>

<div class="login-container">
	<div class="login-card">
		<div class="login-header">
			<span class="login-icon">🏘️</span>
			<h1>Welcome Back</h1>
			<p>Sign in to access the Community Resilience platform</p>
		</div>

		{#if error}
			<div class="error-message">
				{error}
			</div>
		{/if}

		{#if totpRequired}
			<form class="totp-form" method="POST" action="?/verifyTotp" use:enhance={handleEnhance}>
				<input type="hidden" name="totp_token" value={totpToken} />
				<input type="hidden" name="email" value={email} />
				<p class="totp-prompt">Enter the 6-digit code from your authenticator app.</p>
				<input
					type="text"
					name="code"
					placeholder="000000"
					maxlength="6"
					pattern="[0-9]*"
					inputmode="numeric"
					autocomplete="one-time-code"
					class="totp-input"
					required
					disabled={isLoading}
				/>
				<button type="submit" class="submit-button" disabled={isLoading}>
					{isLoading ? 'Verifying...' : 'Verify'}
				</button>
				<a href="/auth/login" class="back-link">Back to login</a>
			</form>
		{:else}
			<form class="password-form" method="POST" action="?/login" use:enhance={handleEnhance}>
				<input
					type="email"
					name="email"
					value={email}
					placeholder="Email address"
					autocomplete="email"
					class="form-input"
					required
					disabled={isLoading}
				/>
				<div class="password-input-wrapper">
					<input
						type={showPassword ? 'text' : 'password'}
						name="password"
						placeholder="Password"
						autocomplete="current-password"
						class="form-input password-input"
						required
						disabled={isLoading}
					/>
					<button
						type="button"
						class="password-toggle"
						onclick={() => (showPassword = !showPassword)}
						aria-label={showPassword ? 'Hide password' : 'Show password'}
						disabled={isLoading}
					>
						{#if showPassword}
							<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
								/>
							</svg>
						{:else}
							<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
								/>
							</svg>
						{/if}
					</button>
				</div>
				<div class="form-footer">
					<a href="/auth/forgot-password" class="forgot-password-link">Forgot password?</a>
				</div>
				<button type="submit" class="submit-button" disabled={isLoading}>
					{isLoading ? 'Signing in...' : 'Sign In'}
				</button>
			</form>

			<p class="register-link">
				Don't have an account? <a href="/auth/register">Create one</a>
			</p>

			{#if isOnline}
				<div class="divider">
					<span>or continue with</span>
				</div>

				<div class="login-buttons">
					<button
						class="oauth-button google"
						onclick={() => loginWithProvider('google')}
						disabled={isLoading}
					>
						<svg viewBox="0 0 24 24" width="20" height="20">
							<path
								fill="currentColor"
								d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
							/>
							<path
								fill="currentColor"
								d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
							/>
							<path
								fill="currentColor"
								d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
							/>
							<path
								fill="currentColor"
								d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
							/>
						</svg>
						<span>Google</span>
					</button>

					<button
						class="oauth-button github"
						onclick={() => loginWithProvider('github')}
						disabled={isLoading}
					>
						<svg viewBox="0 0 24 24" width="20" height="20">
							<path
								fill="currentColor"
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/>
						</svg>
						<span>GitHub</span>
					</button>

					<button
						class="oauth-button microsoft"
						onclick={() => loginWithProvider('microsoft')}
						disabled={isLoading}
					>
						<svg viewBox="0 0 24 24" width="20" height="20">
							<path fill="#f25022" d="M1 1h10v10H1z" />
							<path fill="#00a4ef" d="M1 13h10v10H1z" />
							<path fill="#7fba00" d="M13 1h10v10H13z" />
							<path fill="#ffb900" d="M13 13h10v10H13z" />
						</svg>
						<span>Microsoft</span>
					</button>
				</div>
			{:else}
				<div class="offline-notice">
					<svg viewBox="0 0 20 20" width="16" height="16">
						<path
							fill="currentColor"
							d="M10 2a8 8 0 100 16 8 8 0 000-16zM9 5a1 1 0 112 0v4a1 1 0 11-2 0V5zm1 9a1 1 0 100-2 1 1 0 000 2z"
						/>
					</svg>
					<span>No internet connection - OAuth login unavailable</span>
				</div>
			{/if}
		{/if}

		{#if !totpRequired}
			<div class="login-footer">
				<p>By signing in, you agree to our terms of service and privacy policy.</p>
			</div>
		{/if}
	</div>
</div>

<style>
	.login-container {
		min-height: calc(100vh - 200px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
	}

	.login-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2.5rem;
		width: 100%;
		max-width: 400px;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	}

	.login-header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.login-icon {
		font-size: 3rem;
		display: block;
		margin-bottom: 1rem;
	}

	.login-header h1 {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text);
	}

	.login-header p {
		color: var(--text-muted);
		margin: 0;
		font-size: 0.875rem;
	}

	.error-message {
		background: #fef2f2;
		color: #dc2626;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
		border: 1px solid #fecaca;
	}

	/* Password form */
	.password-form {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.form-input {
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 0.9375rem;
		background: var(--surface);
		color: var(--text);
		outline: none;
		transition: border-color 0.15s ease;
	}

	.form-input:focus {
		border-color: var(--primary);
	}

	.form-input:disabled {
		opacity: 0.6;
	}

	.password-input-wrapper {
		position: relative;
		display: flex;
		align-items: center;
	}

	.password-input {
		padding-right: 3rem;
	}

	.password-toggle {
		position: absolute;
		right: 0.75rem;
		background: none;
		border: none;
		padding: 0.5rem;
		cursor: pointer;
		color: var(--text-muted);
		display: flex;
		align-items: center;
		justify-content: center;
		transition: color 0.15s ease;
	}

	.password-toggle:hover:not(:disabled) {
		color: var(--text);
	}

	.password-toggle:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.form-footer {
		display: flex;
		justify-content: flex-end;
	}

	.forgot-password-link {
		font-size: 0.875rem;
		color: var(--primary);
		text-decoration: none;
		font-weight: 500;
	}

	.forgot-password-link:hover {
		text-decoration: underline;
	}

	.submit-button {
		padding: 0.875rem 1.5rem;
		border-radius: 8px;
		font-size: 0.9375rem;
		font-weight: 500;
		cursor: pointer;
		background: var(--primary);
		color: white;
		border: none;
		transition: background 0.15s ease;
	}

	.submit-button:hover:not(:disabled) {
		background: var(--primary-dark, #2563eb);
	}

	.submit-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.register-link {
		text-align: center;
		font-size: 0.875rem;
		color: var(--text-muted);
		margin: 0 0 1.5rem 0;
	}

	.register-link a {
		color: var(--primary);
		text-decoration: none;
		font-weight: 500;
	}

	.register-link a:hover {
		text-decoration: underline;
	}

	/* Divider */
	.divider {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.divider::before,
	.divider::after {
		content: '';
		flex: 1;
		height: 1px;
		background: var(--border);
	}

	.divider span {
		font-size: 0.8125rem;
		color: var(--text-muted);
		white-space: nowrap;
	}

	/* OAuth buttons */
	.login-buttons {
		display: flex;
		gap: 0.5rem;
	}

	.oauth-button {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem;
		border-radius: 8px;
		font-size: 0.8125rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
		border: 1px solid var(--border);
	}

	.oauth-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.oauth-button.google {
		background: white;
		color: #374151;
	}

	.oauth-button.google:hover:not(:disabled) {
		background: #f9fafb;
		border-color: #d1d5db;
	}

	.oauth-button.github {
		background: #24292f;
		color: white;
		border-color: #24292f;
	}

	.oauth-button.github:hover:not(:disabled) {
		background: #1b1f23;
	}

	.oauth-button.microsoft {
		background: white;
		color: #374151;
	}

	.oauth-button.microsoft:hover:not(:disabled) {
		background: #f9fafb;
		border-color: #d1d5db;
	}

	/* Offline notice */
	.offline-notice {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: #fef3c7;
		color: #92400e;
		border: 1px solid #fde68a;
		border-radius: 8px;
		font-size: 0.8125rem;
		text-align: center;
	}

	.offline-notice svg {
		flex-shrink: 0;
	}

	/* TOTP form */
	.totp-form {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.totp-prompt {
		color: var(--text-muted);
		font-size: 0.9375rem;
		text-align: center;
		margin: 0;
	}

	.totp-input {
		width: 10ch;
		padding: 0.875rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 1.5rem;
		font-family: monospace;
		text-align: center;
		letter-spacing: 0.3em;
		background: var(--surface);
		color: var(--text);
		outline: none;
	}

	.totp-input:focus {
		border-color: var(--primary);
	}

	.totp-form .submit-button {
		width: 100%;
	}

	.back-link {
		background: none;
		border: none;
		color: var(--text-muted);
		font-size: 0.875rem;
		cursor: pointer;
		padding: 0;
		text-decoration: none;
	}

	.back-link:hover {
		color: var(--text);
	}

	/* Footer */
	.login-footer {
		margin-top: 2rem;
		text-align: center;
	}

	.login-footer p {
		color: var(--text-muted);
		font-size: 0.75rem;
		margin: 0;
	}
</style>
