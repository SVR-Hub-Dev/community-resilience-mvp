<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData } = $props();

	let isLoading = $state(false);

	function handleEnhance() {
		isLoading = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isLoading = false;
		};
	}
</script>

<svelte:head>
	<title>Forgot Password - Community Resilience</title>
</svelte:head>

<div class="forgot-password-container">
	<div class="forgot-password-card">
		<div class="header">
			<span class="icon">🔑</span>
			<h1>Reset Password</h1>
			<p>Enter your email address and we'll send you a link to reset your password.</p>
		</div>

		{#if form?.success}
			<div class="success-message">
				<svg viewBox="0 0 20 20" width="20" height="20">
					<path
						fill="currentColor"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
					/>
				</svg>
				<div>
					<strong>Check your email</strong>
					<p>
						If an account exists with that email, we've sent password reset instructions.
						Please check your inbox and spam folder.
					</p>
				</div>
			</div>
			<a href="/auth/login" class="back-link">Back to login</a>
		{:else}
			{#if form?.error}
				<div class="error-message">
					{form.error}
				</div>
			{/if}

			<form method="POST" use:enhance={handleEnhance}>
				<input
					type="email"
					name="email"
					placeholder="Email address"
					autocomplete="email"
					class="form-input"
					required
					disabled={isLoading}
				/>
				<button type="submit" class="submit-button" disabled={isLoading}>
					{isLoading ? 'Sending...' : 'Send Reset Link'}
				</button>
			</form>

			<a href="/auth/login" class="back-link">Back to login</a>
		{/if}
	</div>
</div>

<style>
	.forgot-password-container {
		min-height: calc(100vh - 200px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
	}

	.forgot-password-card {
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
		background: #fef2f2;
		color: #dc2626;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
		border: 1px solid #fecaca;
	}

	form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
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
