<script lang="ts">
	import { onMount } from 'svelte';
	import '../app.css';
	import { initAuth, getAuthState, clearAuth, getRefreshToken } from '$lib/auth.svelte';
	import { api } from '$lib/api';

	let { children } = $props();

	const auth = getAuthState();
	let showUserMenu = $state(false);

	onMount(() => {
		initAuth();
	});

	async function handleLogout() {
		const refreshToken = getRefreshToken();
		if (refreshToken) {
			try {
				await api.auth.logout(refreshToken);
			} catch {
				// Ignore errors, clear auth anyway
			}
		}
		clearAuth();
		showUserMenu = false;
		window.location.href = '/auth/login';
	}

	function toggleUserMenu() {
		showUserMenu = !showUserMenu;
	}

	function closeUserMenu() {
		showUserMenu = false;
	}
</script>

<svelte:window onclick={closeUserMenu} />

<div class="layout">
	<header class="header">
		<div class="container header-inner">
			<a href="/" class="logo">
				<span class="logo-icon">🏘️</span>
				<span class="logo-text">Community Resilience</span>
			</a>
			<nav class="nav">
				<a href="/" class="nav-link">Query</a>
				<a href="/knowledge" class="nav-link">Knowledge Base</a>
				<a href="/events" class="nav-link">Events</a>
				<a href="/assets" class="nav-link">Assets</a>

				{#if auth.isAuthenticated && auth.user}
					<div class="user-menu-container">
						<button
							class="user-button"
							onclick={(e) => {
								e.stopPropagation();
								toggleUserMenu();
							}}
						>
							{#if auth.user.avatar_url}
								<img src={auth.user.avatar_url} alt="" class="user-avatar" />
							{:else}
								<span class="user-avatar-placeholder">
									{auth.user.name.charAt(0).toUpperCase()}
								</span>
							{/if}
							<span class="user-name">{auth.user.name}</span>
							<svg class="dropdown-icon" viewBox="0 0 20 20" width="16" height="16">
								<path
									fill="currentColor"
									d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
								/>
							</svg>
						</button>

						{#if showUserMenu}
							<div class="user-dropdown" onclick={(e) => e.stopPropagation()}>
								<div class="dropdown-header">
									<span class="dropdown-email">{auth.user.email}</span>
									<span class="dropdown-role">{auth.user.role}</span>
								</div>
								<div class="dropdown-divider"></div>
								<a href="/profile" class="dropdown-item" onclick={closeUserMenu}>
									<svg viewBox="0 0 20 20" width="16" height="16">
										<path
											fill="currentColor"
											d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
										/>
									</svg>
									Profile
								</a>
								<a href="/api-keys" class="dropdown-item" onclick={closeUserMenu}>
									<svg viewBox="0 0 20 20" width="16" height="16">
										<path
											fill="currentColor"
											d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
										/>
									</svg>
									API Keys
								</a>
								{#if auth.isAdmin}
									<div class="dropdown-divider"></div>
									<a href="/admin/users" class="dropdown-item" onclick={closeUserMenu}>
										<svg viewBox="0 0 20 20" width="16" height="16">
											<path
												fill="currentColor"
												d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"
											/>
										</svg>
										Manage Users
									</a>
								{/if}
								<div class="dropdown-divider"></div>
								<button class="dropdown-item logout" onclick={handleLogout}>
									<svg viewBox="0 0 20 20" width="16" height="16">
										<path
											fill="currentColor"
											d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z"
										/>
									</svg>
									Sign Out
								</button>
							</div>
						{/if}
					</div>
				{:else if auth.isInitialized}
					<a href="/auth/login" class="sign-in-button">Sign In</a>
				{/if}
			</nav>
		</div>
	</header>

	<main class="main">
		{@render children()}
	</main>

	<footer class="footer">
		<div class="container">
			<p>Community Resilience Reasoning Model MVP</p>
		</div>
	</footer>
</div>

<style>
	.layout {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.header {
		background: var(--surface);
		border-bottom: 1px solid var(--border);
		padding: 1rem 0;
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.header-inner {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.logo {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		text-decoration: none;
		color: var(--text);
		font-weight: 600;
		font-size: 1.125rem;
	}

	.logo-icon {
		font-size: 1.5rem;
	}

	.nav {
		display: flex;
		align-items: center;
		gap: 1.5rem;
	}

	.nav-link {
		text-decoration: none;
		color: var(--text-muted);
		font-size: 0.875rem;
		font-weight: 500;
		transition: color 0.15s ease;
	}

	.nav-link:hover {
		color: var(--primary);
	}

	.sign-in-button {
		display: inline-flex;
		align-items: center;
		padding: 0.5rem 1rem;
		background: var(--primary);
		color: white;
		text-decoration: none;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		transition: background 0.15s ease;
	}

	.sign-in-button:hover {
		background: var(--primary-dark, #2563eb);
	}

	.user-menu-container {
		position: relative;
	}

	.user-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.75rem;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 9999px;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.user-button:hover {
		background: var(--surface);
		border-color: var(--border-hover, #9ca3af);
	}

	.user-avatar {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		object-fit: cover;
	}

	.user-avatar-placeholder {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--primary);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.user-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text);
		max-width: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.dropdown-icon {
		color: var(--text-muted);
	}

	.user-dropdown {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		min-width: 220px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
		z-index: 200;
	}

	.dropdown-header {
		padding: 0.75rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.dropdown-email {
		font-size: 0.875rem;
		color: var(--text);
		font-weight: 500;
	}

	.dropdown-role {
		font-size: 0.75rem;
		color: var(--text-muted);
		text-transform: capitalize;
	}

	.dropdown-divider {
		height: 1px;
		background: var(--border);
	}

	.dropdown-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.625rem 1rem;
		color: var(--text);
		text-decoration: none;
		font-size: 0.875rem;
		background: transparent;
		border: none;
		width: 100%;
		text-align: left;
		cursor: pointer;
		transition: background 0.15s ease;
	}

	.dropdown-item:hover {
		background: var(--surface-hover, #f3f4f6);
	}

	.dropdown-item svg {
		color: var(--text-muted);
	}

	.dropdown-item.logout {
		color: #dc2626;
	}

	.dropdown-item.logout svg {
		color: #dc2626;
	}

	.main {
		flex: 1;
		padding: 2rem 0;
	}

	.footer {
		background: var(--surface);
		border-top: 1px solid var(--border);
		padding: 1.5rem 0;
		text-align: center;
		color: var(--text-muted);
		font-size: 0.875rem;
	}
</style>
