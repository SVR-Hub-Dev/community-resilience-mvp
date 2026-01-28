<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { getAuthState, setAuth } from '$lib/auth.svelte';

	const auth = getAuthState();

	let isLoading = $state(false);
	let error = $state<string | null>(null);

	// Password login form
	let email = $state('');
	let password = $state('');

	// TOTP step
	let totpRequired = $state(false);
	let totpToken = $state('');
	let totpCode = $state('');

	// Redirect if already logged in
	$effect(() => {
		if (auth.isAuthenticated) {
			goto('/');
		}
	});

	function loginWithProvider(provider: 'google' | 'github' | 'microsoft') {
		isLoading = true;
		error = null;
		// Navigate directly to the backend OAuth endpoint, which redirects to the provider
		window.location.href = `/api/auth/login/${provider}`;
	}

	async function handlePasswordLogin(e: SubmitEvent) {
		e.preventDefault();
		isLoading = true;
		error = null;

		try {
			const result = await api.auth.login({ email, password });

			if (result.totp_required && result.totp_token) {
				totpRequired = true;
				totpToken = result.totp_token;
				isLoading = false;
				return;
			}

			if (result.access_token && result.refresh_token) {
				const tokens = {
					access_token: result.access_token,
					refresh_token: result.refresh_token,
					token_type: result.token_type,
					expires_in: result.expires_in || 1800
				};
				setAuth(
					{ id: 0, email: '', name: '', role: 'viewer', oauth_provider: null, avatar_url: null, has_password: false, totp_enabled: false, is_active: true, created_at: '', updated_at: '' },
					tokens
				);
				const user = await api.auth.getMe();
				setAuth(user, tokens);
				goto('/');
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Login failed';
		} finally {
			isLoading = false;
		}
	}

	async function handleTotpVerify(e: SubmitEvent) {
		e.preventDefault();
		isLoading = true;
		error = null;

		try {
			const result = await api.auth.loginTotp({ totp_token: totpToken, code: totpCode });

			if (result.access_token && result.refresh_token) {
				const tokens = {
					access_token: result.access_token,
					refresh_token: result.refresh_token,
					token_type: result.token_type,
					expires_in: result.expires_in || 1800
				};
				setAuth(
					{ id: 0, email: '', name: '', role: 'viewer', oauth_provider: null, avatar_url: null, has_password: false, totp_enabled: false, is_active: true, created_at: '', updated_at: '' },
					tokens
				);
				const user = await api.auth.getMe();
				setAuth(user, tokens);
				goto('/');
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid code';
		} finally {
			isLoading = false;
		}
	}

	function backToLogin() {
		totpRequired = false;
		totpToken = '';
		totpCode = '';
		error = null;
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
			<form class="totp-form" onsubmit={handleTotpVerify}>
				<p class="totp-prompt">Enter the 6-digit code from your authenticator app.</p>
				<input
					type="text"
					bind:value={totpCode}
					placeholder="000000"
					maxlength="6"
					pattern="[0-9]*"
					inputmode="numeric"
					autocomplete="one-time-code"
					class="totp-input"
					required
					disabled={isLoading}
				/>
				<button type="submit" class="submit-button" disabled={isLoading || totpCode.length < 6}>
					{isLoading ? 'Verifying...' : 'Verify'}
				</button>
				<button type="button" class="back-link" onclick={backToLogin}>
					Back to login
				</button>
			</form>
		{:else}
			<form class="password-form" onsubmit={handlePasswordLogin}>
				<input
					type="email"
					bind:value={email}
					placeholder="Email address"
					autocomplete="email"
					class="form-input"
					required
					disabled={isLoading}
				/>
				<input
					type="password"
					bind:value={password}
					placeholder="Password"
					autocomplete="current-password"
					class="form-input"
					required
					disabled={isLoading}
				/>
				<button type="submit" class="submit-button" disabled={isLoading || !email || !password}>
					{isLoading ? 'Signing in...' : 'Sign In'}
				</button>
			</form>

			<p class="register-link">
				Don't have an account? <a href="/auth/register">Create one</a>
			</p>

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
