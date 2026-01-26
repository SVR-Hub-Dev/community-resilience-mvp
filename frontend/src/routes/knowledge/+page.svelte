<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { KnowledgeEntry } from '$lib/types';

	let entries: KnowledgeEntry[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let showForm = $state(false);
	let editingId: number | null = $state(null);

	// Form fields
	let title = $state('');
	let description = $state('');
	let tags = $state('');
	let location = $state('');
	let hazardType = $state('');
	let source = $state('');

	onMount(async () => {
		await loadEntries();
	});

	async function loadEntries() {
		loading = true;
		error = '';
		try {
			entries = await api.getKnowledge();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load knowledge entries';
		} finally {
			loading = false;
		}
	}

	function resetForm() {
		title = '';
		description = '';
		tags = '';
		location = '';
		hazardType = '';
		source = '';
		editingId = null;
		showForm = false;
	}

	function editEntry(entry: KnowledgeEntry) {
		title = entry.title;
		description = entry.description;
		tags = entry.tags?.join(', ') || '';
		location = entry.location || '';
		hazardType = entry.hazard_type || '';
		source = entry.source || '';
		editingId = entry.id;
		showForm = true;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = '';
		const entryData = {
			title,
			description,
			tags: tags.split(',').map(t => t.trim()).filter(Boolean),
			location: location || null,
			hazard_type: hazardType || null,
			source: source || null
		};

		try {
			if (editingId) {
				await api.updateKnowledge(editingId, entryData);
			} else {
				await api.createKnowledge(entryData);
			}
			resetForm();
			await loadEntries();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save entry';
		}
	}

	async function deleteEntry(id: number) {
		if (!confirm('Are you sure you want to delete this entry?')) return;

		try {
			await api.deleteKnowledge(id);
			await loadEntries();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to delete entry';
		}
	}
</script>

<svelte:head>
	<title>Knowledge Base - Community Resilience</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<div class="header-row">
			<h1>Knowledge Base</h1>
			<button class="btn btn-primary" onclick={() => { resetForm(); showForm = !showForm; }}>
				{showForm ? 'Cancel' : 'Add Entry'}
			</button>
		</div>
		<p>Community knowledge entries used for disaster response recommendations.</p>
	</div>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	{#if showForm}
		<div class="card form-card">
			<h2>{editingId ? 'Edit Entry' : 'Add New Entry'}</h2>
			<form onsubmit={handleSubmit}>
				<div class="form-group">
					<label class="label" for="title">Title *</label>
					<input id="title" class="input" bind:value={title} required />
				</div>

				<div class="form-group">
					<label class="label" for="description">Description *</label>
					<textarea id="description" class="textarea" bind:value={description} required></textarea>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label class="label" for="tags">Tags (comma-separated)</label>
						<input id="tags" class="input" bind:value={tags} placeholder="flood, evacuation, elderly" />
					</div>
					<div class="form-group">
						<label class="label" for="hazardType">Hazard Type</label>
						<input id="hazardType" class="input" bind:value={hazardType} placeholder="flood, fire, storm" />
					</div>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label class="label" for="location">Location</label>
						<input id="location" class="input" bind:value={location} placeholder="Riverside Street" />
					</div>
					<div class="form-group">
						<label class="label" for="source">Source</label>
						<input id="source" class="input" bind:value={source} placeholder="Community workshop 2023" />
					</div>
				</div>

				<div class="form-actions">
					<button type="button" class="btn btn-secondary" onclick={resetForm}>Cancel</button>
					<button type="submit" class="btn btn-primary">
						{editingId ? 'Update' : 'Create'} Entry
					</button>
				</div>
			</form>
		</div>
	{/if}

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
		</div>
	{:else if entries.length === 0}
		<div class="card empty-state">
			<p>No knowledge entries yet. Add your first entry to get started.</p>
		</div>
	{:else}
		<div class="entries-grid">
			{#each entries as entry}
				<div class="card entry-card">
					<div class="entry-header">
						<h3>{entry.title}</h3>
						<div class="entry-actions">
							<button class="btn-icon" title="Edit" onclick={() => editEntry(entry)}>
								✏️
							</button>
							<button class="btn-icon" title="Delete" onclick={() => deleteEntry(entry.id)}>
								🗑️
							</button>
						</div>
					</div>
					<p class="entry-description">{entry.description}</p>
					<div class="entry-meta">
						{#if entry.location}
							<span class="meta-item">📍 {entry.location}</span>
						{/if}
						{#if entry.hazard_type}
							<span class="badge badge-warning">{entry.hazard_type}</span>
						{/if}
					</div>
					{#if entry.tags?.length}
						<div class="entry-tags">
							{#each entry.tags as tag}
								<span class="badge badge-primary">{tag}</span>
							{/each}
						</div>
					{/if}
					{#if entry.source}
						<p class="entry-source">Source: {entry.source}</p>
					{/if}
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

	.entries-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1rem;
	}

	.entry-card {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.entry-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 0.5rem;
	}

	.entry-header h3 {
		font-size: 1rem;
		font-weight: 600;
		flex: 1;
	}

	.entry-actions {
		display: flex;
		gap: 0.25rem;
	}

	.btn-icon {
		background: none;
		border: none;
		padding: 0.25rem;
		cursor: pointer;
		opacity: 0.6;
		transition: opacity 0.15s ease;
	}

	.btn-icon:hover {
		opacity: 1;
	}

	.entry-description {
		font-size: 0.875rem;
		color: var(--text-muted);
		line-height: 1.6;
	}

	.entry-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.875rem;
	}

	.meta-item {
		color: var(--text-muted);
	}

	.entry-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.entry-source {
		font-size: 0.75rem;
		color: var(--text-muted);
		font-style: italic;
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

		.entries-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
