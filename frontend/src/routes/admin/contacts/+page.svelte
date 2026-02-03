<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import type { PageData, ActionData } from './$types';

	let { data, form }: { data: PageData; form: ActionData } = $props();

	let expandedId = $state<number | null>(null);

	function formatDateTime(dateStr: string): string {
		return new Date(dateStr).toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit',
		});
	}

	function toggleExpand(id: number) {
		expandedId = expandedId === id ? null : id;
	}

	function handleMarkRead() {
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			await invalidateAll();
		};
	}
</script>

<svelte:head>
	<title>Contact Submissions - Admin</title>
</svelte:head>

<div class="admin-container">
	<div class="header">
		<div>
			<h1>Contact Submissions</h1>
			<p>View messages from the contact form</p>
		</div>
		<a href="/admin/support" class="btn btn-secondary">View Tickets</a>
	</div>

	{#if data.error}
		<div class="error-message">{data.error}</div>
	{/if}

	{#if data.contacts.length === 0}
		<div class="empty-state">
			<div class="empty-icon">📬</div>
			<h2>No Contacts Yet</h2>
			<p>No contact form submissions have been received.</p>
		</div>
	{:else}
		<div class="contacts-list">
			{#each data.contacts as contact (contact.id)}
				<div class="contact-card" class:unread={!contact.is_read}>
					<button type="button" class="contact-header" onclick={() => toggleExpand(contact.id)}>
						<div class="contact-info">
							{#if !contact.is_read}
								<span class="unread-badge">New</span>
							{/if}
							<span class="contact-name">{contact.name}</span>
							<span class="contact-email">&lt;{contact.email}&gt;</span>
						</div>
						<div class="contact-meta">
							<span class="contact-subject">{contact.subject}</span>
							<span class="contact-date">{formatDateTime(contact.created_at)}</span>
						</div>
						<span class="expand-icon">{expandedId === contact.id ? '▼' : '▶'}</span>
					</button>

					{#if expandedId === contact.id}
						<div class="contact-body">
							<div class="contact-message">
								<p>{contact.message}</p>
							</div>

							<div class="contact-actions">
								<a href="mailto:{contact.email}?subject=Re: {contact.subject}" class="btn btn-primary">
									Reply via Email
								</a>

								{#if !contact.is_read}
									<form method="POST" action="?/markRead" use:enhance={handleMarkRead}>
										<input type="hidden" name="contact_id" value={contact.id} />
										<button type="submit" class="btn btn-secondary">Mark as Read</button>
									</form>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
		<div class="list-footer">
			<span>Showing {data.contacts.length} of {data.total} submissions</span>
		</div>
	{/if}
</div>

<style>
	.admin-container {
		max-width: 900px;
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

	.contacts-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.contact-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
	}

	.contact-card.unread {
		border-color: var(--primary);
	}

	.contact-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		width: 100%;
		padding: 1rem 1.25rem;
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
		font-family: inherit;
	}

	.contact-header:hover {
		background: var(--bg);
	}

	.contact-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 200px;
	}

	.unread-badge {
		font-size: 0.6875rem;
		background: var(--primary);
		color: white;
		padding: 0.125rem 0.5rem;
		border-radius: 9999px;
		font-weight: 500;
	}

	.contact-name {
		font-weight: 500;
		color: var(--text);
	}

	.contact-email {
		color: var(--text-muted);
		font-size: 0.875rem;
	}

	.contact-meta {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.contact-subject {
		font-weight: 500;
		color: var(--text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 300px;
	}

	.contact-date {
		color: var(--text-muted);
		font-size: 0.8125rem;
		flex-shrink: 0;
	}

	.expand-icon {
		color: var(--text-muted);
		font-size: 0.75rem;
	}

	.contact-body {
		padding: 0 1.25rem 1.25rem 1.25rem;
		border-top: 1px solid var(--border);
	}

	.contact-message {
		padding: 1rem 0;
	}

	.contact-message p {
		margin: 0;
		line-height: 1.6;
		white-space: pre-wrap;
		color: var(--text);
	}

	.contact-actions {
		display: flex;
		gap: 0.75rem;
	}

	.list-footer {
		padding: 1rem;
		text-align: center;
		font-size: 0.8125rem;
		color: var(--text-muted);
	}

	:global(.dark) .error-message {
		background: #450a0a;
		color: #fca5a5;
		border-color: #dc2626;
	}
</style>
