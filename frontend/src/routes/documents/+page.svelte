<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { DocumentUploadResponse, DocumentStatusResponse, DocumentProcessingStats } from '$lib/types';
	import DocumentStatusBadge from '$lib/components/DocumentStatusBadge.svelte';

	let loading = $state(false);
	let error = $state('');
	let successMessage = $state('');
	let showUploadForm = $state(false);
	let uploading = $state(false);

	// Upload form state
	let selectedFile: File | null = $state(null);
	let title = $state('');
	let description = $state('');
	let tags = $state('');
	let location = $state('');
	let hazardType = $state('');
	let source = $state('');

	// Uploaded documents (from this session)
	let uploadedDocs: DocumentUploadResponse[] = $state([]);

	// Processing stats
	let stats = $state<DocumentProcessingStats | null>(null);
	let statsLoading = $state(true);

	onMount(async () => {
		await loadStats();
	});

	async function loadStats() {
		statsLoading = true;
		try {
			const result = await api.documents.getProcessingStats();
			stats = result as DocumentProcessingStats;
		} catch {
			// Stats are optional — don't block the page
		} finally {
			statsLoading = false;
		}
	}

	function handleFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files?.length) {
			selectedFile = input.files[0];
			// Auto-fill title from filename if empty
			if (!title) {
				const name = selectedFile.name;
				title = name.substring(0, name.lastIndexOf('.')) || name;
			}
		}
	}

	function resetForm() {
		selectedFile = null;
		title = '';
		description = '';
		tags = '';
		location = '';
		hazardType = '';
		source = '';
		showUploadForm = false;
		error = '';
	}

	async function handleUpload(e: Event) {
		e.preventDefault();
		if (!selectedFile) {
			error = 'Please select a file.';
			return;
		}

		uploading = true;
		error = '';
		successMessage = '';

		try {
			const result = await api.documents.upload(selectedFile, {
				title: title || undefined,
				description: description || undefined,
				tags: tags || undefined,
				location: location || undefined,
				hazard_type: hazardType || undefined,
				source: source || undefined
			});

			uploadedDocs = [result, ...uploadedDocs];
			successMessage = result.message;
			resetForm();
			await loadStats();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Upload failed';
		} finally {
			uploading = false;
		}
	}

	async function refreshDocStatus(docId: number) {
		try {
			const updated = await api.documents.getStatus(docId);
			uploadedDocs = uploadedDocs.map((d) =>
				d.id === docId
					? {
							...d,
							processing_status: updated.processing_status,
							processing_mode: updated.processing_mode,
							needs_full_processing: updated.needs_full_processing
						}
					: d
			);
		} catch {
			// Silently fail on status refresh
		}
	}

	let isCloudMode = $derived(stats?.deployment_mode === 'cloud');
</script>

<svelte:head>
	<title>Documents - Community Resilience</title>
</svelte:head>

<div class="container">
	<div class="page-header">
		<div class="header-row">
			<h1>Documents</h1>
			<button
				class="btn btn-primary"
				onclick={() => {
					resetForm();
					showUploadForm = !showUploadForm;
				}}
			>
				{showUploadForm ? 'Cancel' : 'Upload Document'}
			</button>
		</div>
		<p>Upload and manage community knowledge documents.</p>
	</div>

	{#if error}
		<div class="alert alert-error">{error}</div>
	{/if}

	{#if successMessage}
		<div class="alert alert-success">{successMessage}</div>
	{/if}

	<!-- Cloud mode info banner -->
	{#if isCloudMode}
		<div class="info-banner">
			<div class="info-icon">
				<svg viewBox="0 0 20 20" width="20" height="20" fill="currentColor">
					<path
						fill-rule="evenodd"
						d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div>
				<strong>Cloud Mode</strong> &mdash; Basic text extraction is available for PDF, TXT, and
				MD files. Office documents (DOCX, PPTX, XLSX) and advanced OCR require local processing and
				will be queued for the next sync.
			</div>
		</div>
	{/if}

	<!-- Processing stats -->
	{#if stats && !statsLoading}
		<div class="stats-row">
			<div class="stat-card">
				<span class="stat-value">{stats.total}</span>
				<span class="stat-label">Total</span>
			</div>
			<div class="stat-card">
				<span class="stat-value stat-success">{stats.completed}</span>
				<span class="stat-label">Completed</span>
			</div>
			<div class="stat-card">
				<span class="stat-value stat-warning">{stats.needs_local}</span>
				<span class="stat-label">Awaiting Sync</span>
			</div>
			<div class="stat-card">
				<span class="stat-value stat-pending">{stats.pending}</span>
				<span class="stat-label">Pending</span>
			</div>
			{#if stats.failed > 0}
				<div class="stat-card">
					<span class="stat-value stat-danger">{stats.failed}</span>
					<span class="stat-label">Failed</span>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Upload form -->
	{#if showUploadForm}
		<div class="card form-card">
			<h2>Upload Document</h2>

			{#if isCloudMode}
				<p class="form-hint">
					Supported formats: <strong>PDF, TXT, MD</strong>. Other formats will be accepted and
					queued for full processing during the next local sync.
				</p>
			{/if}

			<form onsubmit={handleUpload}>
				<div class="form-group">
					<label class="label" for="file">File *</label>
					<input
						id="file"
						type="file"
						class="input file-input"
						onchange={handleFileSelect}
						required
						accept=".pdf,.txt,.md,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.html,.htm,.rtf,.odt,.odp,.ods"
					/>
				</div>

				<div class="form-group">
					<label class="label" for="doc-title">Title</label>
					<input
						id="doc-title"
						class="input"
						bind:value={title}
						placeholder="Auto-filled from filename"
					/>
				</div>

				<div class="form-group">
					<label class="label" for="doc-description">Description</label>
					<textarea
						id="doc-description"
						class="textarea"
						bind:value={description}
						placeholder="Brief description of the document"
					></textarea>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label class="label" for="doc-tags">Tags (comma-separated)</label>
						<input
							id="doc-tags"
							class="input"
							bind:value={tags}
							placeholder="flood, evacuation, elderly"
						/>
					</div>
					<div class="form-group">
						<label class="label" for="doc-hazard">Hazard Type</label>
						<input
							id="doc-hazard"
							class="input"
							bind:value={hazardType}
							placeholder="flood, fire, storm"
						/>
					</div>
				</div>

				<div class="form-row">
					<div class="form-group">
						<label class="label" for="doc-location">Location</label>
						<input
							id="doc-location"
							class="input"
							bind:value={location}
							placeholder="Riverside Street"
						/>
					</div>
					<div class="form-group">
						<label class="label" for="doc-source">Source</label>
						<input
							id="doc-source"
							class="input"
							bind:value={source}
							placeholder="Community workshop 2023"
						/>
					</div>
				</div>

				<div class="form-actions">
					<button type="button" class="btn btn-secondary" onclick={resetForm}>Cancel</button>
					<button type="submit" class="btn btn-primary" disabled={uploading || !selectedFile}>
						{#if uploading}
							<span class="btn-spinner"></span> Uploading...
						{:else}
							Upload
						{/if}
					</button>
				</div>
			</form>
		</div>
	{/if}

	<!-- Uploaded documents list -->
	{#if uploadedDocs.length > 0}
		<h2 class="section-title">Uploaded Documents</h2>
		<div class="doc-list">
			{#each uploadedDocs as doc (doc.id)}
				<div class="card doc-card">
					<div class="doc-header">
						<h3>{doc.title}</h3>
						<DocumentStatusBadge
							processingStatus={doc.processing_status}
							processingMode={doc.processing_mode}
							needsFullProcessing={doc.needs_full_processing}
						/>
					</div>
					<p class="doc-message">{doc.message}</p>
					{#if doc.needs_full_processing}
						<p class="doc-sync-note">
							Full processing (OCR, structured extraction) will occur when this document is
							synced to a local instance.
						</p>
					{/if}
					<div class="doc-actions">
						<button
							class="btn btn-secondary btn-sm"
							onclick={() => refreshDocStatus(doc.id)}
						>
							Refresh Status
						</button>
					</div>
				</div>
			{/each}
		</div>
	{:else if !showUploadForm && !loading}
		<div class="card empty-state">
			<p>No documents uploaded yet. Click "Upload Document" to get started.</p>
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

	/* Info banner */
	.info-banner {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		background: #eff6ff;
		border: 1px solid #bfdbfe;
		border-radius: var(--radius, 8px);
		color: #1e40af;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
		line-height: 1.5;
	}

	:global([data-theme='dark']) .info-banner {
		background: #1e3a5f;
		border-color: #1e3a5f;
		color: #93c5fd;
	}

	.info-icon {
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	/* Stats row */
	.stats-row {
		display: flex;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}

	.stat-card {
		background: var(--surface);
		border-radius: var(--radius, 8px);
		box-shadow: var(--shadow);
		padding: 1rem 1.25rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		min-width: 100px;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
	}

	.stat-label {
		font-size: 0.75rem;
		color: var(--text-muted);
		margin-top: 0.25rem;
	}

	.stat-success {
		color: #16a34a;
	}
	.stat-warning {
		color: #d97706;
	}
	.stat-pending {
		color: #64748b;
	}
	.stat-danger {
		color: #dc2626;
	}

	/* Form */
	.form-card {
		margin-bottom: 2rem;
	}

	.form-card h2 {
		font-size: 1.25rem;
		margin-bottom: 1rem;
	}

	.form-hint {
		color: var(--text-muted);
		font-size: 0.875rem;
		margin-bottom: 1.25rem;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		margin-top: 1.5rem;
	}

	.file-input {
		padding: 0.5rem;
	}

	.btn-spinner {
		display: inline-block;
		width: 1rem;
		height: 1rem;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.btn-sm {
		padding: 0.375rem 0.75rem;
		font-size: 0.75rem;
	}

	/* Document cards */
	.section-title {
		font-size: 1.25rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	.doc-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.doc-card {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.doc-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}

	.doc-header h3 {
		font-size: 1rem;
		font-weight: 600;
		flex: 1;
	}

	.doc-message {
		font-size: 0.875rem;
		color: var(--text-muted);
	}

	.doc-sync-note {
		font-size: 0.8rem;
		color: #0284c7;
		font-style: italic;
	}

	:global([data-theme='dark']) .doc-sync-note {
		color: #7dd3fc;
	}

	.doc-actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.25rem;
	}

	.empty-state {
		text-align: center;
		padding: 3rem;
		color: var(--text-muted);
	}

	@media (max-width: 640px) {
		.form-row {
			grid-template-columns: 1fr;
		}

		.stats-row {
			flex-direction: column;
		}

		.stat-card {
			flex-direction: row;
			justify-content: space-between;
			min-width: unset;
		}
	}
</style>
