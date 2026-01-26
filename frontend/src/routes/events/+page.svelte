<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { CommunityEvent } from '$lib/types';

	let events: CommunityEvent[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let showForm = $state(false);

	// Form fields
	let eventType = $state('');
	let description = $state('');
	let location = $state('');
	let severity: number | null = $state(null);
	let reportedBy = $state('');

	onMount(async () => {
		await loadEvents();
	});

	async function loadEvents() {
		loading = true;
		error = '';
		try {
			events = await api.getEvents();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load events';
		} finally {
			loading = false;
		}
	}

	function resetForm() {
		eventType = '';
		description = '';
		location = '';
		severity = null;
		reportedBy = '';
		showForm = false;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = '';
		try {
			await api.createEvent({
				event_type: eventType,
				description,
				location: location || null,
				severity,
				reported_by: reportedBy || null
			});
			resetForm();
			await loadEvents();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create event';
		}
	}

	function getSeverityClass(sev: number | null): string {
		if (!sev) return '';
		if (sev >= 4) return 'severity-high';
		if (sev >= 2) return 'severity-medium';
		return 'severity-low';
	}

	function formatDate(timestamp: string): string {
		return new Date(timestamp).toLocaleString();
	}
</script>

<svelte:head>
	<title>Events - Community Resilience</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<div class="header-row">
			<h1>Community Events</h1>
			<button class="btn btn-primary" onclick={() => { resetForm(); showForm = !showForm; }}>
				{showForm ? 'Cancel' : 'Report Event'}
			</button>
		</div>
		<p>Real-time reports from the community during emergencies.</p>
	</div>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	{#if showForm}
		<div class="card form-card">
			<h2>Report New Event</h2>
			<form onsubmit={handleSubmit}>
				<div class="form-row">
					<div class="form-group">
						<label class="label" for="eventType">Event Type *</label>
						<select id="eventType" class="input" bind:value={eventType} required>
							<option value="">Select type...</option>
							<option value="flood">Flood</option>
							<option value="road_closure">Road Closure</option>
							<option value="power_outage">Power Outage</option>
							<option value="evacuation">Evacuation</option>
							<option value="rescue">Rescue Needed</option>
							<option value="shelter">Shelter Update</option>
							<option value="other">Other</option>
						</select>
					</div>
					<div class="form-group">
						<label class="label" for="severity">Severity (1-5)</label>
						<select id="severity" class="input" bind:value={severity}>
							<option value={null}>Select severity...</option>
							<option value={1}>1 - Minor</option>
							<option value={2}>2 - Low</option>
							<option value={3}>3 - Moderate</option>
							<option value={4}>4 - High</option>
							<option value={5}>5 - Critical</option>
						</select>
					</div>
				</div>

				<div class="form-group">
					<label class="label" for="description">Description *</label>
					<textarea id="description" class="textarea" bind:value={description} required
						placeholder="Describe the situation..."></textarea>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label class="label" for="location">Location</label>
						<input id="location" class="input" bind:value={location} placeholder="Where is this happening?" />
					</div>
					<div class="form-group">
						<label class="label" for="reportedBy">Reported By</label>
						<input id="reportedBy" class="input" bind:value={reportedBy} placeholder="Your name (optional)" />
					</div>
				</div>

				<div class="form-actions">
					<button type="button" class="btn btn-secondary" onclick={resetForm}>Cancel</button>
					<button type="submit" class="btn btn-primary">Submit Report</button>
				</div>
			</form>
		</div>
	{/if}

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
		</div>
	{:else if events.length === 0}
		<div class="card empty-state">
			<p>No events reported yet.</p>
		</div>
	{:else}
		<div class="events-list">
			{#each events as event}
				<div class="card event-card {getSeverityClass(event.severity)}">
					<div class="event-header">
						<span class="event-type">{event.event_type.replace('_', ' ')}</span>
						{#if event.severity}
							<span class="badge {event.severity >= 4 ? 'badge-danger' : event.severity >= 2 ? 'badge-warning' : 'badge-primary'}">
								Severity: {event.severity}
							</span>
						{/if}
					</div>
					<p class="event-description">{event.description}</p>
					<div class="event-meta">
						{#if event.location}
							<span>📍 {event.location}</span>
						{/if}
						<span>🕐 {formatDate(event.timestamp)}</span>
						{#if event.reported_by}
							<span>👤 {event.reported_by}</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.page-header {
		margin-bottom: 2rem;
	}

	.header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.header-row h1 {
		font-size: 1.875rem;
		font-weight: 700;
	}

	.page-header p {
		color: var(--text-muted);
	}

	.form-card {
		margin-bottom: 2rem;
	}

	.form-card h2 {
		font-size: 1.25rem;
		margin-bottom: 1.5rem;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		margin-top: 1.5rem;
	}

	select.input {
		cursor: pointer;
	}

	.events-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.event-card {
		border-left: 4px solid var(--border);
	}

	.event-card.severity-high {
		border-left-color: var(--danger);
		background: #fef2f2;
	}

	.event-card.severity-medium {
		border-left-color: var(--warning);
		background: #fffbeb;
	}

	.event-card.severity-low {
		border-left-color: var(--success);
	}

	.event-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
	}

	.event-type {
		font-weight: 600;
		text-transform: capitalize;
	}

	.event-description {
		margin-bottom: 0.75rem;
		line-height: 1.6;
	}

	.event-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.empty-state {
		text-align: center;
		padding: 3rem;
		color: var(--text-muted);
	}

	@media (max-width: 640px) {
		.form-row {
			grid-template-columns: 1fr;
		}
	}
</style>
