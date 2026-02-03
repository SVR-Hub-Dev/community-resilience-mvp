<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import type { PageData, ActionData } from './$types';
	import type { TicketStatus, TicketPriority } from '$lib/types';

	let { data, form }: { data: PageData; form: ActionData } = $props();

	let isUpdating = $state(false);
	let isResponding = $state(false);
	let messageText = $state('');

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

	function formatDateTime(dateStr: string): string {
		return new Date(dateStr).toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit',
		});
	}

	function handleUpdateEnhance() {
		isUpdating = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isUpdating = false;
			await invalidateAll();
		};
	}

	function handleRespondEnhance() {
		isResponding = true;
		return async ({ update, result }: { update: () => Promise<void>; result: { type: string } }) => {
			await update();
			isResponding = false;
			if (result.type === 'success') {
				messageText = '';
				await invalidateAll();
			}
		};
	}
</script>

<svelte:head>
	<title>Admin: Ticket #{data.ticket.id} - Community Resilience</title>
</svelte:head>

<div class="admin-ticket-container">
	<div class="back-link">
		<a href="/admin/support">&larr; Back to Tickets</a>
	</div>

	<div class="ticket-layout">
		<div class="ticket-main">
			<div class="ticket-header-card">
				<div class="ticket-header">
					<div class="ticket-title">
						<span class="ticket-id">Ticket #{data.ticket.id}</span>
						<h1>{data.ticket.subject}</h1>
					</div>
					<div class="ticket-badges">
						<span
							class="status-badge"
							style="background: {statusColors[data.ticket.status]}20; color: {statusColors[
								data.ticket.status
							]}"
						>
							{statusLabels[data.ticket.status]}
						</span>
						<span
							class="priority-badge"
							style="background: {priorityColors[data.ticket.priority]}20; color: {priorityColors[
								data.ticket.priority
							]}"
						>
							{data.ticket.priority}
						</span>
					</div>
				</div>

				<div class="ticket-meta">
					<span>From: {data.ticket.user?.email || `User #${data.ticket.user_id}`}</span>
					<span>Created: {formatDateTime(data.ticket.created_at)}</span>
				</div>

				<div class="ticket-description">
					<h2>Description</h2>
					<p>{data.ticket.description}</p>
				</div>
			</div>

			<div class="responses-section">
				<h2>Responses ({data.ticket.responses.length})</h2>

				{#if data.ticket.responses.length === 0}
					<div class="no-responses">
						<p>No responses yet.</p>
					</div>
				{:else}
					<div class="responses-list">
						{#each data.ticket.responses as response (response.id)}
							<div class="response-card" class:internal={response.is_internal}>
								<div class="response-header">
									<span class="response-author">
										{response.user?.name || response.user?.email || 'Unknown'}
										{#if response.is_internal}
											<span class="internal-badge">Internal Note</span>
										{/if}
									</span>
									<span class="response-date">{formatDateTime(response.created_at)}</span>
								</div>
								<div class="response-message">{response.message}</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<div class="reply-section">
				<h2>Add Response</h2>

				{#if form?.responseError}
					<div class="error-message">{form.responseError}</div>
				{/if}

				<form method="POST" action="?/respond" use:enhance={handleRespondEnhance}>
					<textarea
						name="message"
						placeholder="Type your response..."
						class="form-input"
						rows="4"
						required
						disabled={isResponding}
						bind:value={messageText}
					></textarea>

					<div class="response-options">
						<label class="checkbox-label">
							<input type="checkbox" name="is_internal" />
							<span>Internal note (not visible to user)</span>
						</label>

						<button
							type="submit"
							class="btn btn-primary"
							disabled={isResponding || !messageText.trim()}
						>
							{isResponding ? 'Sending...' : 'Send Response'}
						</button>
					</div>
				</form>
			</div>
		</div>

		<div class="ticket-sidebar">
			<div class="sidebar-card">
				<h3>Manage Ticket</h3>

				{#if form?.updateSuccess}
					<div class="success-message">Ticket updated!</div>
				{/if}
				{#if form?.updateError}
					<div class="error-message">{form.updateError}</div>
				{/if}

				<form method="POST" action="?/update" use:enhance={handleUpdateEnhance}>
					<div class="form-group">
						<label for="status">Status</label>
						<select
							id="status"
							name="status"
							class="form-input"
							disabled={isUpdating}
						>
							<option value="open" selected={data.ticket.status === 'open'}>Open</option>
							<option value="in_progress" selected={data.ticket.status === 'in_progress'}>
								In Progress
							</option>
							<option value="resolved" selected={data.ticket.status === 'resolved'}>Resolved</option>
							<option value="closed" selected={data.ticket.status === 'closed'}>Closed</option>
						</select>
					</div>

					<div class="form-group">
						<label for="priority">Priority</label>
						<select
							id="priority"
							name="priority"
							class="form-input"
							disabled={isUpdating}
						>
							<option value="low" selected={data.ticket.priority === 'low'}>Low</option>
							<option value="medium" selected={data.ticket.priority === 'medium'}>Medium</option>
							<option value="high" selected={data.ticket.priority === 'high'}>High</option>
							<option value="urgent" selected={data.ticket.priority === 'urgent'}>Urgent</option>
						</select>
					</div>

					{#if data.admins && data.admins.length > 0}
						<div class="form-group">
							<label for="assigned_to">Assign To</label>
							<select
								id="assigned_to"
								name="assigned_to"
								class="form-input"
								disabled={isUpdating}
							>
								<option value="">Unassigned</option>
								{#each data.admins as admin (admin.id)}
									<option value={admin.id} selected={data.ticket.assigned_to === admin.id}>
										{admin.name || admin.email}
									</option>
								{/each}
							</select>
						</div>
					{/if}

					<button type="submit" class="btn btn-primary" disabled={isUpdating}>
						{isUpdating ? 'Updating...' : 'Update Ticket'}
					</button>
				</form>
			</div>

			<div class="sidebar-card info-card">
				<h3>Ticket Info</h3>
				<dl>
					<dt>Created</dt>
					<dd>{formatDateTime(data.ticket.created_at)}</dd>

					<dt>Updated</dt>
					<dd>{formatDateTime(data.ticket.updated_at)}</dd>

					{#if data.ticket.resolved_at}
						<dt>Resolved</dt>
						<dd>{formatDateTime(data.ticket.resolved_at)}</dd>
					{/if}

					{#if data.ticket.assignee}
						<dt>Assigned To</dt>
						<dd>{data.ticket.assignee.name || data.ticket.assignee.email}</dd>
					{/if}
				</dl>
			</div>
		</div>
	</div>
</div>

<style>
	.admin-ticket-container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}

	.back-link {
		margin-bottom: 1.5rem;
	}

	.back-link a {
		color: var(--text-muted);
		text-decoration: none;
		font-size: 0.875rem;
	}

	.back-link a:hover {
		color: var(--text);
	}

	.ticket-layout {
		display: grid;
		grid-template-columns: 1fr 300px;
		gap: 1.5rem;
	}

	.ticket-main {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.ticket-header-card,
	.sidebar-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
	}

	.ticket-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.ticket-title {
		flex: 1;
	}

	.ticket-id {
		font-size: 0.875rem;
		color: var(--text-muted);
		font-weight: 500;
	}

	.ticket-title h1 {
		font-size: 1.375rem;
		font-weight: 600;
		margin: 0.25rem 0 0 0;
		color: var(--text);
	}

	.ticket-badges {
		display: flex;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.status-badge,
	.priority-badge {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.375rem 0.75rem;
		border-radius: 9999px;
		text-transform: capitalize;
	}

	.ticket-meta {
		display: flex;
		gap: 1.5rem;
		font-size: 0.8125rem;
		color: var(--text-muted);
		margin-bottom: 1.5rem;
	}

	.ticket-description h2 {
		font-size: 0.75rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.ticket-description p {
		margin: 0;
		color: var(--text);
		line-height: 1.6;
		white-space: pre-wrap;
	}

	.responses-section h2,
	.reply-section h2 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 1rem 0;
		color: var(--text);
	}

	.no-responses {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2rem;
		text-align: center;
		color: var(--text-muted);
	}

	.responses-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.response-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1rem;
	}

	.response-card.internal {
		background: #fefce8;
		border-color: #fde047;
	}

	:global(.dark) .response-card.internal {
		background: #422006;
		border-color: #854d0e;
	}

	.response-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.response-author {
		font-weight: 500;
		color: var(--text);
		font-size: 0.875rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.internal-badge {
		font-size: 0.6875rem;
		background: #fde047;
		color: #854d0e;
		padding: 0.125rem 0.5rem;
		border-radius: 9999px;
		font-weight: 500;
	}

	.response-date {
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	.response-message {
		color: var(--text);
		line-height: 1.5;
		white-space: pre-wrap;
	}

	.reply-section {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
	}

	.reply-section form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.response-options {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		color: var(--text);
		cursor: pointer;
	}

	.sidebar-card h3 {
		font-size: 0.875rem;
		font-weight: 600;
		margin: 0 0 1rem 0;
		color: var(--text);
	}

	.sidebar-card form {
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
		font-size: 0.8125rem;
		font-weight: 500;
		color: var(--text);
	}

	.form-input {
		padding: 0.625rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 0.875rem;
		background: var(--surface);
		color: var(--text);
		font-family: inherit;
	}

	.form-input:focus {
		border-color: var(--primary);
		outline: none;
	}

	textarea.form-input {
		resize: vertical;
	}

	.info-card {
		margin-top: 1rem;
	}

	.info-card dl {
		margin: 0;
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.5rem 1rem;
	}

	.info-card dt {
		font-size: 0.8125rem;
		color: var(--text-muted);
	}

	.info-card dd {
		margin: 0;
		font-size: 0.8125rem;
		color: var(--text);
	}

	.success-message {
		background: #f0fdf4;
		color: #166534;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		margin-bottom: 1rem;
		font-size: 0.8125rem;
		border: 1px solid #bbf7d0;
	}

	.error-message {
		background: #fef2f2;
		color: #dc2626;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
		margin-bottom: 1rem;
		font-size: 0.8125rem;
		border: 1px solid #fecaca;
	}

	:global(.dark) .success-message {
		background: #052e16;
		color: #86efac;
		border-color: #166534;
	}

	:global(.dark) .error-message {
		background: #450a0a;
		color: #fca5a5;
		border-color: #dc2626;
	}

	@media (max-width: 900px) {
		.ticket-layout {
			grid-template-columns: 1fr;
		}

		.ticket-sidebar {
			order: -1;
		}
	}
</style>
