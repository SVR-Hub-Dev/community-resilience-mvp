<script lang="ts">
	import type { KGRelationshipDetail } from '$lib/types';

	let {
		relationships,
		direction,
		entityName
	}: {
		relationships: KGRelationshipDetail[];
		direction: 'outgoing' | 'incoming';
		entityName: string;
	} = $props();
</script>

{#if relationships.length === 0}
	<p class="empty">No {direction} relationships.</p>
{:else}
	<ul class="rel-list">
		{#each relationships as rel}
			<li class="rel-item">
				<div class="rel-arrow">
					{#if direction === 'outgoing'}
						<span class="rel-source">{entityName}</span>
						<span class="rel-type">{rel.relationship_type}</span>
						<span class="arrow">&rarr;</span>
						<a href="/knowledge-graph/{rel.entity_id}" class="rel-target">{rel.entity_name}</a>
						<span class="rel-entity-type">({rel.entity_type})</span>
					{:else}
						<a href="/knowledge-graph/{rel.entity_id}" class="rel-source">{rel.entity_name}</a>
						<span class="rel-entity-type">({rel.entity_type})</span>
						<span class="rel-type">{rel.relationship_type}</span>
						<span class="arrow">&rarr;</span>
						<span class="rel-target">{entityName}</span>
					{/if}
				</div>
				<div class="rel-confidence">
					<div class="confidence-bar">
						<div
							class="confidence-fill"
							style="width: {Math.round(rel.confidence_score * 100)}%"
						></div>
					</div>
					<span class="confidence-value">{Math.round(rel.confidence_score * 100)}%</span>
				</div>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.empty {
		color: var(--text-muted);
		font-size: 0.875rem;
		font-style: italic;
	}

	.rel-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.rel-item {
		padding: 0.75rem;
		background: var(--surface-hover, #f9fafb);
		border-radius: 6px;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.rel-arrow {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		font-size: 0.875rem;
	}

	.rel-source,
	.rel-target {
		font-weight: 600;
		color: var(--text);
	}

	a.rel-source,
	a.rel-target {
		color: var(--primary);
		text-decoration: none;
	}

	a.rel-source:hover,
	a.rel-target:hover {
		text-decoration: underline;
	}

	.rel-type {
		font-size: 0.75rem;
		font-weight: 600;
		padding: 0.125rem 0.5rem;
		background: var(--primary);
		color: white;
		border-radius: 9999px;
	}

	.rel-entity-type {
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	.arrow {
		color: var(--text-muted);
		font-size: 1rem;
	}

	.rel-confidence {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.confidence-bar {
		flex: 1;
		height: 3px;
		background: var(--border);
		border-radius: 2px;
		overflow: hidden;
		max-width: 120px;
	}

	.confidence-fill {
		height: 100%;
		background: var(--primary);
		border-radius: 2px;
	}

	.confidence-value {
		font-size: 0.7rem;
		color: var(--text-muted);
		font-weight: 600;
	}
</style>
