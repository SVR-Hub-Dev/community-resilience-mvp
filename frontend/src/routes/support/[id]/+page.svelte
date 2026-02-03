<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import type { PageData, ActionData } from './$types';
	import type { TicketStatus, TicketPriority } from '$lib/types';

	let { data, form }: { data: PageData; form: ActionData } = $props();

	let isLoading = $state(false);
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

	function handleEnhance() {
		isLoading = true;
		return async ({ update, result }: { update: () => Promise<void>; result: { type: string } }) => {
			await update();
			isLoading = false;
			if (result.type === 'success') {
				messageText = '';
				await invalidateAll();
			}
		};
	}
</script>

<svelte:head>
	<title>Ticket #{data.ticket.id} - Community Resilience</title>
</svelte:head>

<div class="ticket-container">
	<div class="back-link">
		<a href="/support">&larr; Back to Tickets</a>
	</div>

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
					{data.ticket.priority} priority
				</span>
			</div>
		</div>

		<div class="ticket-meta">
			<span>Created: {formatDateTime(data.ticket.created_at)}</span>
			{#if data.ticket.updated_at !== data.ticket.created_at}
				<span>Updated: {formatDateTime(data.ticket.updated_at)}</span>
			{/if}
			{#if data.ticket.resolved_at}
				<span>Resolved: {formatDateTime(data.ticket.resolved_at)}</span>
			{/if}
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
				<p>No responses yet. Add a message below.</p>
			</div>
		{:else}
			<div class="responses-list">
				{#each data.ticket.responses as response (response.id)}
					<div class="response-card">
						<div class="response-header">
							<span class="response-author">
								{response.user?.name || response.user?.email || 'Unknown User'}
							</span>
							<span class="response-date">{formatDateTime(response.created_at)}</span>
						</div>
						<div class="response-message">{response.message}</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	{#if data.ticket.status !== 'closed'}
		<div class="reply-section">
			<h2>Add Response</h2>

			{#if form?.error}
				<div class="error-message">{form.error}</div>
			{/if}

			<form method="POST" action="?/respond" use:enhance={handleEnhance}>
				<textarea
					name="message"
					placeholder="Type your message..."
					class="form-input"
					rows="4"
					required
					disabled={isLoading}
					bind:value={messageText}
				></textarea>
				<button type="submit" class="btn btn-primary" disabled={isLoading || !messageText.trim()}>
					{isLoading ? 'Sending...' : 'Send Response'}
				</button>
			</form>
		</div>
	{:else}
		<div class="closed-notice">
			<p>This ticket is closed. If you need further assistance, please create a new ticket.</p>
		</div>
	{/if}
</div>

<style>
	.ticket-container {
		max-width: 800px;
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

	.ticket-header-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
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
		font-size: 1.5rem;
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
		flex-wrap: wrap;
	}

	.ticket-description h2 {
		font-size: 0.875rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.ticket-description p {
		margin: 0;
		color: var(--text);
		line-height: 1.6;
		white-space: pre-wrap;
	}

	.responses-section {
		margin-bottom: 1.5rem;
	}

	.responses-section h2 {
		font-size: 1.125rem;
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

	.no-responses p {
		margin: 0;
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

	.reply-section h2 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 1rem 0;
		color: var(--text);
	}

	.reply-section form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
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
		resize: vertical;
	}

	.form-input:focus {
		border-color: var(--primary);
	}

	.error-message {
		background: #fef2f2;
		color: #dc2626;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		font-size: 0.875rem;
		border: 1px solid #fecaca;
	}

	.closed-notice {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		text-align: center;
		color: var(--text-muted);
	}

	.closed-notice p {
		margin: 0;
	}

	:global(.dark) .error-message {
		background: #450a0a;
		color: #fca5a5;
		border-color: #dc2626;
	}

	@media (max-width: 640px) {
		.ticket-header {
			flex-direction: column;
		}

		.ticket-badges {
			flex-wrap: wrap;
		}
	}
</style>
