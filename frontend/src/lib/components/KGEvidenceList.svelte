<script lang="ts">
	import type { KGEvidence } from '$lib/types';

	let { evidence }: { evidence: KGEvidence[] } = $props();

	let expandedIds: Set<number> = $state(new Set());

	function toggleExpand(id: number) {
		const next = new Set(expandedIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		expandedIds = next;
	}
</script>

{#if evidence.length === 0}
	<p class="empty">No evidence records.</p>
{:else}
	<ul class="evidence-list">
		{#each evidence as item}
			<li class="evidence-item">
				<div class="evidence-header">
					<a href="/documents" class="doc-link">Document #{item.document_id}</a>
					{#if item.extraction_confidence != null}
						<span class="confidence">
							{Math.round(item.extraction_confidence * 100)}% confidence
						</span>
					{/if}
				</div>
				{#if item.evidence_text}
					<div class="evidence-text" class:expanded={expandedIds.has(item.id)}>
						<p>{item.evidence_text}</p>
					</div>
					{#if item.evidence_text.length > 200}
						<button class="expand-btn" onclick={() => toggleExpand(item.id)}>
							{expandedIds.has(item.id) ? 'Show less' : 'Show more'}
						</button>
					{/if}
				{/if}
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

	.evidence-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.evidence-item {
		padding: 0.75rem;
		background: var(--surface-hover, #f9fafb);
		border-radius: 6px;
		border-left: 3px solid var(--primary);
	}

	.evidence-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.doc-link {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--primary);
		text-decoration: none;
	}

	.doc-link:hover {
		text-decoration: underline;
	}

	.confidence {
		font-size: 0.7rem;
		color: var(--text-muted);
		font-weight: 500;
	}

	.evidence-text {
		font-size: 0.85rem;
		color: var(--text);
		line-height: 1.6;
		max-height: 4.8em;
		overflow: hidden;
		transition: max-height 0.3s ease;
	}

	.evidence-text.expanded {
		max-height: none;
	}

	.evidence-text p {
		margin: 0;
	}

	.expand-btn {
		background: none;
		border: none;
		color: var(--primary);
		font-size: 0.75rem;
		cursor: pointer;
		padding: 0.25rem 0;
		margin-top: 0.25rem;
	}

	.expand-btn:hover {
		text-decoration: underline;
	}
</style>
