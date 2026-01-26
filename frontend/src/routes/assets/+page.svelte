<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { CommunityAsset } from '$lib/types';

	let assets: CommunityAsset[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let showForm = $state(false);

	// Form fields
	let name = $state('');
	let assetType = $state('');
	let description = $state('');
	let location = $state('');
	let capacity: number | null = $state(null);
	let status = $state('');
	let tags = $state('');

	onMount(async () => {
		await loadAssets();
	});

	async function loadAssets() {
		loading = true;
		error = '';
		try {
			assets = await api.getAssets();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load assets';
		} finally {
			loading = false;
		}
	}

	function resetForm() {
		name = '';
		assetType = '';
		description = '';
		location = '';
		capacity = null;
		status = '';
		tags = '';
		showForm = false;
	}

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = '';
		try {
			await api.createAsset({
				name,
				asset_type: assetType,
				description: description || null,
				location: location || null,
				capacity,
				status: status || null,
				tags: tags.split(',').map(t => t.trim()).filter(Boolean)
			});
			resetForm();
			await loadAssets();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create asset';
		}
	}

	function getStatusClass(st: string | null): string {
		if (!st) return '';
		switch (st.toLowerCase()) {
			case 'available': return 'status-available';
			case 'in_use': return 'status-in-use';
			case 'unavailable': return 'status-unavailable';
			default: return '';
		}
	}
</script>

<svelte:head>
	<title>Assets - Community Resilience</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<div class="header-row">
			<h1>Community Assets</h1>
			<button class="btn btn-primary" onclick={() => { resetForm(); showForm = !showForm; }}>
				{showForm ? 'Cancel' : 'Add Asset'}
			</button>
		</div>
		<p>Resources and facilities available during emergencies.</p>
	</div>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	{#if showForm}
		<div class="card form-card">
			<h2>Add New Asset</h2>
			<form onsubmit={handleSubmit}>
				<div class="form-row">
					<div class="form-group">
						<label class="label" for="name">Name *</label>
						<input id="name" class="input" bind:value={name} required placeholder="e.g., Hilltop Community Hall" />
					</div>
					<div class="form-group">
						<label class="label" for="assetType">Asset Type *</label>
						<select id="assetType" class="input" bind:value={assetType} required>
							<option value="">Select type...</option>
							<option value="shelter">Shelter</option>
							<option value="vehicle">Vehicle</option>
							<option value="equipment">Equipment</option>
							<option value="supplies">Supplies</option>
							<option value="facility">Facility</option>
							<option value="other">Other</option>
						</select>
					</div>
				</div>

				<div class="form-group">
					<label class="label" for="description">Description</label>
					<textarea id="description" class="textarea" bind:value={description}
						placeholder="Describe the asset, capabilities, access information..."></textarea>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label class="label" for="location">Location</label>
						<input id="location" class="input" bind:value={location} placeholder="Address or area" />
					</div>
					<div class="form-group">
						<label class="label" for="capacity">Capacity</label>
						<input id="capacity" class="input" type="number" bind:value={capacity} placeholder="Number of people/items" />
					</div>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label class="label" for="status">Status</label>
						<select id="status" class="input" bind:value={status}>
							<option value="">Select status...</option>
							<option value="available">Available</option>
							<option value="in_use">In Use</option>
							<option value="unavailable">Unavailable</option>
						</select>
					</div>
					<div class="form-group">
						<label class="label" for="tags">Tags (comma-separated)</label>
						<input id="tags" class="input" bind:value={tags} placeholder="generator, accessible, medical" />
					</div>
				</div>

				<div class="form-actions">
					<button type="button" class="btn btn-secondary" onclick={resetForm}>Cancel</button>
					<button type="submit" class="btn btn-primary">Add Asset</button>
				</div>
			</form>
		</div>
	{/if}

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
		</div>
	{:else if assets.length === 0}
		<div class="card empty-state">
			<p>No community assets registered yet.</p>
		</div>
	{:else}
		<div class="assets-grid">
			{#each assets as asset}
				<div class="card asset-card">
					<div class="asset-header">
						<h3>{asset.name}</h3>
						{#if asset.status}
							<span class="badge {getStatusClass(asset.status)}">
								{asset.status.replace('_', ' ')}
							</span>
						{/if}
					</div>
					<span class="asset-type">{asset.asset_type}</span>
					{#if asset.description}
						<p class="asset-description">{asset.description}</p>
					{/if}
					<div class="asset-meta">
						{#if asset.location}
							<span>📍 {asset.location}</span>
						{/if}
						{#if asset.capacity}
							<span>👥 Capacity: {asset.capacity}</span>
						{/if}
					</div>
					{#if asset.tags?.length}
						<div class="asset-tags">
							{#each asset.tags as tag}
								<span class="badge badge-primary">{tag}</span>
							{/each}
						</div>
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

	select.input {
		cursor: pointer;
	}

	.assets-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 1rem;
	}

	.asset-card {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.asset-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 0.5rem;
	}

	.asset-header h3 {
		font-size: 1rem;
		font-weight: 600;
	}

	.asset-type {
		font-size: 0.75rem;
		text-transform: uppercase;
		color: var(--text-muted);
		font-weight: 500;
	}

	.asset-description {
		font-size: 0.875rem;
		color: var(--text-muted);
		line-height: 1.6;
	}

	.asset-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.asset-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 0.25rem;
	}

	.status-available {
		background: #dcfce7;
		color: #16a34a;
	}

	.status-in-use {
		background: #fef3c7;
		color: #d97706;
	}

	.status-unavailable {
		background: #fee2e2;
		color: #dc2626;
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

		.assets-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
