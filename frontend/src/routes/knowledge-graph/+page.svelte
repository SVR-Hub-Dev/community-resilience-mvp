<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { getAuthState } from '$lib/auth.svelte';
	import KGEntityCard from '$lib/components/KGEntityCard.svelte';
	import type { KGEntity, KGStats } from '$lib/types';

	const ENTITY_TYPES = ['HazardType', 'Community', 'Agency', 'Location', 'Resource', 'Action'];

	const auth = getAuthState();

	let entities: KGEntity[] = $state([]);
	let stats: KGStats | null = $state(null);
	let total = $state(0);
	let loading = $state(true);
	let error = $state('');
	let initialLoadDone = $state(false);

	// Filters
	let selectedType: string = $state('');
	let searchQuery: string = $state('');
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;

	// Wait for auth to be initialized before loading data
	$effect(() => {
		if (auth.isInitialized && !initialLoadDone) {
			if (!auth.isAuthenticated) {
				goto('/auth/login');
				return;
			}
			initialLoadDone = true;
			loadEntities();
			loadStats();
		}
	});

	async function loadEntities() {
		loading = true;
		error = '';
		try {
			const result = await api.knowledgeGraph.getEntities({
				entity_type: selectedType || undefined,
				search: searchQuery || undefined,
				limit: 100
			});
			entities = result.entities;
			total = result.total;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load entities';
		} finally {
			loading = false;
		}
	}

	async function loadStats() {
		try {
			stats = await api.knowledgeGraph.getStatistics();
		} catch {
			// Stats are non-critical, don't block on failure
		}
	}

	function handleTypeFilter(type: string) {
		selectedType = type === selectedType ? '' : type;
		loadEntities();
	}

	function handleSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		searchQuery = target.value;
		if (searchTimeout) clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			loadEntities();
		}, 300);
	}
</script>

<svelte:head>
	<title>Knowledge Graph - Community Resilience</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<div class="header-row">
			<h1>Knowledge Graph</h1>
		</div>
		<p>Structured entities and relationships extracted from community documents.</p>
	</div>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	<!-- Stats cards -->
	{#if stats}
		<div class="stats-row">
			<div class="stat-card">
				<span class="stat-value">{stats.total_entities}</span>
				<span class="stat-label">Entities</span>
			</div>
			<div class="stat-card">
				<span class="stat-value">{stats.total_relationships}</span>
				<span class="stat-label">Relationships</span>
			</div>
			<div class="stat-card">
				<span class="stat-value">{Math.round(stats.avg_confidence * 100)}%</span>
				<span class="stat-label">Avg Confidence</span>
			</div>
			{#each Object.entries(stats.entity_counts) as [type, count]}
				<div class="stat-card stat-card-small">
					<span class="stat-value">{count}</span>
					<span class="stat-label">{type}</span>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Filters -->
	<div class="filters-bar">
		<div class="type-filters">
			<button
				class="filter-btn"
				class:active={selectedType === ''}
				onclick={() => handleTypeFilter('')}
			>
				All
			</button>
			{#each ENTITY_TYPES as type}
				<button
					class="filter-btn"
					class:active={selectedType === type}
					onclick={() => handleTypeFilter(type)}
				>
					{type}
				</button>
			{/each}
		</div>
		<div class="search-box">
			<input
				type="text"
				class="input search-input"
				placeholder="Search entities..."
				value={searchQuery}
				oninput={handleSearchInput}
			/>
		</div>
	</div>

	<!-- Results count -->
	<p class="results-count">
		{total} {total === 1 ? 'entity' : 'entities'} found
		{#if selectedType}
			&middot; filtered by <strong>{selectedType}</strong>
		{/if}
	</p>

	<!-- Entity grid -->
	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
		</div>
	{:else if entities.length === 0}
		<div class="card empty-state">
			<p>No knowledge graph entities found. Upload documents to start extracting structured knowledge.</p>
		</div>
	{:else}
		<div class="entities-grid">
			{#each entities as entity (entity.id)}
				<KGEntityCard {entity} />
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

	/* Stats */
	.stats-row {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.stat-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 1rem 1.5rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.25rem;
		min-width: 100px;
	}

	.stat-card-small {
		padding: 0.75rem 1rem;
		min-width: 80px;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--text);
	}

	.stat-card-small .stat-value {
		font-size: 1.25rem;
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	/* Filters */
	.filters-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1rem;
		flex-wrap: wrap;
	}

	.type-filters {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.filter-btn {
		padding: 0.375rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 6px;
		background: var(--surface);
		color: var(--text-muted);
		font-size: 0.8rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.filter-btn:hover {
		border-color: var(--primary);
		color: var(--primary);
	}

	.filter-btn.active {
		background: var(--primary);
		border-color: var(--primary);
		color: white;
	}

	.search-box {
		min-width: 200px;
	}

	.search-input {
		width: 100%;
	}

	.results-count {
		font-size: 0.875rem;
		color: var(--text-muted);
		margin-bottom: 1rem;
	}

	/* Entity grid */
	.entities-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1rem;
	}

	.empty-state {
		text-align: center;
		padding: 3rem;
		color: var(--text-muted);
	}

	@media (max-width: 640px) {
		.filters-bar {
			flex-direction: column;
			align-items: stretch;
		}

		.entities-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
