export interface Action {
	priority: number;
	action: string;
	rationale: string;
}

export interface QueryResponse {
	summary: string;
	actions: Action[];
	retrieved_knowledge_ids: number[];
	log_id: number;
}

export interface KnowledgeEntry {
	id: number;
	title: string;
	description: string;
	tags: string[];
	location: string | null;
	hazard_type: string | null;
	source: string | null;
	created_at: string;
}

export interface FeedbackRequest {
	log_id: number;
	rating: number;
	comments?: string;
}

export interface CommunityEvent {
	id: number;
	event_type: string;
	description: string;
	location: string | null;
	severity: number | null;
	reported_by: string | null;
	timestamp: string;
}

export interface CommunityAsset {
	id: number;
	name: string;
	asset_type: string;
	description: string | null;
	location: string | null;
	capacity: number | null;
	status: string | null;
	tags: string[];
	updated_at: string;
}

export interface HealthStatus {
	status: string;
	database: string;
	llm: string;
}

// ============================================================================
// Authentication Types
// ============================================================================

export type UserRole = 'admin' | 'editor' | 'viewer';

// ...existing code...
export interface User {
    id: number;
    email: string;
    name: string;
    role: UserRole;
    password_hash?: string | null;
    oauth_provider?: string | null;
    oauth_id?: string | null;
    avatar_url?: string | null;
    totp_secret?: string | null;
    totp_enabled: boolean;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}
// ...existing code...

export interface TokenPair {
	access_token: string;
	refresh_token: string;
	token_type: string;
	expires_in: number;
}

export interface OAuthRedirect {
	authorization_url: string;
	state: string;
}

export interface APIKey {
	id: number;
	name: string;
	description: string | null;
	key_prefix: string;
	scopes: string[] | null;
	last_used_at: string | null;
	expires_at: string | null;
	is_active: boolean;
	created_at: string;
}

export interface APIKeyCreated extends APIKey {
	key: string; // Full key - only shown on creation
}

export interface Session {
	id: number;
	user_agent: string | null;
	ip_address: string | null;
	expires_at: string;
	created_at: string;
	is_current?: boolean;
}

export interface AuthResponse {
	user: User;
	tokens: TokenPair;
}

export interface LoginResponse {
	access_token?: string;
	refresh_token?: string;
	token_type: string;
	expires_in?: number;
	totp_required: boolean;
	totp_token?: string;
}

export interface TOTPSetupResponse {
	secret: string;
	provisioning_uri: string;
	qr_svg: string;
}

// ============================================================================
// Document Types
// ============================================================================

export interface DocumentUploadResponse {
    id: number;
    title: string;
    processing_mode: string;
    processing_status: string;
    needs_full_processing: boolean;
    message: string;
}

export interface DocumentStatusResponse {
    id: number;
    title: string;
    processing_mode: string;
    processing_status: string;
    needs_full_processing: boolean;
    processed_at: string | null;
}

export interface DocumentProcessingStats {
    total: number;
    completed: number;
    pending: number;
    needs_local: number;
    failed: number;
    processing: number;
    by_status: Record<string, number>;
    needs_full_processing: number;
    deployment_mode: string;
    capabilities: {
        supported_extensions: string[];
        max_upload_size_mb: number;
        deployment_mode: string;
    };
}

// ============================================================================
// Knowledge Graph Types
// ============================================================================

export interface KGEntity {
	id: number;
	entity_type: string;
	entity_subtype: string | null;
	name: string;
	attributes: Record<string, unknown>;
	location_text: string | null;
	confidence_score: number;
	extraction_method: string | null;
	created_at: string;
}

export interface KGRelationshipDetail {
	id: number;
	relationship_type: string;
	confidence_score: number;
	attributes: Record<string, unknown>;
	entity_id: number;
	entity_name: string;
	entity_type: string;
}

export interface KGEvidence {
	id: number;
	document_id: number;
	evidence_text: string | null;
	extraction_confidence: number | null;
}

export interface KGEntityDetail extends KGEntity {
	outgoing_relationships: KGRelationshipDetail[];
	incoming_relationships: KGRelationshipDetail[];
	evidence: KGEvidence[];
	updated_at: string | null;
}

export interface KGStats {
	total_entities: number;
	total_relationships: number;
	entity_counts: Record<string, number>;
	relationship_counts: Record<string, number>;
	avg_confidence: number;
}

export interface KGEntityList {
	entities: KGEntity[];
	total: number;
}

export interface KGNetworkData {
	nodes: Array<{
		id: number;
		name: string;
		entity_type: string;
		entity_subtype: string | null;
		confidence_score: number;
	}>;
	edges: Array<{
		id: number;
		source: number;
		target: number;
		relationship_type: string;
		confidence_score: number;
	}>;
}

// ============================================================================
// Support System Types
// ============================================================================

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface UserBrief {
	id: number;
	email: string;
	name: string | null;
}

export interface SupportTicket {
	id: number;
	user_id: number | null;
	subject: string;
	description: string;
	status: TicketStatus;
	priority: TicketPriority;
	assigned_to: number | null;
	created_at: string;
	updated_at: string;
	resolved_at: string | null;
}

export interface TicketResponse {
	id: number;
	ticket_id: number;
	user_id: number | null;
	message: string;
	is_internal: boolean;
	created_at: string;
	user: UserBrief | null;
}

export interface TicketDetail extends SupportTicket {
	user: UserBrief | null;
	assignee: UserBrief | null;
	responses: TicketResponse[];
}

export interface TicketListResponse {
	tickets: SupportTicket[];
	total: number;
}

export interface ContactSubmission {
	id: number;
	name: string;
	email: string;
	subject: string;
	message: string;
	is_read: boolean;
	created_at: string;
}

export interface ContactListResponse {
	contacts: ContactSubmission[];
	total: number;
}