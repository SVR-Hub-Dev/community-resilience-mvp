<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData } = $props();

	let isLoading = $state(false);

	function handleEnhance() {
		isLoading = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isLoading = false;
		};
	}
</script>

<svelte:head>
	<title>Contact Us - Community Resilience</title>
</svelte:head>

<div class="contact-container">
	<div class="contact-card">
		<div class="header">
			<h1>Contact Us</h1>
			<p>Have a question or feedback? We'd love to hear from you.</p>
		</div>

		{#if form?.success}
			<div class="success-message">
				<svg viewBox="0 0 20 20" width="24" height="24">
					<path
						fill="currentColor"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
					/>
				</svg>
				<div>
					<strong>Message Sent!</strong>
					<p>Thank you for reaching out. We'll get back to you as soon as possible.</p>
				</div>
			</div>
			<a href="/" class="btn btn-primary">Return Home</a>
		{:else}
			{#if form?.error}
				<div class="error-message">
					{form.error}
				</div>
			{/if}

			<form method="POST" use:enhance={handleEnhance}>
				<div class="form-group">
					<label for="name">Name</label>
					<input
						type="text"
						id="name"
						name="name"
						placeholder="Your name"
						autocomplete="name"
						class="form-input"
						required
						disabled={isLoading}
						value={form?.name ?? ''}
					/>
				</div>

				<div class="form-group">
					<label for="email">Email</label>
					<input
						type="email"
						id="email"
						name="email"
						placeholder="your@email.com"
						autocomplete="email"
						class="form-input"
						required
						disabled={isLoading}
						value={form?.email ?? ''}
					/>
				</div>

				<div class="form-group">
					<label for="subject">Subject</label>
					<input
						type="text"
						id="subject"
						name="subject"
						placeholder="How can we help?"
						class="form-input"
						required
						disabled={isLoading}
						value={form?.subject ?? ''}
					/>
				</div>

				<div class="form-group">
					<label for="message">Message</label>
					<textarea
						id="message"
						name="message"
						placeholder="Tell us more..."
						class="form-input"
						rows="5"
						required
						disabled={isLoading}
						>{form?.message ?? ''}</textarea
					>
				</div>

				<button type="submit" class="btn btn-primary submit-button" disabled={isLoading}>
					{isLoading ? 'Sending...' : 'Send Message'}
				</button>
			</form>
		{/if}
	</div>
</div>

<style>
	.contact-container {
		min-height: calc(100vh - 200px);
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding: 2rem;
	}

	.contact-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 2.5rem;
		width: 100%;
		max-width: 500px;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	}

	.header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.header h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin: 0 0 0.5rem 0;
		color: var(--text);
	}

	.header p {
		color: var(--text-muted);
		margin: 0;
		font-size: 0.9375rem;
		line-height: 1.5;
	}

	.success-message {
		display: flex;
		gap: 0.75rem;
		background: #f0fdf4;
		color: #166534;
		padding: 1.25rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		border: 1px solid #bbf7d0;
	}

	.success-message svg {
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.success-message strong {
		display: block;
		margin-bottom: 0.25rem;
	}

	.success-message p {
		margin: 0;
		font-size: 0.875rem;
		line-height: 1.5;
	}

	.error-message {
		background: #fef2f2;
		color: #dc2626;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
		border: 1px solid #fecaca;
	}

	form {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.form-group label {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--text);
	}

	.form-input {
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: 8px;
		font-size: 0.9375rem;
		background: var(--surface);
		color: var(--text);
		outline: none;
		transition: border-color 0.15s ease;
		font-family: inherit;
	}

	.form-input:focus {
		border-color: var(--primary);
	}

	.form-input:disabled {
		opacity: 0.6;
	}

	textarea.form-input {
		resize: vertical;
		min-height: 120px;
	}

	.submit-button {
		padding: 0.875rem 1.5rem;
		margin-top: 0.5rem;
	}

	:global(.dark) .success-message {
		background: #052e16;
		color: #86efac;
		border-color: #166534;
	}

	:global(.dark) .error-message {
		background: #450a0a;
		color: #fca5a5;
		border-color: #dc2626;
	}
</style>
