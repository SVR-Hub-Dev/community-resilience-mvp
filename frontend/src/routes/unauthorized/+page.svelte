<script lang="ts">
	import { page } from '$app/stores';

	let requiredRole = $derived($page.url.searchParams.get('role') || 'appropriate permissions');
</script>

<svelte:head>
	<title>Access Denied - Community Resilience</title>
</svelte:head>

<div class="container error-container">
	<div class="error-card">
		<div class="error-icon">🔒</div>
		<h1>Access Denied</h1>
		<p>You don't have permission to access this page.</p>
		<p class="error-detail">Required: {requiredRole}</p>

		<div class="error-actions">
			<a href="/" class="btn btn-primary">Go Home</a>
			<a href="/support" class="btn btn-secondary">Contact Support</a>
		</div>
	</div>
</div>

<style>
	.error-container {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
	}

	.error-card {
		text-align: center;
		max-width: 500px;
		padding: 3rem 2rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
	}

	.error-icon {
		font-size: 4rem;
		margin-bottom: 1rem;
	}

	.error-card h1 {
		font-size: 2rem;
		margin-bottom: 1rem;
		color: #dc2626;
	}

	.error-card p {
		color: var(--text-muted);
		margin-bottom: 0.5rem;
	}

	.error-detail {
		font-weight: 600;
		color: var(--text);
	}

	.error-actions {
		display: flex;
		gap: 1rem;
		justify-content: center;
		margin-top: 2rem;
	}

	.btn-secondary {
		background: transparent;
		border: 2px solid var(--border);
		color: var(--text);
	}

	.btn-secondary:hover {
		background: var(--surface-hover);
		border-color: var(--primary);
	}
</style>
