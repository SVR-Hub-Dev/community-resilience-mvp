<script lang="ts">
	interface Props {
		processingStatus: string;
		processingMode: string;
		needsFullProcessing: boolean;
	}

	let { processingStatus, processingMode, needsFullProcessing }: Props = $props();

	const statusConfig: Record<string, { label: string; class: string }> = {
		completed: { label: 'Fully Processed', class: 'badge-success' },
		needs_local: { label: 'Pending Sync', class: 'badge-warning' },
		pending: { label: 'Pending', class: 'badge-secondary' },
		processing: { label: 'Processing...', class: 'badge-primary' },
		failed: { label: 'Failed', class: 'badge-danger' }
	};

	let status = $derived(statusConfig[processingStatus] ?? { label: processingStatus, class: 'badge-secondary' });
	let modeLabel = $derived(processingMode === 'cloud_basic' ? 'Basic' : processingMode === 'local_full' ? 'Full' : processingMode);
</script>

<span class="badge-group">
	<span class="badge {status.class}">{status.label}</span>
	{#if needsFullProcessing}
		<span class="badge badge-info" title="Full processing will occur when synced to a local instance">
			Awaiting Full Processing
		</span>
	{:else}
		<span class="badge badge-mode">{modeLabel}</span>
	{/if}
</span>

<style>
	.badge-group {
		display: inline-flex;
		flex-wrap: wrap;
		gap: 0.375rem;
		align-items: center;
	}

	.badge {
		display: inline-flex;
		align-items: center;
		padding: 0.2rem 0.625rem;
		border-radius: 9999px;
		font-size: 0.7rem;
		font-weight: 500;
		white-space: nowrap;
	}

	.badge-success {
		background: #dcfce7;
		color: #16a34a;
	}

	.badge-warning {
		background: #fef3c7;
		color: #d97706;
	}

	.badge-danger {
		background: #fee2e2;
		color: #dc2626;
	}

	.badge-primary {
		background: #dbeafe;
		color: #2563eb;
	}

	.badge-secondary {
		background: #f1f5f9;
		color: #64748b;
	}

	.badge-info {
		background: #e0f2fe;
		color: #0284c7;
	}

	.badge-mode {
		background: #f3e8ff;
		color: #7c3aed;
	}

	:global([data-theme='dark']) .badge-success {
		background: #064e3b;
		color: #6ee7b7;
	}
	:global([data-theme='dark']) .badge-warning {
		background: #78350f;
		color: #fcd34d;
	}
	:global([data-theme='dark']) .badge-danger {
		background: #7f1d1d;
		color: #fca5a5;
	}
	:global([data-theme='dark']) .badge-primary {
		background: #1e3a5f;
		color: #93c5fd;
	}
	:global([data-theme='dark']) .badge-secondary {
		background: #334155;
		color: #94a3b8;
	}
	:global([data-theme='dark']) .badge-info {
		background: #0c4a6e;
		color: #7dd3fc;
	}
	:global([data-theme='dark']) .badge-mode {
		background: #3b0764;
		color: #c4b5fd;
	}
</style>
