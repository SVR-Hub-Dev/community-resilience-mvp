<script lang="ts">
	import type { KGEntity } from '$lib/types';

	let { entity }: { entity: KGEntity } = $props();

	const typeColors: Record<string, string> = {
		HazardType: '#dc2626',
		Community: '#2563eb',
		Agency: '#7c3aed',
		Location: '#059669',
		Resource: '#d97706',
		Action: '#0891b2'
	};

	const typeIcons: Record<string, string> = {
		HazardType: 'H',
		Community: 'C',
		Agency: 'A',
		Location: 'L',
		Resource: 'R',
		Action: 'X'
	};

	let color = $derived(typeColors[entity.entity_type] || '#6b7280');
	let icon = $derived(typeIcons[entity.entity_type] || '?');
	let confidencePercent = $derived(Math.round(entity.confidence_score * 100));
</script>

<a href="/knowledge-graph/{entity.id}" class="entity-card">
	<div class="entity-header">
		<span class="type-icon" style="background: {color}">{icon}</span>
		<div class="entity-info">
			<h3 class="entity-name">{entity.name}</h3>
			<div class="entity-type-row">
				<span class="type-badge" style="color: {color}; border-color: {color}">{entity.entity_type}</span>
				{#if entity.entity_subtype}
					<span class="subtype">{entity.entity_subtype}</span>
				{/if}
			</div>
		</div>
	</div>

	{#if entity.location_text}
		<p class="entity-location">{entity.location_text}</p>
	{/if}

	<div class="entity-footer">
		<div class="confidence">
			<div class="confidence-bar">
				<div class="confidence-fill" style="width: {confidencePercent}%; background: {color}"></div>
			</div>
			<span class="confidence-label">{confidencePercent}%</span>
		</div>
		{#if entity.extraction_method}
			<span class="method-badge">{entity.extraction_method}</span>
		{/if}
	</div>
</a>

<style>
	.entity-card {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		padding: 1.25rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		text-decoration: none;
		color: var(--text);
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}

	.entity-card:hover {
		border-color: var(--primary);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	.entity-header {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
	}

	.type-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		border-radius: 8px;
		color: white;
		font-weight: 700;
		font-size: 0.875rem;
		flex-shrink: 0;
	}

	.entity-info {
		flex: 1;
		min-width: 0;
	}

	.entity-name {
		font-size: 1rem;
		font-weight: 600;
		margin: 0;
		line-height: 1.3;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.entity-type-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 0.25rem;
	}

	.type-badge {
		font-size: 0.7rem;
		font-weight: 600;
		padding: 0.125rem 0.5rem;
		border: 1px solid;
		border-radius: 9999px;
		text-transform: uppercase;
		letter-spacing: 0.025em;
	}

	.subtype {
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	.entity-location {
		font-size: 0.8rem;
		color: var(--text-muted);
		margin: 0;
		padding-left: 0.25rem;
	}

	.entity-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.confidence {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
	}

	.confidence-bar {
		flex: 1;
		height: 4px;
		background: var(--border);
		border-radius: 2px;
		overflow: hidden;
	}

	.confidence-fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.3s ease;
	}

	.confidence-label {
		font-size: 0.7rem;
		font-weight: 600;
		color: var(--text-muted);
		min-width: 2.5rem;
		text-align: right;
	}

	.method-badge {
		font-size: 0.65rem;
		padding: 0.125rem 0.375rem;
		background: var(--surface-hover, #f3f4f6);
		border-radius: 4px;
		color: var(--text-muted);
		white-space: nowrap;
	}
</style>
