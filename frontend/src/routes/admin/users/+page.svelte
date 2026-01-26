<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { getAuthState } from '$lib/auth.svelte';
	import type { User, UserRole } from '$lib/types';

	const auth = getAuthState();

	let users = $state<User[]>([]);
	let total = $state(0);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let editingUser = $state<User | null>(null);
	let editRole = $state<UserRole>('viewer');
	let editIsActive = $state(true);

	onMount(async () => {
		if (!auth.isAuthenticated || !auth.isAdmin) {
			goto('/');
			return;
		}
		await loadUsers();
	});

	async function loadUsers() {
		isLoading = true;
		error = null;
		try {
			const response = await api.auth.admin.getUsers({ limit: 100 });
			users = response.users;
			total = response.total;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load users';
		}
		isLoading = false;
	}

	function startEdit(user: User) {
		editingUser = user;
		editRole = user.role;
		editIsActive = user.is_active;
	}

	function cancelEdit() {
		editingUser = null;
	}

	async function saveEdit() {
		if (!editingUser) return;

		try {
			await api.auth.admin.updateUser(editingUser.id, {
				role: editRole,
				is_active: editIsActive
			});
			await loadUsers();
			editingUser = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update user';
		}
	}

	async function deleteUser(user: User) {
		if (
			!confirm(
				`Are you sure you want to delete ${user.name}? This will also delete all their API keys and sessions.`
			)
		) {
			return;
		}

		try {
			await api.auth.admin.deleteUser(user.id);
			await loadUsers();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete user';
		}
	}
</script>

<svelte:head>
	<title>Manage Users - Community Resilience</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<h1>Manage Users</h1>
		<p>View and manage user accounts and roles.</p>
	</div>

	{#if error}
		<div class="error-banner">
			{error}
		</div>
	{/if}

	<div class="card">
		<div class="card-header">
			<h2>Users ({total})</h2>
		</div>

		{#if isLoading}
			<div class="loading">Loading...</div>
		{:else if users.length === 0}
			<div class="empty-state">
				<p>No users found.</p>
			</div>
		{:else}
			<table class="table">
				<thead>
					<tr>
						<th>User</th>
						<th>Role</th>
						<th>Provider</th>
						<th>Status</th>
						<th>Joined</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each users as user}
						<tr>
							<td>
								<div class="user-info">
									{#if user.avatar_url}
										<img src={user.avatar_url} alt="" class="user-avatar" />
									{:else}
										<span class="user-avatar-placeholder">
											{user.name.charAt(0).toUpperCase()}
										</span>
									{/if}
									<div>
										<span class="user-name">{user.name}</span>
										<span class="user-email">{user.email}</span>
									</div>
								</div>
							</td>
							<td>
								<span class="role-badge role-{user.role}">{user.role}</span>
							</td>
							<td>{user.oauth_provider || '-'}</td>
							<td>
								<span class="status-badge" class:active={user.is_active}>
									{user.is_active ? 'Active' : 'Inactive'}
								</span>
							</td>
							<td>{new Date(user.created_at).toLocaleDateString()}</td>
							<td>
								<div class="actions">
									<button class="btn btn-secondary btn-sm" onclick={() => startEdit(user)}>
										Edit
									</button>
									{#if user.id !== auth.user?.id}
										<button class="btn btn-danger btn-sm" onclick={() => deleteUser(user)}>
											Delete
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>

{#if editingUser}
	<div class="modal-overlay" onclick={cancelEdit}>
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<h2>Edit User</h2>
			<div class="user-info modal-user">
				{#if editingUser.avatar_url}
					<img src={editingUser.avatar_url} alt="" class="user-avatar" />
				{:else}
					<span class="user-avatar-placeholder">
						{editingUser.name.charAt(0).toUpperCase()}
					</span>
				{/if}
				<div>
					<span class="user-name">{editingUser.name}</span>
					<span class="user-email">{editingUser.email}</span>
				</div>
			</div>

			<form
				onsubmit={(e) => {
					e.preventDefault();
					saveEdit();
				}}
			>
				<div class="form-group">
					<label for="role">Role</label>
					<select id="role" bind:value={editRole}>
						<option value="viewer">Viewer</option>
						<option value="editor">Editor</option>
						<option value="admin">Admin</option>
					</select>
				</div>

				<div class="form-group">
					<label class="checkbox-label">
						<input type="checkbox" bind:checked={editIsActive} />
						<span>Account is active</span>
					</label>
				</div>

				<div class="modal-actions">
					<button type="button" class="btn btn-secondary" onclick={cancelEdit}> Cancel </button>
					<button type="submit" class="btn btn-primary"> Save Changes </button>
				</div>
			</form>
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

	.user-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.modal-user {
		margin-bottom: 1.5rem;
		padding: 1rem;
		background: #f3f4f6;
		border-radius: 8px;
	}

	.user-avatar {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		object-fit: cover;
	}

	.user-avatar-placeholder {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--primary);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.user-name {
		display: block;
		font-weight: 500;
	}

	.user-email {
		display: block;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}

	.role-badge {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: capitalize;
	}

	.role-badge.role-admin {
		background: #fef3c7;
		color: #92400e;
	}

	.role-badge.role-editor {
		background: #dbeafe;
		color: #1e40af;
	}

	.role-badge.role-viewer {
		background: #f3f4f6;
		color: #374151;
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

	.actions {
		display: flex;
		gap: 0.5rem;
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

	.btn-primary:hover {
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
		max-width: 400px;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
	}

	.modal h2 {
		margin: 0 0 1rem 0;
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

	.form-group select {
		width: 100%;
		padding: 0.625rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 0.875rem;
		background: white;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		cursor: pointer;
	}

	.checkbox-label input {
		width: 18px;
		height: 18px;
	}

	.modal-actions {
		display: flex;
		gap: 0.75rem;
		justify-content: flex-end;
		margin-top: 1.5rem;
	}
</style>
