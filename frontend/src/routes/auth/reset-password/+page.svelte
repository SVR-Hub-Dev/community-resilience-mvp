<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData } = $props();

	let isLoading = $state(false);
	let showPassword = $state(false);
	let showConfirmPassword = $state(false);

	// Get the token from URL query params
	let token = $derived(page.url.searchParams.get('token') || '');

	function handleEnhance() {
		isLoading = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isLoading = false;
		};
	}
</script>

<svelte:head>
	<title>Reset Password - Community Resilience</title>
</svelte:head>

<div class="reset-password-container">
	<div class="reset-password-card">
		<div class="header">
			<span class="icon">🔐</span>
			<h1>Create New Password</h1>
			<p>Enter your new password below.</p>
		</div>

		{#if !token}
			<div class="error-message">
				<svg viewBox="0 0 20 20" width="20" height="20">
					<path
						fill="currentColor"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
					/>
				</svg>
				<div>
					<strong>Invalid Reset Link</strong>
					<p>This password reset link is invalid or has expired.</p>
				</div>
			</div>
			<a href="/auth/forgot-password" class="link-button">Request New Reset Link</a>
		{:else if form?.success}
			<div class="success-message">
				<svg viewBox="0 0 20 20" width="20" height="20">
					<path
						fill="currentColor"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
					/>
				</svg>
				<div>
					<strong>Password Reset Successful</strong>
					<p>Your password has been successfully reset. You can now sign in with your new password.</p>
				</div>
			</div>
			<a href="/auth/login" class="link-button">Sign In</a>
		{:else}
			{#if form?.error}
				<div class="error-message">
					{form.error}
				</div>
			{/if}

			<form method="POST" use:enhance={handleEnhance}>
				<input type="hidden" name="token" value={token} />

				<div class="password-input-wrapper">
					<input
						type={showPassword ? 'text' : 'password'}
						name="password"
						placeholder="New password"
						autocomplete="new-password"
						class="form-input password-input"
						minlength="8"
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

				<div class="password-input-wrapper">
					<input
						type={showConfirmPassword ? 'text' : 'password'}
						name="confirmPassword"
						placeholder="Confirm new password"
						autocomplete="new-password"
						class="form-input password-input"
						minlength="8"
						required
						disabled={isLoading}
					/>
					<button
						type="button"
						class="password-toggle"
						onclick={() => (showConfirmPassword = !showConfirmPassword)}
						aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
						disabled={isLoading}
					>
						{#if showConfirmPassword}
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

				<div class="password-requirements">
					<p>Password must be at least 8 characters long.</p>
				</div>

				<button type="submit" class="submit-button" disabled={isLoading}>
					{isLoading ? 'Resetting...' : 'Reset Password'}
				</button>
			</form>

			<a href="/auth/login" class="back-link">Back to login</a>
		{/if}
	</div>
</div>

<style>
	.reset-password-container {
		min-height: calc(100vh - 200px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
	}

	.reset-password-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2.5rem;
		width: 100%;
		max-width: 400px;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	}

	.header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.icon {
		font-size: 3rem;
		display: block;
		margin-bottom: 1rem;
	}

	.header h1 {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text);
	}

	.header p {
		color: var(--text-muted);
		margin: 0;
		font-size: 0.875rem;
		line-height: 1.5;
	}

	.success-message {
		display: flex;
		gap: 0.75rem;
		background: #f0fdf4;
		color: #166534;
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		border: 1px solid #bbf7d0;
	}

	.success-message svg {
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.success-message strong {
		display: block;
		margin-bottom: 0.25rem;
	}

	.success-message p {
		margin: 0;
		font-size: 0.875rem;
		line-height: 1.5;
	}

	.error-message {
		display: flex;
		gap: 0.75rem;
		background: #fef2f2;
		color: #dc2626;
		padding: 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		border: 1px solid #fecaca;
	}

	.error-message svg {
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.error-message strong {
		display: block;
		margin-bottom: 0.25rem;
	}

	.error-message p {
		margin: 0;
		font-size: 0.875rem;
		line-height: 1.5;
	}

	form {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
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

	.password-requirements {
		margin: -0.25rem 0 0.25rem 0;
	}

	.password-requirements p {
		margin: 0;
		font-size: 0.8125rem;
		color: var(--text-muted);
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

	.link-button {
		display: block;
		width: 100%;
		padding: 0.875rem 1.5rem;
		border-radius: 8px;
		font-size: 0.9375rem;
		font-weight: 500;
		text-align: center;
		background: var(--primary);
		color: white;
		text-decoration: none;
		transition: background 0.15s ease;
	}

	.link-button:hover {
		background: var(--primary-dark, #2563eb);
	}

	.back-link {
		display: block;
		text-align: center;
		color: var(--text-muted);
		text-decoration: none;
		font-size: 0.875rem;
	}

	.back-link:hover {
		color: var(--text);
	}
</style>
