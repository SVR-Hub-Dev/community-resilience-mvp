<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { getAuthState, setAuth } from '$lib/auth.svelte';

	const auth = getAuthState();

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	$effect(() => {
		if (auth.isAuthenticated) {
			goto('/');
		}
	});

	async function handleRegister(e: SubmitEvent) {
		e.preventDefault();
		error = null;

		if (password.length < 8) {
			error = 'Password must be at least 8 characters';
			return;
		}

		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		isLoading = true;

		try {
			const result = await api.auth.register({ email, password, name });
			setAuth(result.user, result.tokens);
			goto('/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Registration failed';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Create Account - Community Resilience</title>
</svelte:head>

<div class="register-container">
	<div class="register-card">
		<div class="register-header">
			<span class="register-icon">🏘️</span>
			<h1>Create Account</h1>
			<p>Join the Community Resilience platform</p>
		</div>

		{#if error}
			<div class="error-message">
				{error}
			</div>
		{/if}

		<form class="register-form" onsubmit={handleRegister}>
			<input
				type="text"
				bind:value={name}
				placeholder="Full name"
				autocomplete="name"
				class="form-input"
				required
				disabled={isLoading}
			/>
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
				placeholder="Password (min. 8 characters)"
				autocomplete="new-password"
				minlength="8"
				class="form-input"
				required
				disabled={isLoading}
			/>
			<input
				type="password"
				bind:value={confirmPassword}
				placeholder="Confirm password"
				autocomplete="new-password"
				minlength="8"
				class="form-input"
				required
				disabled={isLoading}
			/>
			<button
				type="submit"
				class="submit-button"
				disabled={isLoading || !name || !email || !password || !confirmPassword}
			>
				{isLoading ? 'Creating account...' : 'Create Account'}
			</button>
		</form>

		<p class="login-link">
			Already have an account? <a href="/auth/login">Sign in</a>
		</p>
	</div>
</div>

<style>
	.register-container {
		min-height: calc(100vh - 200px);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem;
	}

	.register-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2.5rem;
		width: 100%;
		max-width: 400px;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	}

	.register-header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.register-icon {
		font-size: 3rem;
		display: block;
		margin-bottom: 1rem;
	}

	.register-header h1 {
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text);
	}

	.register-header p {
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

	.register-form {
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

	.login-link {
		text-align: center;
		font-size: 0.875rem;
		color: var(--text-muted);
		margin: 0;
	}

	.login-link a {
		color: var(--primary);
		text-decoration: none;
		font-weight: 500;
	}

	.login-link a:hover {
		text-decoration: underline;
	}
</style>
