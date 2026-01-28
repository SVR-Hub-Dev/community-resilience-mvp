<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { getAuthState } from '$lib/auth.svelte';
	import type { APIKey, APIKeyCreated } from '$lib/types';

	const auth = getAuthState();

	let apiKeys = $state<APIKey[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let showCreateModal = $state(false);
	let newKeyName = $state('');
	let newKeyDescription = $state('');
	let newKeyExpiresDays = $state<number | null>(null);
	let isCreating = $state(false);
	let createdKey = $state<APIKeyCreated | null>(null);

	onMount(async () => {
		if (!auth.isAuthenticated) {
			goto('/auth/login');
			return;
		}
		await loadApiKeys();
	});

	async function loadApiKeys() {
		isLoading = true;
		error = null;
		try {
			const response = await api.auth.getApiKeys();
			apiKeys = response.api_keys;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load API keys';
		}
		isLoading = false;
	}

	async function createApiKey() {
		if (!newKeyName.trim()) return;

		isCreating = true;
		error = null;
		try {
			const key = await api.auth.createApiKey({
				name: newKeyName.trim(),
				description: newKeyDescription.trim() || undefined,
				expires_in_days: newKeyExpiresDays || undefined
			});
			createdKey = key;
			await loadApiKeys();
			newKeyName = '';
			newKeyDescription = '';
			newKeyExpiresDays = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create API key';
		}
		isCreating = false;
	}

	async function revokeKey(id: number) {
		if (!confirm('Are you sure you want to revoke this API key? This cannot be undone.')) {
			return;
		}

		try {
			await api.auth.revokeApiKey(id);
			await loadApiKeys();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to revoke API key';
		}
	}

	function closeCreatedKeyModal() {
		createdKey = null;
		showCreateModal = false;
	}

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text);
	}
</script>

<svelte:head>
	<title>API Keys - Community Resilience</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<h1>API Keys</h1>
		<p>Manage your API keys for programmatic access to the Community Resilience API.</p>
	</div>

	{#if error}
		<div class="error-banner">
			{error}
		</div>
	{/if}

	<div class="card">
		<div class="card-header">
			<h2>Your API Keys</h2>
			<button class="btn btn-primary" onclick={() => (showCreateModal = true)}>
				Create New Key
			</button>
		</div>

		{#if isLoading}
			<div class="loading">Loading...</div>
		{:else if apiKeys.length === 0}
			<div class="empty-state">
				<p>You don't have any API keys yet.</p>
				<p>Create one to start using the API programmatically.</p>
			</div>
		{:else}
			<table class="table">
				<thead>
					<tr>
						<th>Name</th>
						<th>Key Prefix</th>
						<th>Last Used</th>
						<th>Expires</th>
						<th>Status</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each apiKeys as key}
						<tr>
							<td>
								<span class="key-name">{key.name}</span>
								{#if key.description}
									<span class="key-description">{key.description}</span>
								{/if}
							</td>
							<td><code>{key.key_prefix}...</code></td>
							<td>
								{key.last_used_at
									? new Date(key.last_used_at).toLocaleDateString()
									: 'Never'}
							</td>
							<td>
								{key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}
							</td>
							<td>
								<span class="status-badge" class:active={key.is_active}>
									{key.is_active ? 'Active' : 'Inactive'}
								</span>
							</td>
							<td>
								<button class="btn btn-danger btn-sm" onclick={() => revokeKey(key.id)}>
									Revoke
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>

{#if showCreateModal && !createdKey}
	<div class="modal-overlay" onclick={() => (showCreateModal = false)} onkeydown={(e) => {
		if (e.key === 'Escape') {
			showCreateModal = false;
		}
	}} role="dialog" aria-modal="true" aria-labelledby="create-modal-title" tabindex="-1">
		<div class="modal">
			<h2 id="create-modal-title">Create New API Key</h2>
			<form onsubmit={(e) => { e.preventDefault(); createApiKey(); }}>
				<div class="form-group">
					<label for="name">Name *</label>
					<input
						id="name"
						type="text"
						bind:value={newKeyName}
						placeholder="e.g., Production Server"
						required
					/>
				</div>
				<div class="form-group">
					<label for="description">Description</label>
					<input
						id="description"
						type="text"
						bind:value={newKeyDescription}
						placeholder="What is this key for?"
					/>
				</div>
				<div class="form-group">
					<label for="expires">Expires in (days)</label>
					<input
						id="expires"
						type="number"
						bind:value={newKeyExpiresDays}
						placeholder="Leave empty for no expiration"
						min="1"
					/>
				</div>
				<div class="modal-actions">
					<button type="button" class="btn btn-secondary" onclick={() => (showCreateModal = false)}>
						Cancel
					</button>
					<button type="submit" class="btn btn-primary" disabled={isCreating || !newKeyName.trim()}>
						{isCreating ? 'Creating...' : 'Create Key'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

{#if createdKey}
	<div class="modal-overlay" onclick={closeCreatedKeyModal} onkeydown={(e) => {
		if (e.key === 'Escape') {
			closeCreatedKeyModal();
		}
	}} role="dialog" aria-modal="true" aria-labelledby="created-modal-title" tabindex="-1">
		<div class="modal">
			<h2 id="created-modal-title">API Key Created</h2>
			<div class="warning-banner">
				Make sure to copy your API key now. You won't be able to see it again!
			</div>
			<div class="key-display">
				<code>{createdKey.key}</code>
				<button class="btn btn-secondary btn-sm" onclick={() => copyToClipboard(createdKey!.key)}>
					Copy
				</button>
			</div>
			<div class="modal-actions">
				<button class="btn btn-primary" onclick={closeCreatedKeyModal}>
					Done
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.page-header {
		margin-bottom: 2rem;
	}

	.page-header h1 {
		font-size: 1.75rem;
		margin: 0 0 0.5rem 0;
	}

	.page-header p {
		color: var(--text-muted);
		margin: 0;
	}

	.error-banner {
		background: #fef2f2;
		color: #dc2626;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		border: 1px solid #fecaca;
	}

	.card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem 1.5rem;
		border-bottom: 1px solid var(--border);
	}

	.card-header h2 {
		font-size: 1rem;
		margin: 0;
	}

	.loading,
	.empty-state {
		padding: 2rem;
		text-align: center;
		color: var(--text-muted);
	}

	.table {
		width: 100%;
		border-collapse: collapse;
	}

	.table th,
	.table td {
		padding: 0.75rem 1rem;
		text-align: left;
		border-bottom: 1px solid var(--border);
	}

	.table th {
		font-weight: 500;
		color: var(--text-muted);
		font-size: 0.875rem;
	}

	.key-name {
		display: block;
		font-weight: 500;
	}

	.key-description {
		display: block;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}

	.status-badge {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
		background: #fef2f2;
		color: #dc2626;
	}

	.status-badge.active {
		background: #f0fdf4;
		color: #16a34a;
	}

	.btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		border: none;
		transition: all 0.15s ease;
	}

	.btn-sm {
		padding: 0.375rem 0.75rem;
		font-size: 0.8125rem;
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
		border: 1px solid var(--border);
	}

	.btn-secondary:hover {
		background: var(--surface-hover, #f3f4f6);
	}

	.btn-danger {
		background: #fef2f2;
		color: #dc2626;
	}

	.btn-danger:hover {
		background: #fee2e2;
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal {
		background: var(--surface);
		border-radius: 12px;
		padding: 1.5rem;
		width: 100%;
		max-width: 440px;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
	}

	.modal h2 {
		margin: 0 0 1.5rem 0;
		font-size: 1.25rem;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.form-group label {
		display: block;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.form-group input {
		width: 100%;
		padding: 0.625rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.modal-actions {
		display: flex;
		gap: 0.75rem;
		justify-content: flex-end;
		margin-top: 1.5rem;
	}

	.warning-banner {
		background: #fef3c7;
		color: #92400e;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		font-size: 0.875rem;
	}

	.key-display {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: #f3f4f6;
		padding: 0.75rem 1rem;
		border-radius: 6px;
	}

	.key-display code {
		flex: 1;
		font-size: 0.8125rem;
		word-break: break-all;
	}
</style>
