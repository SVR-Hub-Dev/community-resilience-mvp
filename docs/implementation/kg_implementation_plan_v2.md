<!-- markdownlint-disable MD024 -->
# Knowledge Graph Implementation Plan

## Overview

Add a Knowledge Graph (KG) capability to the Community Resilience MVP. The KG provides structured, enumerable facts (entities and relationships) extracted from uploaded documents via LLM prompts. It complements the existing vector-similarity retrieval by answering questions LLMs alone cannot: "list all organizations," "what's missing," and "what depends on X."

**Architecture**: LLM = reasoning engine, KG = system memory.

**Principle**: Follow existing codebase patterns exactly (SQLAlchemy ORM with sync sessions, Alembic migrations, FastAPI routers with Pydantic schemas, Svelte 5 runes).

---

## Ontology Prioritization

The full ontology (docs/design/8.1.ontology.md) defines 11 entity classes. For the initial implementation, prioritize these 6:

| Priority | Entity Type | Examples |
| -------- | ----------- | -------- |
| 1 | `HazardType` | Bushfire, flood, storm, drought |
| 2 | `Community` | Towns, neighborhoods, demographic groups |
| 3 | `Agency` | Emergency services, government bodies, NGOs |
| 4 | `Location` | Areas, evacuation zones, infrastructure sites |
| 5 | `Resource` | Shelters, equipment, supplies, funding |
| 6 | `Action` | Mitigation measures, response actions, recovery programs |

Deferred: NaturalFeature, ClimateVariable, RiskAssessment, SocialConcepts, detailed Governance hierarchies, GIS/spatial features.

---

## Phase 1: Database Schema (Alembic Migration)

**Goal**: Create KG tables. Add `kg_extraction_status` column to existing `documents` table.

**Create**: `backend/alembic/versions/004_knowledge_graph_tables.py`

### Tables

**`kg_entities`** - Core entity/node storage:

- `id` Integer PK (matches existing codebase pattern — not UUIDs)
- `entity_type` String(50) NOT NULL — one of the 6 priority types
- `entity_subtype` String(50) nullable — e.g. "bushfire", "urban"
- `name` Text NOT NULL
- `canonical_name` Text nullable — normalized for dedup (lowercase, stripped)
- `attributes` JSON default `{}` — type-specific key-value data
- `location_text` Text nullable — human-readable location string
- `confidence_score` Float default 0.5 — 0.0 to 1.0
- `extraction_method` String(50) nullable — "llm_extracted" or "manual"
- `embedding` Vector(384) nullable — for similarity search (matches EMBEDDING_DIM)
- `created_at`, `updated_at` DateTime(timezone=True) with server defaults
- `is_deleted` Boolean default false — soft delete
- UNIQUE constraint on `(canonical_name, entity_type)`

Indexes: `entity_type`, `canonical_name`, `(entity_type, entity_subtype)`, trigram on `name` (via pg_trgm), ivfflat on `embedding`.

**`kg_relationships`** - Edges between entities:

- `id` Integer PK
- `source_entity_id` Integer FK → kg_entities.id ON DELETE CASCADE
- `target_entity_id` Integer FK → kg_entities.id ON DELETE CASCADE
- `relationship_type` String(100) NOT NULL — e.g. "occursIn", "serves", "dependsOn"
- `attributes` JSON default `{}`
- `confidence_score` Float default 0.5
- `extraction_method` String(50) nullable
- `created_at`, `updated_at` DateTime(timezone=True)
- `is_deleted` Boolean default false
- UNIQUE constraint on `(source_entity_id, target_entity_id, relationship_type)`

Indexes: `source_entity_id`, `target_entity_id`, `relationship_type`, `(source_entity_id, relationship_type)`.

**`kg_evidence`** - Provenance tracking (links entities/relationships back to source documents):

- `id` Integer PK
- `entity_id` Integer FK → kg_entities.id ON DELETE CASCADE (nullable)
- `relationship_id` Integer FK → kg_relationships.id ON DELETE CASCADE (nullable)
- `document_id` Integer FK → documents.id ON DELETE CASCADE NOT NULL
- `evidence_text` Text nullable — the source text span
- `extraction_confidence` Float nullable
- `created_at` DateTime(timezone=True)
- CHECK constraint: exactly one of entity_id or relationship_id must be non-null

Indexes: `entity_id`, `relationship_id`, `document_id`.

**Alter `documents` table**: Add column `kg_extraction_status` String(50) default "pending".

**Extension**: `CREATE EXTENSION IF NOT EXISTS pg_trgm` (for fuzzy name matching).

### Verification

Run `alembic upgrade head` and confirm tables exist with correct columns, constraints, and indexes.

---

## Phase 2: ORM Models

**Goal**: SQLAlchemy models matching the migration schema.

**Create**: `backend/models/kg_models.py`

### Classes

```text
KGEntity(Base)
  __tablename__ = "kg_entities"
  - Standard Column definitions matching Phase 1 schema
  - Relationships:
    outgoing_relationships → KGRelationship (via source_entity_id)
    incoming_relationships → KGRelationship (via target_entity_id)
    evidence → KGEvidence

KGRelationship(Base)
  __tablename__ = "kg_relationships"
  - Standard Column definitions
  - Relationships:
    source_entity → KGEntity
    target_entity → KGEntity
    evidence → KGEvidence

KGEvidence(Base)
  __tablename__ = "kg_evidence"
  - Standard Column definitions
  - Relationships:
    entity → KGEntity
    relationship → KGRelationship
    document → Document
```

### Constants (in same file)

```python
ENTITY_TYPES = ["HazardType", "Community", "Agency", "Location", "Resource", "Action"]

RELATIONSHIP_TYPES = [
    "occursIn", "hasHazardType", "serves", "responsibleFor",
    "locatedIn", "targets", "owns", "implementedBy", "dependsOn", "partOf",
]
```

### Wiring

- Import KG models in `backend/alembic/env.py` so `Base.metadata` includes them for future autogenerate migrations.

---

## Phase 3: Entity Extraction Service

**Goal**: LLM-based service that takes document text and returns structured entities and relationships. Uses the existing `llm` singleton from `llm_client.py` (supports Groq, Ollama, OpenAI automatically).

**Create**: `backend/services/kg_extractor.py`

### Data Classes

```python
@dataclass
class ExtractedEntity:
    entity_type: str           # From ENTITY_TYPES
    entity_subtype: Optional[str]
    name: str
    attributes: Dict[str, Any]
    confidence: float          # 0.0 - 1.0
    evidence_text: str         # Source text span
    location_text: Optional[str]

@dataclass
class ExtractedRelationship:
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relationship_type: str     # From RELATIONSHIP_TYPES
    attributes: Dict[str, Any]
    confidence: float
    evidence_text: str
```

### Class: KGExtractor

```text
KGExtractor
  __init__(): uses llm singleton from llm_client.py

  async extract_from_text(content, metadata) → (entities, relationships)
    - Chunks the content at paragraph boundaries
    - For each chunk: extract entities, then extract relationships given entities
    - Deduplicates across chunks by name+type
    - Returns combined results

  async _extract_entities(chunk, metadata) → List[ExtractedEntity]
    - Builds JSON-output prompt listing the 6 entity types with examples
    - Calls llm.generate() with low temperature
    - Parses JSON response with fallback (mirrors reasoning.py parse_response pattern)

  async _extract_relationships(chunk, entities, metadata) → List[ExtractedRelationship]
    - Builds prompt with discovered entities as context
    - Requests relationships between them
    - Parses JSON response

  _build_entity_prompt(chunk, metadata) → str
  _build_relationship_prompt(chunk, entities, metadata) → str
  _parse_entity_response(response) → List[ExtractedEntity]
  _parse_relationship_response(response) → List[ExtractedRelationship]
  _chunk_text(content, max_chars=3000) → List[str]
```

### Prompt Design

- List the 6 priority entity types with 2-3 examples each
- Include document metadata (title, tags, hazard_type) for extraction context
- Request strict JSON output schema
- Use low temperature (0.1-0.3) for deterministic extraction
- Include the relationship types list in the relationship prompt

### Cloud vs Local

- Cloud (Groq): single-pass extraction, smaller chunks (~2000 chars), combined entities+relationships prompt
- Local (Ollama): two-pass extraction (entities first, then relationships), larger chunks (~4000 chars)
- Controlled via `settings.deployment_mode`

### Tests

**Create**: `backend/tests/test_kg_extractor.py`

- Mock `llm.generate()` to return known JSON
- Verify correct parsing of entities and relationships
- Test malformed JSON fallback handling
- Test chunking logic

---

## Phase 4: KG Storage Service

**Goal**: Store extracted entities and relationships in PostgreSQL with deduplication via canonical names.

**Create**: `backend/services/kg_storage.py`

### Class: KGStorageService

```text
KGStorageService

  store_extraction_results(db, document_id, entities, relationships) → (entity_ids, rel_ids)
    - Stores each entity (with dedup), then each relationship
    - Creates evidence records linking back to the document

  _store_entity(db, entity, document_id) → entity_id
    - Normalizes name → canonical_name
    - Looks up by (canonical_name, entity_type)
    - If exists: update confidence (take max), merge attributes, add evidence
    - If new: create entity with embedding via embed_text(), add evidence

  _store_relationship(db, rel, document_id) → Optional[rel_id]
    - Resolves source/target by canonical_name + type
    - If both found: create/update relationship, add evidence
    - If either missing: log warning, return None

  _find_entity_by_name(db, name, entity_type) → Optional[entity_id]
  _normalize_name(name) → str  # lowercase, strip punctuation, collapse whitespace
  _store_evidence(db, document_id, evidence_text, confidence, entity_id?, relationship_id?)
```

### Dedup Strategy

1. `_normalize_name()`: lowercase, strip leading/trailing whitespace, collapse internal whitespace, remove punctuation
2. Query `kg_entities` by `(canonical_name, entity_type)` unique constraint
3. On match: `confidence_score = max(existing, new)`, merge attributes (existing wins conflicts), add new evidence record
4. On miss: create new entity, generate embedding via `embed_text(name + " " + entity_type)`

### Tests

**Create**: `backend/tests/test_kg_storage.py`

- Store entities, verify dedup (same entity stored twice merges correctly)
- Verify evidence records are created with correct document_id
- Verify relationships link correct entity IDs
- Test missing entity graceful handling

---

## Phase 5: KG Query Service

**Goal**: Read-only service for querying the knowledge graph.

**Create**: `backend/services/kg_query.py`

### Class: KGQueryService

```text
KGQueryService

  list_entities(db, entity_type?, search?, limit=100, offset=0) → (entities, total_count)
    - Filter by entity_type if provided
    - Text search via ILIKE on name and location_text
    - Order by confidence_score desc, name asc

  get_entity_detail(db, entity_id) → dict
    - Entity fields + outgoing relationships + incoming relationships + evidence
    - Each relationship includes the connected entity's name and type

  search_entities(db, query, entity_types?, limit=20) → List[KGEntity]
    - ILIKE text search + vector similarity via embedding
    - Combined ranking: exact text matches first, then vector similarity

  get_entity_relationships(db, entity_id) → dict
    - Outgoing and incoming relationships grouped by relationship_type

  get_statistics(db) → dict
    - total_entities, total_relationships
    - entity_counts by type, relationship_counts by type
    - avg_confidence

  find_coverage_gaps(db, entity_type, required_relationship, target_type) → List[KGEntity]
    - Entities of entity_type that lack a relationship of required_relationship to any target_type entity
    - Example: Communities without any "responsibleFor" Agency

  get_entity_network(db, entity_id, max_depth=2) → dict
    - BFS from entity_id up to max_depth hops
    - Returns {nodes: [...], edges: [...]} for frontend visualization
```

### Tests

**Create**: `backend/tests/test_kg_query.py`

- Create test fixtures (entities + relationships)
- Verify list, search, detail, statistics, coverage gap queries

---

## Phase 6: API Endpoints

**Goal**: FastAPI router exposing KG query and CRUD operations.

**Create**: `backend/api/kg_router.py`

### Pydantic Schemas (in same file, matching app.py pattern)

```text
KGEntityOut: id, entity_type, entity_subtype, name, attributes,
             location_text, confidence_score, extraction_method, created_at
             (Config: from_attributes = True)

KGRelationshipOut: id, source_entity_id, target_entity_id, relationship_type,
                   attributes, confidence_score, created_at

KGEntityDetailOut(KGEntityOut): + outgoing_relationships, incoming_relationships, evidence

KGEntityListOut: entities: List[KGEntityOut], total: int

KGStatsOut: total_entities, total_relationships, entity_counts, relationship_counts, avg_confidence

KGEntityCreateIn: entity_type, name, entity_subtype?, attributes?, location_text?
```

### Endpoints

| Method | Path | Description | Auth |
| ------ | ---- | ----------- | ---- |
| `GET` | `/api/kg/entities` | List entities (type filter, search, pagination) | `require_viewer` |
| `GET` | `/api/kg/entities/search` | Search entities by text/vector | `require_viewer` |
| `GET` | `/api/kg/entities/{id}` | Get entity detail with relationships + evidence | `require_viewer` |
| `GET` | `/api/kg/entities/{id}/network` | Get network data for visualization | `require_viewer` |
| `GET` | `/api/kg/relationships` | List relationships (type filter) | `require_viewer` |
| `GET` | `/api/kg/statistics` | Get KG summary stats | `require_viewer` |
| `GET` | `/api/kg/coverage-gaps` | Find entities missing relationships | `require_viewer` |
| `POST` | `/api/kg/entities` | Manually create an entity | `require_editor` |
| `PUT` | `/api/kg/entities/{id}` | Update an entity | `require_editor` |
| `DELETE` | `/api/kg/entities/{id}` | Soft-delete an entity | `require_editor` |

### Wiring

**Modify**: `backend/app.py` — add `app.include_router(kg_router)`

### Tests

- FastAPI TestClient with mocked DB session
- Verify response schemas, auth requirements, error handling

---

## Phase 7: Frontend — KG Dashboard Page

**Goal**: Knowledge Graph dashboard with statistics, entity list with filtering, and search.

### Files to Create

- `frontend/src/routes/knowledge-graph/+page.svelte`
- `frontend/src/lib/components/KGEntityCard.svelte`

### Files to Modify

- `frontend/src/lib/types/index.ts` — add KG TypeScript interfaces
- `frontend/src/lib/api.ts` — add `knowledgeGraph` namespace to api object
- `frontend/src/routes/+layout.svelte` — add "Graph" nav link

### TypeScript Types (add to types/index.ts)

```typescript
interface KGEntity {
  id: number; entity_type: string; entity_subtype: string | null;
  name: string; attributes: Record<string, unknown>;
  location_text: string | null; confidence_score: number;
  extraction_method: string | null; created_at: string;
}

interface KGRelationshipDetail {
  id: number; relationship_type: string; confidence_score: number;
  entity_id: number; entity_name: string; entity_type: string;
}

interface KGEvidence {
  id: number; document_id: number; evidence_text: string | null;
  extraction_confidence: number | null;
}

interface KGEntityDetail extends KGEntity {
  outgoing_relationships: KGRelationshipDetail[];
  incoming_relationships: KGRelationshipDetail[];
  evidence: KGEvidence[];
}

interface KGStats {
  total_entities: number; total_relationships: number;
  entity_counts: Record<string, number>;
  relationship_counts: Record<string, number>;
  avg_confidence: number;
}
```

### API Client Additions (add to api.ts)

```typescript
knowledgeGraph: {
  getEntities(params?): Promise<{ entities: KGEntity[]; total: number }>
  getEntity(id): Promise<KGEntityDetail>
  searchEntities(query, entityTypes?): Promise<KGEntity[]>
  getStatistics(): Promise<KGStats>
  getCoverageGaps(entityType, relationship, targetType): Promise<{ gaps: KGEntity[] }>
  getEntityNetwork(id, maxDepth?): Promise<{ nodes: any[]; edges: any[] }>
  createEntity(data): Promise<{ status: string; id: number }>
  updateEntity(id, data): Promise<{ status: string }>
  deleteEntity(id): Promise<{ status: string }>
}
```

### Dashboard Page Layout

- **Stats row**: Cards showing total entities, total relationships, average confidence (follow documents page stat card pattern)
- **Entity type filter tabs**: All | HazardType | Community | Agency | Location | Resource | Action
- **Search input**: Debounced text search
- **Entity grid**: Card layout using `.entries-grid` pattern from knowledge page
- **KGEntityCard**: Name, type badge (colored), subtype, location, confidence bar, evidence count

### Component Pattern

- Use `$state()` for reactive state
- `onMount` for initial data load
- `$derived()` for filtered/computed values
- Follow existing CSS variable theming

---

## Phase 8: Frontend — Entity Detail View

**Goal**: Detail page for individual KG entities showing relationships, evidence, and connected entities.

### Files to Create

- `frontend/src/routes/knowledge-graph/[id]/+page.svelte`
- `frontend/src/lib/components/KGRelationshipList.svelte`
- `frontend/src/lib/components/KGEvidenceList.svelte`

### Page Layout

- **Breadcrumb**: Knowledge Graph > Entity Name
- **Entity header**: Name, type badge, subtype, confidence score, extraction method
- **Attributes section**: Key-value display of the JSON attributes
- **Location**: Text display (GIS/map deferred to later phase)
- **Relationships section** (two columns):
  - Outgoing: "This entity → relationship_type → Target entity"
  - Incoming: "Source entity → relationship_type → This entity"
  - Each entry is a clickable link to the connected entity
- **Evidence section**: List of evidence records with document source links, expandable text

### Routing

- SvelteKit dynamic route `[id]`
- Load entity via `$page.params.id` in `onMount`

---

## Phase 9: Document Processing Integration

**Goal**: Automatically extract KG entities when documents are processed.

### Files to Modify

- `backend/api/documents.py` — add background KG extraction after document upload

### Integration Point

After a document is successfully uploaded and processed in the `upload_document` endpoint, trigger KG extraction as a FastAPI `BackgroundTask`:

```python
from fastapi import BackgroundTasks

async def extract_kg_background(document_id: int, content: str, metadata: dict):
    """Background task for KG extraction after document upload."""
    # 1. Update document.kg_extraction_status = "processing"
    # 2. Call kg_extractor.extract_from_text(content, metadata)
    # 3. Call kg_storage.store_extraction_results(db, document_id, entities, relationships)
    # 4. Update document.kg_extraction_status = "completed" (or "failed" on error)
```

In the upload endpoint, after document is stored:

```python
if result.success and result.content:
    background_tasks.add_task(extract_kg_background, document.id, result.content, metadata)
```

### Status Tracking

- `kg_extraction_status` column (from Phase 1): "pending" → "processing" → "completed" / "failed"
- Frontend documents page can show a KG extraction badge alongside the existing processing status badge

### Cloud vs Local Behavior

- **Cloud (Groq)**: Basic extraction runs quickly via API
- **Local (Ollama)**: Deeper multi-pass extraction, may be slower but doesn't block the user

---

## Future Phases (Not In This Plan)

These are documented for reference but not part of the current implementation:

- **Phase 10: GIS/Spatial Integration** — PostGIS geometry columns, spatial queries, LLM geocoding service, MapLibre GL visualization (see `docs/implementation/kg_gis_integration.md`)
- **Phase 11: Network Visualization** — Interactive force-directed graph using D3.js or vis.js
- **Phase 12: Entity Resolution** — LLM-assisted fuzzy matching for advanced dedup
- **Phase 13: Conflicts & Aliases** — `kg_conflicts` and `kg_entity_aliases` tables for tracking contradictory information
- **Phase 14: Ontology Management** — `kg_ontology` table for dynamic entity type/relationship type management
- **Phase 15: KG-Enhanced Reasoning** — Feed KG context into the reasoning pipeline alongside vector search results

---

## Dependency Graph

```text
Phase 1 (Migration)
  └→ Phase 2 (ORM Models)
       ├→ Phase 3 (Extractor) ──→ Phase 4 (Storage)
       │                              │
       └→ Phase 5 (Query) ───────────→ Phase 6 (API)
                                        ├→ Phase 7 (Dashboard)
                                        │    └→ Phase 8 (Detail View)
                                        └→ Phase 9 (Doc Integration) ←── Phase 4
```

Phases 3+4 and Phase 5 can be developed in parallel after Phase 2. Phase 6 requires Phase 5. Frontend phases (7-8) require Phase 6. Phase 9 requires Phases 4 and 6.

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Primary keys | Integer | Matches all existing models (User, Document, CommunityKnowledge) |
| DB sessions | Sync (Session) | Matches majority pattern in app.py endpoints |
| LLM client | Existing `llm` singleton | Auto-handles Groq/Ollama/OpenAI switching |
| PostGIS | Deferred | Adds deployment complexity; `location_text` sufficient for MVP |
| Ontology table | Deferred | Python constants sufficient; dynamic types add premature complexity |
| Conflicts/aliases tables | Deferred | Canonical name dedup sufficient for MVP |
| Soft delete | Yes (`is_deleted`) | Matches design docs; allows recovery |
| Background extraction | FastAPI BackgroundTasks | Non-blocking; simple; no task queue dependency |

---

## Files Summary

### Create (15 files)

| File | Phase |
| ---- | ----- |
| `backend/alembic/versions/004_knowledge_graph_tables.py` | 1 |
| `backend/models/kg_models.py` | 2 |
| `backend/services/kg_extractor.py` | 3 |
| `backend/services/kg_storage.py` | 4 |
| `backend/services/kg_query.py` | 5 |
| `backend/api/kg_router.py` | 6 |
| `backend/tests/test_kg_extractor.py` | 3 |
| `backend/tests/test_kg_storage.py` | 4 |
| `backend/tests/test_kg_query.py` | 5 |
| `frontend/src/routes/knowledge-graph/+page.svelte` | 7 |
| `frontend/src/lib/components/KGEntityCard.svelte` | 7 |
| `frontend/src/routes/knowledge-graph/[id]/+page.svelte` | 8 |
| `frontend/src/lib/components/KGRelationshipList.svelte` | 8 |
| `frontend/src/lib/components/KGEvidenceList.svelte` | 8 |
| `frontend/src/lib/types/index.ts` (create if missing) | 7 |

### Modify (4 files)

| File | Phase | Change |
| ---- | ----- | ------ |
| `backend/app.py` | 6 | Add `app.include_router(kg_router)` |
| `backend/alembic/env.py` | 2 | Import KG models for metadata |
| `frontend/src/lib/api.ts` | 7 | Add `knowledgeGraph` API methods |
| `frontend/src/routes/+layout.svelte` | 7 | Add "Graph" nav link |
| `backend/api/documents.py` | 9 | Add background KG extraction task |
