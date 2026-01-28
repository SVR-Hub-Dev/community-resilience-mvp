<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { api } from '$lib/api';
	import KGRelationshipList from '$lib/components/KGRelationshipList.svelte';
	import KGEvidenceList from '$lib/components/KGEvidenceList.svelte';
	import type { KGEntityDetail } from '$lib/types';

	let entity = $state<KGEntityDetail | null>(null);
	let loading = $state(true);
	let error = $state('');

	const typeColors: Record<string, string> = {
		HazardType: '#dc2626',
		Community: '#2563eb',
		Agency: '#7c3aed',
		Location: '#059669',
		Resource: '#d97706',
		Action: '#0891b2'
	};

	let color = $derived(entity ? typeColors[entity.entity_type] || '#6b7280' : '#6b7280');
	let confidencePercent = $derived(entity ? Math.round(entity.confidence_score * 100) : 0);

	onMount(async () => {
		const id = Number($page.params.id);
		if (isNaN(id)) {
			error = 'Invalid entity ID';
			loading = false;
			return;
		}

		try {
			entity = await api.knowledgeGraph.getEntity(id);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load entity';
		} finally {
			loading = false;
		}
	});

	let attributeEntries = $derived(
		entity?.attributes ? Object.entries(entity.attributes).filter(([, v]) => v != null) : []
	);
</script>

<svelte:head>
	<title>{entity?.name || 'Entity'} - Knowledge Graph</title>
</svelte:head>

<div class="container">
	<!-- Breadcrumb -->
	<nav class="breadcrumb">
		<a href="/knowledge-graph">Knowledge Graph</a>
		<span class="sep">/</span>
		<span>{entity?.name || 'Loading...'}</span>
	</nav>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
		</div>
	{:else if entity}
		<!-- Entity header -->
		<div class="entity-header">
			<div class="header-main">
				<h1>{entity.name}</h1>
				<div class="header-badges">
					<span class="type-badge" style="color: {color}; border-color: {color}">
						{entity.entity_type}
					</span>
					{#if entity.entity_subtype}
						<span class="subtype-badge">{entity.entity_subtype}</span>
					{/if}
					{#if entity.extraction_method}
						<span class="method-badge">{entity.extraction_method}</span>
					{/if}
				</div>
			</div>
			<div class="header-confidence">
				<span class="confidence-label">Confidence</span>
				<div class="confidence-bar-large">
					<div
						class="confidence-fill-large"
						style="width: {confidencePercent}%; background: {color}"
					></div>
				</div>
				<span class="confidence-value" style="color: {color}">{confidencePercent}%</span>
			</div>
		</div>

		<!-- Info section -->
		<div class="detail-grid">
			<!-- Left column: attributes & location -->
			<div class="detail-section">
				{#if entity.location_text}
					<div class="card info-card">
						<h2>Location</h2>
						<p>{entity.location_text}</p>
					</div>
				{/if}

				{#if attributeEntries.length > 0}
					<div class="card info-card">
						<h2>Attributes</h2>
						<dl class="attrs-list">
							{#each attributeEntries as [key, value]}
								<div class="attr-row">
									<dt>{key}</dt>
									<dd>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd>
								</div>
							{/each}
						</dl>
					</div>
				{/if}

				<!-- Evidence -->
				<div class="card info-card">
					<h2>Evidence ({entity.evidence.length})</h2>
					<KGEvidenceList evidence={entity.evidence} />
				</div>
			</div>

			<!-- Right column: relationships -->
			<div class="detail-section">
				<div class="card info-card">
					<h2>Outgoing Relationships ({entity.outgoing_relationships.length})</h2>
					<KGRelationshipList
						relationships={entity.outgoing_relationships}
						direction="outgoing"
						entityName={entity.name}
					/>
				</div>

				<div class="card info-card">
					<h2>Incoming Relationships ({entity.incoming_relationships.length})</h2>
					<KGRelationshipList
						relationships={entity.incoming_relationships}
						direction="incoming"
						entityName={entity.name}
					/>
				</div>
			</div>
		</div>

		<!-- Metadata footer -->
		<div class="meta-footer">
			{#if entity.created_at}
				<span>Created: {new Date(entity.created_at).toLocaleDateString()}</span>
			{/if}
			{#if entity.updated_at}
				<span>Updated: {new Date(entity.updated_at).toLocaleDateString()}</span>
			{/if}
		</div>
	{/if}
</div>

<style>
	.breadcrumb {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.breadcrumb a {
		color: var(--primary);
		text-decoration: none;
	}

	.breadcrumb a:hover {
		text-decoration: underline;
	}

	.breadcrumb .sep {
		color: var(--border);
	}

	/* Entity header */
	.entity-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 2rem;
		margin-bottom: 2rem;
		flex-wrap: wrap;
	}

	.header-main h1 {
		font-size: 1.875rem;
		font-weight: 700;
		margin: 0 0 0.75rem 0;
	}

	.header-badges {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.type-badge {
		font-size: 0.75rem;
		font-weight: 600;
		padding: 0.25rem 0.75rem;
		border: 1.5px solid;
		border-radius: 9999px;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.subtype-badge {
		font-size: 0.75rem;
		padding: 0.25rem 0.625rem;
		background: var(--surface-hover, #f3f4f6);
		border-radius: 6px;
		color: var(--text-muted);
	}

	.method-badge {
		font-size: 0.7rem;
		padding: 0.2rem 0.5rem;
		background: var(--surface-hover, #f3f4f6);
		border-radius: 4px;
		color: var(--text-muted);
	}

	.header-confidence {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-width: 200px;
	}

	.confidence-label {
		font-size: 0.8rem;
		color: var(--text-muted);
		font-weight: 500;
		white-space: nowrap;
	}

	.confidence-bar-large {
		flex: 1;
		height: 8px;
		background: var(--border);
		border-radius: 4px;
		overflow: hidden;
	}

	.confidence-fill-large {
		height: 100%;
		border-radius: 4px;
		transition: width 0.3s ease;
	}

	.confidence-value {
		font-size: 1.125rem;
		font-weight: 700;
		min-width: 3rem;
		text-align: right;
	}

	/* Detail grid */
	.detail-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	.detail-section {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.info-card h2 {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 1rem;
		color: var(--text);
	}

	.info-card p {
		font-size: 0.9rem;
		color: var(--text);
		line-height: 1.6;
		margin: 0;
	}

	/* Attributes */
	.attrs-list {
		margin: 0;
	}

	.attr-row {
		display: flex;
		gap: 1rem;
		padding: 0.5rem 0;
		border-bottom: 1px solid var(--border);
	}

	.attr-row:last-child {
		border-bottom: none;
	}

	.attr-row dt {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--text-muted);
		min-width: 120px;
		text-transform: capitalize;
	}

	.attr-row dd {
		font-size: 0.85rem;
		color: var(--text);
		margin: 0;
	}

	/* Meta footer */
	.meta-footer {
		display: flex;
		gap: 2rem;
		font-size: 0.8rem;
		color: var(--text-muted);
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}

	@media (max-width: 768px) {
		.detail-grid {
			grid-template-columns: 1fr;
		}

		.entity-header {
			flex-direction: column;
		}

		.header-confidence {
			min-width: unset;
			width: 100%;
		}
	}
</style>
