<script lang="ts">
	import { goto } from '$app/navigation';
	import type { PageData } from './$types';
	import type { TicketStatus, TicketPriority } from '$lib/types';

	let { data }: { data: PageData } = $props();

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

	function applyFilters(event: Event) {
		const form = event.target as HTMLFormElement;
		const formData = new FormData(form);
		const params = new URLSearchParams();

		const status = formData.get('status') as string;
		const priority = formData.get('priority') as string;

		if (status) params.set('status', status);
		if (priority) params.set('priority', priority);

		const query = params.toString();
		goto(`/admin/support${query ? `?${query}` : ''}`, { replaceState: true });
	}
</script>

<svelte:head>
	<title>Manage Support Tickets - Admin</title>
</svelte:head>

<div class="admin-container">
	<div class="header">
		<div>
			<h1>Support Tickets</h1>
			<p>Manage all support tickets</p>
		</div>
		<a href="/admin/contacts" class="btn btn-secondary">View Contacts</a>
	</div>

	<div class="filters-card">
		<form onsubmit={applyFilters} class="filters-form">
			<div class="filter-group">
				<label for="status">Status</label>
				<select id="status" name="status" class="form-input">
					<option value="">All</option>
					<option value="open" selected={data.filters?.status === 'open'}>Open</option>
					<option value="in_progress" selected={data.filters?.status === 'in_progress'}>
						In Progress
					</option>
					<option value="resolved" selected={data.filters?.status === 'resolved'}>Resolved</option>
					<option value="closed" selected={data.filters?.status === 'closed'}>Closed</option>
				</select>
			</div>

			<div class="filter-group">
				<label for="priority">Priority</label>
				<select id="priority" name="priority" class="form-input">
					<option value="">All</option>
					<option value="low" selected={data.filters?.priority === 'low'}>Low</option>
					<option value="medium" selected={data.filters?.priority === 'medium'}>Medium</option>
					<option value="high" selected={data.filters?.priority === 'high'}>High</option>
					<option value="urgent" selected={data.filters?.priority === 'urgent'}>Urgent</option>
				</select>
			</div>

			<button type="submit" class="btn btn-primary">Apply Filters</button>
		</form>
	</div>

	{#if data.error}
		<div class="error-message">{data.error}</div>
	{/if}

	{#if data.tickets.length === 0}
		<div class="empty-state">
			<div class="empty-icon">🎫</div>
			<h2>No Tickets Found</h2>
			<p>No tickets match the current filters.</p>
		</div>
	{:else}
		<div class="tickets-table-container">
			<table class="tickets-table">
				<thead>
					<tr>
						<th>ID</th>
						<th>Subject</th>
						<th>User</th>
						<th>Status</th>
						<th>Priority</th>
						<th>Created</th>
						<th>Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each data.tickets as ticket (ticket.id)}
						<tr>
							<td class="ticket-id">#{ticket.id}</td>
							<td class="ticket-subject">{ticket.subject}</td>
							<td class="ticket-user">User #{ticket.user_id}</td>
							<td>
								<span
									class="status-badge"
									style="background: {statusColors[ticket.status]}20; color: {statusColors[
										ticket.status
									]}"
								>
									{statusLabels[ticket.status]}
								</span>
							</td>
							<td>
								<span
									class="priority-badge"
									style="background: {priorityColors[ticket.priority]}20; color: {priorityColors[
										ticket.priority
									]}"
								>
									{ticket.priority}
								</span>
							</td>
							<td class="ticket-date">{formatDate(ticket.created_at)}</td>
							<td>
								<a href="/admin/support/{ticket.id}" class="btn btn-sm">View</a>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<div class="table-footer">
			<span>Showing {data.tickets.length} of {data.total} tickets</span>
		</div>
	{/if}
</div>

<style>
	.admin-container {
		max-width: 1200px;
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
	}

	.filters-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.25rem;
		margin-bottom: 1.5rem;
	}

	.filters-form {
		display: flex;
		gap: 1rem;
		align-items: flex-end;
		flex-wrap: wrap;
	}

	.filter-group {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.filter-group label {
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text);
	}

	.form-input {
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 0.875rem;
		background: var(--surface);
		color: var(--text);
		min-width: 140px;
	}

	.error-message {
		background: #fef2f2;
		color: #dc2626;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		border: 1px solid #fecaca;
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

	.tickets-table-container {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
	}

	.tickets-table {
		width: 100%;
		border-collapse: collapse;
	}

	.tickets-table th,
	.tickets-table td {
		padding: 0.875rem 1rem;
		text-align: left;
		border-bottom: 1px solid var(--border);
	}

	.tickets-table th {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
		background: var(--bg);
	}

	.tickets-table tbody tr:last-child td {
		border-bottom: none;
	}

	.tickets-table tbody tr:hover {
		background: var(--bg);
	}

	.ticket-id {
		font-weight: 500;
		color: var(--text-muted);
	}

	.ticket-subject {
		font-weight: 500;
		color: var(--text);
		max-width: 300px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.ticket-user {
		color: var(--text-muted);
		font-size: 0.875rem;
	}

	.ticket-date {
		color: var(--text-muted);
		font-size: 0.875rem;
	}

	.status-badge,
	.priority-badge {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.25rem 0.625rem;
		border-radius: 9999px;
		text-transform: capitalize;
		display: inline-block;
	}

	.btn-sm {
		padding: 0.375rem 0.75rem;
		font-size: 0.8125rem;
	}

	.table-footer {
		padding: 0.75rem 1rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-top: none;
		border-radius: 0 0 12px 12px;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}

	:global(.dark) .error-message {
		background: #450a0a;
		color: #fca5a5;
		border-color: #dc2626;
	}
</style>
