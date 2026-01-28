<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { getAuthState, updateUser } from '$lib/auth.svelte';
	import type { TOTPSetupResponse } from '$lib/types';
	import { getTheme, setTheme } from '$lib/theme';
	import type { ThemeMode } from '$lib/theme';

	const auth = getAuthState();

	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	// Password state
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');

	// TOTP setup state
	let totpSetup = $state<TOTPSetupResponse | null>(null);
	let verifyCode = $state('');

	// Theme state - initialize to 'system' for SSR
	let themeMode = $state<ThemeMode>('system');

	onMount(() => {
		// Set actual theme from localStorage after mount
		themeMode = getTheme();
	});

	function handleThemeChange(e: Event) {
		const value = (e.target as HTMLInputElement).value as ThemeMode;
		themeMode = value;
		setTheme(themeMode);
	}

	$effect(() => {
		if (!auth.isLoading && !auth.isAuthenticated) {
			goto('/auth/login');
		}
	});

	async function startTotpSetup() {
		isLoading = true;
		error = null;
		success = null;

		try {
			totpSetup = await api.auth.setupTotp();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start TOTP setup';
		} finally {
			isLoading = false;
		}
	}

	async function confirmTotpSetup(e: SubmitEvent) {
		e.preventDefault();
		isLoading = true;
		error = null;

		try {
			await api.auth.verifyTotpSetup(verifyCode);
			// Refresh user data to reflect totp_enabled
			const user = await api.auth.getMe();
			updateUser(user);
			totpSetup = null;
			verifyCode = '';
			success = 'Two-factor authentication has been enabled.';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid code';
		} finally {
			isLoading = false;
		}
	}

	async function disableTotp() {
		isLoading = true;
		error = null;
		success = null;

		try {
			await api.auth.disableTotp();
			const user = await api.auth.getMe();
			updateUser(user);
			success = 'Two-factor authentication has been disabled.';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to disable TOTP';
		} finally {
			isLoading = false;
		}
	}

	async function handleSetPassword(e: SubmitEvent) {
		e.preventDefault();
		error = null;
		success = null;

		if (newPassword.length < 8) {
			error = 'Password must be at least 8 characters.';
			return;
		}
		if (newPassword !== confirmPassword) {
			error = 'Passwords do not match.';
			return;
		}

		isLoading = true;
		try {
			const payload: { new_password: string; current_password?: string } = {
				new_password: newPassword
			};
			if (auth.user?.has_password) {
				payload.current_password = currentPassword;
			}
			await api.auth.setPassword(payload);
			const user = await api.auth.getMe();
			updateUser(user);
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
			success = auth.user?.has_password
				? 'Password has been changed.'
				: 'Password has been set. You can now sign in with email and password.';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to set password';
		} finally {
			isLoading = false;
		}
	}

	function cancelSetup() {
		totpSetup = null;
		verifyCode = '';
		error = null;
	}
</script>

<svelte:head>
	<title>Settings - Community Resilience</title>
</svelte:head>

<div class="settings-container">
	<h1>Settings</h1>

	<section class="settings-section">
		<h2>Theme</h2>
		<p class="section-description">Choose your preferred color mode.</p>
		<div class="theme-switch">
			<label><input type="radio" name="theme" value="light" onchange={handleThemeChange} checked={themeMode === 'light'} /> Light</label>
			<label><input type="radio" name="theme" value="dark" onchange={handleThemeChange} checked={themeMode === 'dark'} /> Dark</label>
			<label><input type="radio" name="theme" value="system" onchange={handleThemeChange} checked={themeMode === 'system'} /> System</label>
		</div>
	</section>

	{#if error}
		<div class="message error-message">{error}</div>
	{/if}
	{#if success}
		<div class="message success-message">{success}</div>
	{/if}

	<section class="settings-section">
		<h2>Password</h2>
		<p class="section-description">
			{#if auth.user?.has_password}
				Change your password for email/password sign-in.
			{:else}
				Set a password to enable offline sign-in with your email and password.
			{/if}
		</p>

		<form class="password-form" onsubmit={handleSetPassword}>
			{#if auth.user?.has_password}
				<label for="current-password">Current password</label>
				<input
					id="current-password"
					type="password"
					bind:value={currentPassword}
					required
					disabled={isLoading}
					autocomplete="current-password"
				/>
			{/if}

			<label for="new-password">
				{auth.user?.has_password ? 'New password' : 'Password'}
			</label>
			<input
				id="new-password"
				type="password"
				bind:value={newPassword}
				required
				minlength="8"
				disabled={isLoading}
				autocomplete="new-password"
			/>

			<label for="confirm-password">Confirm password</label>
			<input
				id="confirm-password"
				type="password"
				bind:value={confirmPassword}
				required
				minlength="8"
				disabled={isLoading}
				autocomplete="new-password"
			/>

			<button type="submit" class="btn btn-primary" disabled={isLoading || newPassword.length < 8 || newPassword !== confirmPassword}>
				{isLoading ? 'Saving...' : auth.user?.has_password ? 'Change Password' : 'Set Password'}
			</button>
		</form>
	</section>

	<section class="settings-section">
		<h2>Two-Factor Authentication (TOTP)</h2>
		<p class="section-description">
			Add an extra layer of security by requiring a code from your authenticator app when you sign in.
		</p>

		{#if totpSetup}
			<div class="totp-setup">
				<p>Scan this QR code with your authenticator app (Google Authenticator, Microsoft Authenticator, Authy, etc.):</p>

				<div class="qr-code">
					{@html totpSetup.qr_svg}
				</div>

				<details class="manual-entry">
					<summary>Can't scan? Enter this key manually</summary>
					<code class="secret-key">{totpSetup.secret}</code>
				</details>

				<form class="verify-form" onsubmit={confirmTotpSetup}>
					<label for="totp-verify">Enter the 6-digit code from your app to confirm setup:</label>
					<input
						id="totp-verify"
						type="text"
						bind:value={verifyCode}
						placeholder="000000"
						maxlength="6"
						pattern="[0-9]*"
						inputmode="numeric"
						autocomplete="one-time-code"
						class="totp-input"
						required
						disabled={isLoading}
					/>
					<div class="button-row">
						<button type="submit" class="btn btn-primary" disabled={isLoading || verifyCode.length < 6}>
							{isLoading ? 'Verifying...' : 'Enable TOTP'}
						</button>
						<button type="button" class="btn btn-secondary" onclick={cancelSetup} disabled={isLoading}>
							Cancel
						</button>
					</div>
				</form>
			</div>
		{:else if auth.user?.totp_enabled}
			<div class="totp-status enabled">
				<span class="status-badge">Enabled</span>
				<p>Two-factor authentication is active on your account.</p>
				<button class="btn btn-danger" onclick={disableTotp} disabled={isLoading}>
					{isLoading ? 'Disabling...' : 'Disable TOTP'}
				</button>
			</div>
		{:else}
			<div class="totp-status disabled">
				<span class="status-badge off">Not enabled</span>
				<p>Protect your account with a time-based one-time password.</p>
				<button class="btn btn-primary" onclick={startTotpSetup} disabled={isLoading}>
					{isLoading ? 'Setting up...' : 'Set Up TOTP'}
				</button>
			</div>
		{/if}
	</section>
</div>

<style>
	.theme-switch {
		display: flex;
		gap: 1.5rem;
		margin-bottom: 1.5rem;
		align-items: center;
	}
	.theme-switch label {
		font-size: 1rem;
		color: var(--text);
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.settings-container {
		max-width: 640px;
		margin: 0 auto;
		padding: 2rem;
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--text);
		margin: 0 0 1.5rem 0;
	}

	.message {
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
	}

	.error-message {
		background: #fef2f2;
		color: #dc2626;
		border: 1px solid #fecaca;
	}

	.success-message {
		background: #f0fdf4;
		color: #16a34a;
		border: 1px solid #bbf7d0;
	}

	.settings-section {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
	}

	h2 {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--text);
		margin: 0 0 0.5rem 0;
	}

	.section-description {
		color: var(--text-muted);
		font-size: 0.875rem;
		margin: 0 0 1.5rem 0;
	}

	.settings-section + .settings-section {
		margin-top: 1.5rem;
	}

	/* Password form */
	.password-form {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.password-form label {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text);
		margin-top: 0.25rem;
	}

	.password-form input {
		padding: 0.625rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 0.875rem;
		background: var(--surface);
		color: var(--text);
		outline: none;
	}

	.password-form input:focus {
		border-color: var(--primary);
	}

	.password-form .btn {
		margin-top: 0.5rem;
		align-self: flex-start;
	}

	/* TOTP status */
	.totp-status {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		align-items: flex-start;
	}

	.totp-status p {
		color: var(--text-muted);
		font-size: 0.875rem;
		margin: 0;
	}

	.status-badge {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		border-radius: 999px;
		font-size: 0.75rem;
		font-weight: 600;
		background: #dcfce7;
		color: #16a34a;
	}

	.status-badge.off {
		background: #f3f4f6;
		color: #6b7280;
	}

	/* TOTP setup */
	.totp-setup {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.totp-setup p {
		color: var(--text-muted);
		font-size: 0.875rem;
		margin: 0;
	}

	.qr-code {
		display: flex;
		justify-content: center;
		padding: 1rem;
		background: white;
		border-radius: 8px;
		border: 1px solid var(--border);
	}

	.qr-code :global(svg) {
		width: 200px;
		height: 200px;
	}

	.manual-entry {
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.manual-entry summary {
		cursor: pointer;
		user-select: none;
	}

	.secret-key {
		display: block;
		margin-top: 0.5rem;
		padding: 0.75rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		font-family: monospace;
		font-size: 0.9375rem;
		letter-spacing: 0.1em;
		word-break: break-all;
		color: var(--text);
	}

	.verify-form {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.verify-form label {
		font-size: 0.875rem;
		color: var(--text);
	}

	.totp-input {
		width: 10ch;
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 1.25rem;
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

	/* Buttons */
	.button-row {
		display: flex;
		gap: 0.5rem;
	}

	.btn {
		padding: 0.625rem 1.25rem;
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		border: 1px solid transparent;
		transition: all 0.15s ease;
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-primary {
		background: var(--primary);
		color: white;
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--primary-dark, #2563eb);
	}

	.btn-secondary {
		background: var(--surface);
		color: var(--text);
		border-color: var(--border);
	}

	.btn-secondary:hover:not(:disabled) {
		background: var(--border);
	}

	.btn-danger {
		background: #ef4444;
		color: white;
	}

	.btn-danger:hover:not(:disabled) {
		background: #dc2626;
	}
</style>
