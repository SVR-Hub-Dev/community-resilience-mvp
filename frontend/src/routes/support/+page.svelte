<script lang="ts">
	import { enhance } from '$app/forms';
	import type { PageData, ActionData } from './$types';
	import type { SupportTicket, TicketStatus, TicketPriority } from '$lib/types';

	let { data, form }: { data: PageData; form: ActionData } = $props();

	let showCreateForm = $state(false);
	let isLoading = $state(false);

	const statusColors: Record<TicketStatus, string> = {
		open: '#22c55e',
		in_progress: '#f59e0b',
		resolved: '#3b82f6',
		closed: '#6b7280',
	};

	const statusLabels: Record<TicketStatus, string> = {
		open: 'Open',
		in_progress: 'In Progress',
		resolved: 'Resolved',
		closed: 'Closed',
	};

	const priorityColors: Record<TicketPriority, string> = {
		low: '#6b7280',
		medium: '#3b82f6',
		high: '#f59e0b',
		urgent: '#ef4444',
	};

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
		});
	}

	function handleEnhance() {
		isLoading = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isLoading = false;
		};
	}
</script>

<svelte:head>
	<title>Support Tickets - Community Resilience</title>
</svelte:head>

<div class="support-container">
	<div class="header">
		<div>
			<h1>Support Tickets</h1>
			<p>View and manage your support requests</p>
		</div>
		<button class="btn btn-primary" onclick={() => (showCreateForm = !showCreateForm)}>
			{showCreateForm ? 'Cancel' : 'New Ticket'}
		</button>
	</div>

	{#if form?.error}
		<div class="error-message">{form.error}</div>
	{/if}

	{#if showCreateForm}
		<div class="create-form-card">
			<h2>Create New Ticket</h2>
			<form method="POST" action="?/create" use:enhance={handleEnhance}>
				<div class="form-group">
					<label for="subject">Subject</label>
					<input
						type="text"
						id="subject"
						name="subject"
						placeholder="Brief summary of your issue"
						class="form-input"
						required
						disabled={isLoading}
					/>
				</div>

				<div class="form-group">
					<label for="priority">Priority</label>
					<select id="priority" name="priority" class="form-input" disabled={isLoading}>
						<option value="low">Low</option>
						<option value="medium" selected>Medium</option>
						<option value="high">High</option>
						<option value="urgent">Urgent</option>
					</select>
				</div>

				<div class="form-group">
					<label for="description">Description</label>
					<textarea
						id="description"
						name="description"
						placeholder="Describe your issue in detail..."
						class="form-input"
						rows="5"
						required
						disabled={isLoading}
					></textarea>
				</div>

				<button type="submit" class="btn btn-primary" disabled={isLoading}>
					{isLoading ? 'Creating...' : 'Create Ticket'}
				</button>
			</form>
		</div>
	{/if}

	{#if data.tickets.length === 0}
		<div class="empty-state">
			<div class="empty-icon">🎫</div>
			<h2>No Tickets Yet</h2>
			<p>You haven't created any support tickets. Click "New Ticket" to get started.</p>
		</div>
	{:else}
		<div class="tickets-list">
			{#each data.tickets as ticket (ticket.id)}
				<a href="/support/{ticket.id}" class="ticket-card">
					<div class="ticket-header">
						<span class="ticket-id">#{ticket.id}</span>
						<span
							class="status-badge"
							style="background: {statusColors[ticket.status]}20; color: {statusColors[
								ticket.status
							]}"
						>
							{statusLabels[ticket.status]}
						</span>
					</div>
					<h3 class="ticket-subject">{ticket.subject}</h3>
					<div class="ticket-meta">
						<span
							class="priority-badge"
							style="background: {priorityColors[ticket.priority]}20; color: {priorityColors[
								ticket.priority
							]}"
						>
							{ticket.priority}
						</span>
						<span class="ticket-date">{formatDate(ticket.created_at)}</span>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.support-container {
		max-width: 800px;
		margin: 0 auto;
		padding: 2rem;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 2rem;
	}

	.header h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin: 0 0 0.25rem 0;
		color: var(--text);
	}

	.header p {
		color: var(--text-muted);
		margin: 0;
		font-size: 0.9375rem;
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

	.create-form-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 2rem;
	}

	.create-form-card h2 {
		font-size: 1.125rem;
		font-weight: 600;
		margin: 0 0 1.25rem 0;
		color: var(--text);
	}

	.create-form-card form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.form-group label {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text);
	}

	.form-input {
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 0.9375rem;
		background: var(--surface);
		color: var(--text);
		outline: none;
		font-family: inherit;
	}

	.form-input:focus {
		border-color: var(--primary);
	}

	.empty-state {
		text-align: center;
		padding: 4rem 2rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
	}

	.empty-icon {
		font-size: 4rem;
		margin-bottom: 1rem;
	}

	.empty-state h2 {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text);
	}

	.empty-state p {
		color: var(--text-muted);
		margin: 0;
	}

	.tickets-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.ticket-card {
		display: block;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.25rem;
		text-decoration: none;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}

	.ticket-card:hover {
		border-color: var(--primary);
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	}

	.ticket-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.ticket-id {
		font-size: 0.875rem;
		color: var(--text-muted);
		font-weight: 500;
	}

	.status-badge,
	.priority-badge {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.25rem 0.625rem;
		border-radius: 9999px;
		text-transform: capitalize;
	}

	.ticket-subject {
		font-size: 1rem;
		font-weight: 500;
		margin: 0 0 0.75rem 0;
		color: var(--text);
	}

	.ticket-meta {
		display: flex;
		gap: 0.75rem;
		align-items: center;
	}

	.ticket-date {
		font-size: 0.8125rem;
		color: var(--text-muted);
	}

	:global(.dark) .error-message {
		background: #450a0a;
		color: #fca5a5;
		border-color: #dc2626;
	}
</style>
