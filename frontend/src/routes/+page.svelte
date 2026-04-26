<script lang="ts">
	import { page } from '$app/stores';
	import { getAuthHelpers } from '$lib/auth.svelte';
	import { api } from '$lib/api';
	import type { QueryResponse } from '$lib/types';

	let auth = $derived(getAuthHelpers($page.data.user));

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
	<title>Community Resilience{auth.isAuthenticated ? ' - Query' : ''}</title>
</svelte:head>

{#if auth.isAuthenticated}
	<!-- Query Interface for Authenticated Users -->
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
{:else}
	<!-- Landing Page for Unauthenticated Users -->
	<div class="landing-container">
		<section class="hero">
			<h1>Batlow Community Resilience Hub</h1>
			<p class="hero-subtitle">
				Your local disaster response knowledge base powered by AI
			</p>
			<div class="hero-actions">
				<a href="/auth/login" class="btn btn-primary btn-large">
					Sign In to Get Started
				</a>
				<a href="/auth/register" class="btn btn-secondary btn-large">
					Create Account
				</a>
			</div>
		</section>

		<section class="features">
			<h2>How It Helps Your Community</h2>
			<div class="feature-grid">
				<div class="feature-card">
					<div class="feature-icon">🔍</div>
					<h3>AI-Powered Recommendations</h3>
					<p>Get prioritized action plans based on local knowledge and past events.</p>
				</div>
				<div class="feature-card">
					<div class="feature-icon">📚</div>
					<h3>Community Knowledge Base</h3>
					<p>Access curated information about local hazards, resources, and best practices.</p>
				</div>
				<div class="feature-card">
					<div class="feature-icon">🗺️</div>
					<h3>Knowledge Graph</h3>
					<p>Visualize connections between events, locations, and community assets.</p>
				</div>
				<div class="feature-card">
					<div class="feature-icon">📄</div>
					<h3>Document Management</h3>
					<p>Upload and process emergency plans, reports, and community documents.</p>
				</div>
			</div>
		</section>

		<section class="cta">
			<h2>Ready to Enhance Community Resilience?</h2>
			<p>Sign in to access the disaster response assistant and community resources.</p>
			<a href="/auth/login" class="btn btn-primary btn-large">Get Started</a>
		</section>

		<section class="public-contact">
			<p>Have questions? <a href="/contact">Contact us</a></p>
		</section>
	</div>
{/if}

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

	/* Landing Page Styles */
	.landing-container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem 1rem;
	}

	.hero {
		text-align: center;
		padding: 4rem 2rem;
		background: linear-gradient(135deg, #eff6ff 0%, var(--surface) 100%);
		border-radius: 12px;
		margin-bottom: 3rem;
	}

	.hero h1 {
		font-size: 2.5rem;
		font-weight: 700;
		margin-bottom: 1rem;
		color: var(--primary);
	}

	.hero-subtitle {
		font-size: 1.25rem;
		color: var(--text-muted);
		margin-bottom: 2rem;
		max-width: 600px;
		margin-left: auto;
		margin-right: auto;
	}

	.hero-actions {
		display: flex;
		gap: 1rem;
		justify-content: center;
		flex-wrap: wrap;
	}

	.btn-large {
		padding: 0.875rem 2rem;
		font-size: 1rem;
	}

	.btn-secondary {
		background: transparent;
		border: 2px solid var(--primary);
		color: var(--primary);
	}

	.btn-secondary:hover {
		background: var(--primary);
		color: white;
	}

	.features {
		margin-bottom: 3rem;
	}

	.features h2 {
		text-align: center;
		font-size: 2rem;
		margin-bottom: 2rem;
	}

	.feature-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
		gap: 1.5rem;
	}

	.feature-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 2rem;
		text-align: center;
		transition: transform 0.2s, box-shadow 0.2s;
	}

	.feature-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.feature-icon {
		font-size: 3rem;
		margin-bottom: 1rem;
	}

	.feature-card h3 {
		font-size: 1.25rem;
		margin-bottom: 0.5rem;
	}

	.feature-card p {
		color: var(--text-muted);
		font-size: 0.875rem;
	}

	.cta {
		text-align: center;
		padding: 3rem 2rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		margin-bottom: 2rem;
	}

	.cta h2 {
		font-size: 1.75rem;
		margin-bottom: 1rem;
	}

	.cta p {
		color: var(--text-muted);
		margin-bottom: 1.5rem;
	}

	.public-contact {
		text-align: center;
		padding: 1rem;
		color: var(--text-muted);
	}

	.public-contact a {
		color: var(--primary);
		text-decoration: none;
	}

	.public-contact a:hover {
		text-decoration: underline;
	}
</style>
