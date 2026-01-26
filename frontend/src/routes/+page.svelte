<script lang="ts">
	import { api } from '$lib/api';
	import type { QueryResponse } from '$lib/types';

	let situationText = $state('');
	let loading = $state(false);
	let error = $state('');
	let response: QueryResponse | null = $state(null);
	let feedbackSubmitted = $state(false);
	let feedbackRating = $state(0);
	let feedbackComments = $state('');

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!situationText.trim()) return;

		loading = true;
		error = '';
		response = null;
		feedbackSubmitted = false;
		feedbackRating = 0;
		feedbackComments = '';

		try {
			response = await api.query(situationText);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to get recommendations';
		} finally {
			loading = false;
		}
	}

	async function submitFeedback() {
		if (!response || feedbackRating === 0) return;

		try {
			await api.submitFeedback({
				log_id: response.log_id,
				rating: feedbackRating,
				comments: feedbackComments || undefined
			});
			feedbackSubmitted = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to submit feedback';
		}
	}

	function getPriorityClass(priority: number): string {
		if (priority === 1) return 'priority-1';
		if (priority === 2) return 'priority-2';
		return 'priority-3';
	}

	function getPriorityLabel(priority: number): string {
		if (priority === 1) return 'Critical';
		if (priority === 2) return 'High';
		return 'Normal';
	}
</script>

<svelte:head>
	<title>Community Resilience - Query</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<h1>Disaster Response Assistant</h1>
		<p>Describe your current situation to receive prioritized action recommendations based on local community knowledge.</p>
	</div>

	<div class="query-section card">
		<form onsubmit={handleSubmit}>
			<label class="label" for="situation">Current Situation</label>
			<textarea
				id="situation"
				class="textarea"
				bind:value={situationText}
				placeholder="Describe what's happening. Example: Heavy rain, Riverside Street flooding, power out in the area..."
				disabled={loading}
			></textarea>

			<div class="submit-row">
				<button type="submit" class="btn btn-primary" disabled={loading || !situationText.trim()}>
					{#if loading}
						<span class="spinner-small"></span>
						Analyzing...
					{:else}
						Get Recommendations
					{/if}
				</button>
			</div>
		</form>
	</div>

	{#if error}
		<div class="alert alert-error">
			{error}
		</div>
	{/if}

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
		</div>
	{/if}

	{#if response}
		<div class="results">
			<div class="card summary-card">
				<h2>Situation Summary</h2>
				<p>{response.summary}</p>
			</div>

			<div class="actions-section">
				<h2>Recommended Actions</h2>
				<div class="actions-list">
					{#each response.actions as action}
						<div class="action-card card {getPriorityClass(action.priority)}">
							<div class="action-header">
								<span class="badge badge-{action.priority === 1 ? 'danger' : action.priority === 2 ? 'warning' : 'primary'}">
									Priority {action.priority}: {getPriorityLabel(action.priority)}
								</span>
							</div>
							<div class="action-content">
								<p class="action-text">{action.action}</p>
								<p class="action-rationale">{action.rationale}</p>
							</div>
						</div>
					{/each}
				</div>
			</div>

			{#if response.retrieved_knowledge_ids.length > 0}
				<div class="card knowledge-used">
					<h3>Knowledge Used</h3>
					<p>This response was informed by {response.retrieved_knowledge_ids.length} knowledge entries from the community database.</p>
				</div>
			{/if}

			<div class="card feedback-section">
				<h3>Was this helpful?</h3>
				{#if feedbackSubmitted}
					<div class="alert alert-success">
						Thank you for your feedback!
					</div>
				{:else}
					<div class="rating-buttons">
						{#each [1, 2, 3, 4, 5] as rating}
							<button
								type="button"
								class="rating-btn {feedbackRating === rating ? 'active' : ''}"
								onclick={() => feedbackRating = rating}
							>
								{rating}
							</button>
						{/each}
					</div>
					<p class="rating-hint">1 = Not helpful, 5 = Very helpful</p>

					{#if feedbackRating > 0}
						<div class="feedback-form">
							<label class="label" for="comments">Additional comments (optional)</label>
							<textarea
								id="comments"
								class="textarea"
								bind:value={feedbackComments}
								placeholder="What could be improved?"
							></textarea>
							<button type="button" class="btn btn-primary" onclick={submitFeedback}>
								Submit Feedback
							</button>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.page-header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.page-header h1 {
		font-size: 1.875rem;
		font-weight: 700;
		margin-bottom: 0.5rem;
	}

	.page-header p {
		color: var(--text-muted);
		max-width: 600px;
		margin: 0 auto;
	}

	.query-section {
		margin-bottom: 2rem;
	}

	.submit-row {
		margin-top: 1rem;
		display: flex;
		justify-content: flex-end;
	}

	.spinner-small {
		width: 1rem;
		height: 1rem;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.results {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.summary-card h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
	}

	.actions-section h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
	}

	.actions-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.action-card {
		padding: 1rem 1.5rem;
	}

	.action-header {
		margin-bottom: 0.75rem;
	}

	.action-text {
		font-weight: 500;
		margin-bottom: 0.5rem;
	}

	.action-rationale {
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.knowledge-used h3 {
		font-size: 1rem;
		margin-bottom: 0.5rem;
	}

	.knowledge-used p {
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.feedback-section h3 {
		font-size: 1rem;
		margin-bottom: 1rem;
	}

	.rating-buttons {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.rating-btn {
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 50%;
		border: 2px solid var(--border);
		background: var(--surface);
		cursor: pointer;
		font-weight: 600;
		transition: all 0.15s ease;
	}

	.rating-btn:hover {
		border-color: var(--primary);
		color: var(--primary);
	}

	.rating-btn.active {
		background: var(--primary);
		border-color: var(--primary);
		color: white;
	}

	.rating-hint {
		font-size: 0.75rem;
		color: var(--text-muted);
		margin-bottom: 1rem;
	}

	.feedback-form {
		margin-top: 1rem;
	}

	.feedback-form .textarea {
		margin-bottom: 1rem;
	}
</style>
