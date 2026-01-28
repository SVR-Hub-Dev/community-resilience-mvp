# Knowledge Graph Implementation Plan

## Community Resilience System

---

## Executive Summary

This plan implements a **hybrid Postgres-based knowledge graph** that:

- Leverages your strong local LLM (Ollama) for entity extraction and relationship inference
- Operates offline-first with cloud sync capability
- Uses Postgres JSONB + normalized tables (no additional graph database needed initially)
- Builds incrementally as documents are processed
- Supports all enumeration, dashboard, map, and dependency queries

**Key Principle**: The KG is the system's **structured memory**; the LLM is its **reasoning and extraction engine**.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                     DOCUMENT INGESTION FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Upload → Docling Processing → Structured Content            │
│                                                                  │
│  2. LLM Entity Extraction (Ollama locally)                       │
│     ├─ First pass: Entity identification                        │
│     ├─ Second pass: Relationship inference                      │
│     └─ Third pass: Confidence scoring & validation              │
│                                                                  │
│  3. Entity Resolution (merge duplicates)                         │
│     └─ LLM-assisted fuzzy matching                              │
│                                                                  │
│  4. Knowledge Graph Storage (Postgres)                           │
│     ├─ Entities table (normalized)                              │
│     ├─ Relationships table (edges)                              │
│     └─ Evidence/provenance tracking                             │
│                                                                  │
│  5. Dashboard/Query Layer                                        │
│     ├─ SQL queries for enumeration                              │
│     ├─ GeoJSON for maps                                         │
│     └─ Graph traversal for dependencies                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Database Schema (Week 1)

### 1.1 Core Knowledge Graph Tables

```sql
-- =============================================================================
-- ENTITIES: Core node storage
-- =============================================================================
CREATE TABLE kg_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,  -- HazardType, Community, Agency, etc.
    entity_subtype VARCHAR(50),         -- bushfire, urban, emergencyService, etc.
    name TEXT NOT NULL,
    canonical_name TEXT,                -- Normalized name for deduplication
    
    -- Core attributes (type-specific, stored as JSONB)
    attributes JSONB DEFAULT '{}',
    
    -- Geospatial (if applicable)
    location_point GEOMETRY(Point, 4326),
    location_area GEOMETRY(Polygon, 4326),
    location_text TEXT,                 -- Human-readable location
    
    -- Confidence and provenance
    confidence_score FLOAT DEFAULT 0.5, -- 0.0 to 1.0
    extraction_method VARCHAR(50),      -- 'llm_extracted', 'manual', 'imported'
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,                    -- User or system
    
    -- Sync support
    sync_version INTEGER DEFAULT 1,
    instance_id UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT unique_canonical_name_type UNIQUE (canonical_name, entity_type)
);

-- Indexes for common queries
CREATE INDEX idx_kg_entities_type ON kg_entities(entity_type);
CREATE INDEX idx_kg_entities_subtype ON kg_entities(entity_type, entity_subtype);
CREATE INDEX idx_kg_entities_name_trgm ON kg_entities USING gin(name gin_trgm_ops);
CREATE INDEX idx_kg_entities_canonical ON kg_entities(canonical_name);
CREATE INDEX idx_kg_entities_location_point ON kg_entities USING gist(location_point);
CREATE INDEX idx_kg_entities_location_area ON kg_entities USING gist(location_area);
CREATE INDEX idx_kg_entities_attributes ON kg_entities USING gin(attributes);

-- =============================================================================
-- RELATIONSHIPS: Edges between entities
-- =============================================================================
CREATE TABLE kg_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- The relationship
    source_entity_id UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,  -- hasHazardType, occursIn, implementedBy
    
    -- Relationship attributes (e.g., strength, role, temporal info)
    attributes JSONB DEFAULT '{}',
    
    -- Directionality
    is_bidirectional BOOLEAN DEFAULT FALSE,
    
    -- Confidence and provenance
    confidence_score FLOAT DEFAULT 0.5,
    extraction_method VARCHAR(50),
    
    -- Temporal aspects
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Sync support
    sync_version INTEGER DEFAULT 1,
    instance_id UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT unique_relationship UNIQUE (source_entity_id, target_entity_id, relationship_type)
);

-- Indexes for graph traversal
CREATE INDEX idx_kg_rel_source ON kg_relationships(source_entity_id);
CREATE INDEX idx_kg_rel_target ON kg_relationships(target_entity_id);
CREATE INDEX idx_kg_rel_type ON kg_relationships(relationship_type);
CREATE INDEX idx_kg_rel_source_type ON kg_relationships(source_entity_id, relationship_type);
CREATE INDEX idx_kg_rel_attributes ON kg_relationships USING gin(attributes);

-- =============================================================================
-- EVIDENCE: Track which documents support which facts
-- =============================================================================
CREATE TABLE kg_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What this evidence supports
    entity_id UUID REFERENCES kg_entities(id) ON DELETE CASCADE,
    relationship_id UUID REFERENCES kg_relationships(id) ON DELETE CASCADE,
    
    -- Source document/section
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_id TEXT,                    -- Reference to specific section in document
    page_number INTEGER,
    
    -- The actual evidence
    evidence_text TEXT,
    context_text TEXT,                  -- Surrounding text for context
    
    -- Quality metrics
    relevance_score FLOAT,
    extraction_confidence FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT evidence_target_check CHECK (
        (entity_id IS NOT NULL AND relationship_id IS NULL) OR
        (entity_id IS NULL AND relationship_id IS NOT NULL)
    )
);

CREATE INDEX idx_kg_evidence_entity ON kg_evidence(entity_id);
CREATE INDEX idx_kg_evidence_relationship ON kg_evidence(relationship_id);
CREATE INDEX idx_kg_evidence_document ON kg_evidence(document_id);

-- =============================================================================
-- ENTITY ALIASES: Handle name variations
-- =============================================================================
CREATE TABLE kg_entity_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type VARCHAR(50),  -- 'acronym', 'informal', 'historical', 'alternative'
    confidence_score FLOAT DEFAULT 1.0,
    
    UNIQUE (entity_id, alias)
);

CREATE INDEX idx_kg_aliases_entity ON kg_entity_aliases(entity_id);
CREATE INDEX idx_kg_aliases_text ON kg_entity_aliases USING gin(alias gin_trgm_ops);

-- =============================================================================
-- CONFLICTS: Track conflicts for human review
-- =============================================================================
CREATE TABLE kg_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    conflict_type VARCHAR(50) NOT NULL,  -- 'duplicate_entity', 'contradictory_relationship'
    
    -- Conflicting items
    entity_ids UUID[],
    relationship_ids UUID[],
    
    -- Conflict details
    description TEXT,
    evidence JSONB,
    
    -- Resolution
    status VARCHAR(20) DEFAULT 'open',  -- 'open', 'resolved', 'ignored'
    resolution_notes TEXT,
    resolved_by UUID,
    resolved_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kg_conflicts_status ON kg_conflicts(status);

-- =============================================================================
-- ONTOLOGY METADATA: Track entity types and relationships that exist
-- =============================================================================
CREATE TABLE kg_ontology (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    element_type VARCHAR(20) NOT NULL,  -- 'entity_type' or 'relationship_type'
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_type VARCHAR(100),           -- For hierarchical types
    
    -- Expected attributes schema
    expected_attributes JSONB,
    
    -- Validation rules
    validation_rules JSONB,
    
    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kg_ontology_type ON kg_ontology(element_type);
```

### 1.2 Extensions and Setup

```sql
-- Required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;        -- Fuzzy text matching
CREATE EXTENSION IF NOT EXISTS postgis;        -- Geospatial support
CREATE EXTENSION IF NOT EXISTS btree_gin;      -- Multi-column indexes

-- Helper function: Calculate text similarity
CREATE OR REPLACE FUNCTION kg_text_similarity(text1 TEXT, text2 TEXT)
RETURNS FLOAT AS $$
    SELECT similarity(lower(text1), lower(text2));
$$ LANGUAGE SQL IMMUTABLE;

-- Helper function: Normalize entity name
CREATE OR REPLACE FUNCTION kg_normalize_name(name TEXT)
RETURNS TEXT AS $$
    SELECT lower(
        regexp_replace(
            regexp_replace(name, '[^\w\s]', '', 'g'),
            '\s+', ' ', 'g'
        )
    );
$$ LANGUAGE SQL IMMUTABLE;
```

---

## Phase 2: LLM Extraction Pipeline (Week 1-2)

### 2.1 Entity Extraction Service

```python
# backend/services/kg_extractor.py

from typing import List, Dict, Any, Optional
import json
import asyncio
from dataclasses import dataclass
from datetime import datetime

from services.ollama_client import OllamaClient
from services.docling_service import DoclingProcessor

@dataclass
class ExtractedEntity:
    """Represents an entity extracted from text."""
    entity_type: str
    entity_subtype: Optional[str]
    name: str
    attributes: Dict[str, Any]
    confidence: float
    context: str  # Surrounding text
    location_text: Optional[str] = None


@dataclass
class ExtractedRelationship:
    """Represents a relationship between entities."""
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relationship_type: str
    attributes: Dict[str, Any]
    confidence: float
    context: str


class KnowledgeGraphExtractor:
    """
    Extracts entities and relationships from documents using local LLM.
    
    Uses a multi-pass approach:
    1. Entity extraction
    2. Relationship inference
    3. Confidence scoring
    """
    
    def __init__(self):
        self.llm = OllamaClient()
        self.model = "llama3.1:70b"  # Or your preferred model
        
    async def extract_from_document(
        self, 
        document_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """
        Main extraction pipeline for a document.
        """
        # Split into manageable chunks if needed
        chunks = self._chunk_document(content)
        
        all_entities = []
        all_relationships = []
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}")
            
            # Pass 1: Extract entities
            entities = await self._extract_entities(chunk, metadata)
            all_entities.extend(entities)
            
            # Pass 2: Extract relationships (within chunk)
            relationships = await self._extract_relationships(
                chunk, entities, metadata
            )
            all_relationships.extend(relationships)
        
        # Pass 3: Cross-chunk relationship inference
        cross_chunk_rels = await self._infer_cross_chunk_relationships(
            all_entities, chunks, metadata
        )
        all_relationships.extend(cross_chunk_rels)
        
        return all_entities, all_relationships
    
    async def _extract_entities(
        self, 
        text: str, 
        metadata: Dict[str, Any]
    ) -> List[ExtractedEntity]:
        """
        Extract entities from a text chunk using LLM.
        """
        prompt = self._build_entity_extraction_prompt(text, metadata)
        
        response = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,  # Low temperature for extraction
            format="json"
        )
        
        # Parse and validate response
        try:
            extracted = json.loads(response)
            entities = []
            
            for entity_data in extracted.get("entities", []):
                entity = ExtractedEntity(
                    entity_type=entity_data["type"],
                    entity_subtype=entity_data.get("subtype"),
                    name=entity_data["name"],
                    attributes=entity_data.get("attributes", {}),
                    confidence=entity_data.get("confidence", 0.7),
                    context=entity_data.get("context", ""),
                    location_text=entity_data.get("location")
                )
                entities.append(entity)
            
            return entities
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse entity extraction: {e}")
            return []
    
    async def _extract_relationships(
        self,
        text: str,
        entities: List[ExtractedEntity],
        metadata: Dict[str, Any]
    ) -> List[ExtractedRelationship]:
        """
        Extract relationships between entities in a text chunk.
        """
        if len(entities) < 2:
            return []
        
        prompt = self._build_relationship_extraction_prompt(
            text, entities, metadata
        )
        
        response = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,
            format="json"
        )
        
        try:
            extracted = json.loads(response)
            relationships = []
            
            for rel_data in extracted.get("relationships", []):
                rel = ExtractedRelationship(
                    source_name=rel_data["source"],
                    source_type=rel_data["source_type"],
                    target_name=rel_data["target"],
                    target_type=rel_data["target_type"],
                    relationship_type=rel_data["relationship"],
                    attributes=rel_data.get("attributes", {}),
                    confidence=rel_data.get("confidence", 0.7),
                    context=rel_data.get("context", "")
                )
                relationships.append(rel)
            
            return relationships
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse relationship extraction: {e}")
            return []
    
    def _build_entity_extraction_prompt(
        self, 
        text: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """
        Build a prompt for entity extraction.
        """
        # Get relevant entity types based on document category
        doc_category = metadata.get("category", "general")
        relevant_types = self._get_relevant_entity_types(doc_category)
        
        return f"""You are extracting structured information from an emergency management document.

Document Type: {doc_category}
Document Context: {metadata.get('description', 'Unknown')}

TEXT TO ANALYZE:
{text}

TASK:
Extract all entities from the above text. Focus on these entity types:
{json.dumps(relevant_types, indent=2)}

For each entity, provide:
- type: The entity type (e.g., "Community", "Agency", "HazardType")
- subtype: More specific classification if applicable
- name: The entity name exactly as it appears in text
- attributes: Key-value pairs of important attributes (e.g., population, address, contact)
- confidence: Your confidence in this extraction (0.0 to 1.0)
- context: The sentence or phrase where you found this entity
- location: Geographic location if mentioned

IMPORTANT:
- Only extract entities explicitly mentioned in the text
- Maintain original spelling and capitalization for names
- Include confidence score based on clarity of mention
- Extract acronyms and full names as separate entities if both appear

Return ONLY a JSON object with this structure:
{{
  "entities": [
    {{
      "type": "Community",
      "subtype": "rural",
      "name": "Smithville",
      "attributes": {{"population": 5000}},
      "confidence": 0.9,
      "context": "Smithville community with a population of 5000",
      "location": "Northern region"
    }}
  ]
}}"""
    
    def _build_relationship_extraction_prompt(
        self,
        text: str,
        entities: List[ExtractedEntity],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Build a prompt for relationship extraction.
        """
        entity_list = "\n".join([
            f"- {e.name} (type: {e.entity_type})" 
            for e in entities
        ])
        
        return f"""You are identifying relationships between entities in an emergency management document.

ENTITIES FOUND IN THIS TEXT:
{entity_list}

TEXT:
{text}

TASK:
Identify all relationships between the entities listed above. Common relationship types include:
- occursIn (DisasterEvent → Community/Location)
- hasHazardType (DisasterEvent → HazardType)
- implementedBy (Action → Agency/Organisation)
- responsibleFor (Agency → HazardType/EventPhase)
- serves (Infrastructure → Community)
- targets (Action → Community/HazardType)
- owns (Agency → Resource)
- locatedIn (Entity → Location)
- partOf (Entity → ParentEntity)
- dependsOn (Entity → Entity)

For each relationship provide:
- source: Name of source entity
- source_type: Type of source entity
- target: Name of target entity
- target_type: Type of target entity
- relationship: Type of relationship
- attributes: Additional relationship attributes (e.g., role, timeframe)
- confidence: Your confidence (0.0 to 1.0)
- context: Text supporting this relationship

IMPORTANT:
- Only identify relationships explicitly stated or strongly implied
- Be conservative with confidence scores
- Include temporal information in attributes if mentioned

Return ONLY a JSON object:
{{
  "relationships": [
    {{
      "source": "Smithville Fire Brigade",
      "source_type": "Agency",
      "target": "Smithville",
      "target_type": "Community",
      "relationship": "serves",
      "attributes": {{"coverage": "primary"}},
      "confidence": 0.9,
      "context": "Smithville Fire Brigade serves the Smithville community"
    }}
  ]
}}"""
    
    def _get_relevant_entity_types(self, doc_category: str) -> Dict[str, List[str]]:
        """
        Return relevant entity types based on document category.
        """
        base_types = {
            "Community": ["urban", "rural", "remote"],
            "Agency": ["emergencyService", "healthService", "socialService"],
            "Location": ["point", "area", "evacuationZone"],
        }
        
        if doc_category == "emergency_plan":
            base_types.update({
                "DisasterEvent": ["flood", "bushfire", "storm"],
                "Action": ["ResponseAction", "MitigationMeasure"],
                "Role": ["incidentController", "publicInformationOfficer"],
            })
        elif doc_category == "risk_assessment":
            base_types.update({
                "HazardType": ["flood", "bushfire", "storm", "heatwave"],
                "RiskMetric": ["riskScore", "vulnerabilityIndex"],
                "VulnerableGroup": [],
            })
        elif doc_category == "resource_inventory":
            base_types.update({
                "Resource": ["vehicle", "equipment", "supply"],
                "Facility": [],
            })
        
        return base_types
    
    def _chunk_document(self, content: str, chunk_size: int = 2000) -> List[str]:
        """
        Split document into overlapping chunks for processing.
        """
        # Simple paragraph-based chunking with overlap
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                # Keep last paragraph for overlap
                current_chunk = [current_chunk[-1], para] if current_chunk else [para]
                current_size = len(current_chunk[0]) + para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    async def _infer_cross_chunk_relationships(
        self,
        entities: List[ExtractedEntity],
        chunks: List[str],
        metadata: Dict[str, Any]
    ) -> List[ExtractedRelationship]:
        """
        Infer relationships that span multiple chunks.
        This is useful for documents where entities are mentioned far apart.
        """
        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)
        
        # Look for implicit relationships based on document structure
        # For example: if a Community and multiple Agencies are mentioned,
        # they likely have a "serves" relationship
        
        relationships = []
        
        # Example: Connect agencies to communities in the same document
        if "Agency" in entities_by_type and "Community" in entities_by_type:
            for agency in entities_by_type["Agency"]:
                for community in entities_by_type["Community"]:
                    # Create a low-confidence inferred relationship
                    rel = ExtractedRelationship(
                        source_name=agency.name,
                        source_type="Agency",
                        target_name=community.name,
                        target_type="Community",
                        relationship_type="serves",
                        attributes={"inferred": True},
                        confidence=0.4,  # Low confidence for inference
                        context=f"Inferred from document: {metadata.get('filename')}"
                    )
                    relationships.append(rel)
        
        return relationships
```

### 2.2 Entity Resolution Service

```python
# backend/services/kg_resolver.py

from typing import List, Optional, Tuple
import asyncio
from dataclasses import dataclass

from services.ollama_client import OllamaClient
from db.database import database

@dataclass
class EntityMatch:
    """Represents a potential match between entities."""
    entity1_id: str
    entity2_id: str
    similarity_score: float
    match_reason: str


class EntityResolver:
    """
    Resolves duplicate entities using LLM-assisted matching.
    """
    
    def __init__(self):
        self.llm = OllamaClient()
        self.model = "llama3.1:70b"
    
    async def find_duplicates(
        self, 
        entity_type: str,
        threshold: float = 0.85
    ) -> List[EntityMatch]:
        """
        Find potential duplicate entities of a given type.
        """
        # Get all entities of this type
        query = """
            SELECT id, name, canonical_name, attributes, entity_subtype
            FROM kg_entities
            WHERE entity_type = :entity_type
              AND is_deleted = FALSE
            ORDER BY created_at
        """
        entities = await database.fetch_all(query, {"entity_type": entity_type})
        
        if len(entities) < 2:
            return []
        
        matches = []
        
        # Compare each pair
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                e1 = entities[i]
                e2 = entities[j]
                
                # Quick text similarity check first
                text_sim = await self._calculate_text_similarity(
                    e1['name'], e2['name']
                )
                
                if text_sim < 0.7:  # Skip obviously different names
                    continue
                
                # Use LLM for deeper comparison
                is_match, confidence, reason = await self._llm_compare_entities(
                    e1, e2
                )
                
                if is_match and confidence >= threshold:
                    match = EntityMatch(
                        entity1_id=str(e1['id']),
                        entity2_id=str(e2['id']),
                        similarity_score=confidence,
                        match_reason=reason
                    )
                    matches.append(match)
        
        return matches
    
    async def _calculate_text_similarity(
        self, 
        text1: str, 
        text2: str
    ) -> float:
        """
        Calculate text similarity using database function.
        """
        query = "SELECT kg_text_similarity(:text1, :text2) as similarity"
        result = await database.fetch_one(query, {
            "text1": text1,
            "text2": text2
        })
        return result['similarity']
    
    async def _llm_compare_entities(
        self,
        entity1: dict,
        entity2: dict
    ) -> Tuple[bool, float, str]:
        """
        Use LLM to determine if two entities are the same.
        """
        prompt = f"""You are comparing two entities to determine if they refer to the same real-world entity.

ENTITY 1:
- Name: {entity1['name']}
- Type: {entity1['entity_subtype'] or 'unknown'}
- Attributes: {entity1['attributes']}

ENTITY 2:
- Name: {entity2['name']}
- Type: {entity2['entity_subtype'] or 'unknown'}
- Attributes: {entity2['attributes']}

TASK:
Determine if these two entities are the same real-world entity.
Consider:
- Name variations (abbreviations, acronyms, informal names)
- Attribute similarity (location, contacts, etc.)
- Context clues

Respond ONLY with a JSON object:
{{
  "is_match": true/false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation of your decision"
}}"""

        response = await self.llm.generate(
            prompt=prompt,
            model=self.model,
            temperature=0.1,
            format="json"
        )
        
        try:
            result = json.loads(response)
            return (
                result.get("is_match", False),
                result.get("confidence", 0.0),
                result.get("reason", "")
            )
        except json.JSONDecodeError:
            return False, 0.0, "Failed to parse response"
    
    async def merge_entities(
        self,
        primary_id: str,
        duplicate_id: str,
        merge_reason: str
    ) -> bool:
        """
        Merge a duplicate entity into the primary entity.
        """
        async with database.transaction():
            # Get both entities
            primary = await database.fetch_one(
                "SELECT * FROM kg_entities WHERE id = :id",
                {"id": primary_id}
            )
            duplicate = await database.fetch_one(
                "SELECT * FROM kg_entities WHERE id = :id",
                {"id": duplicate_id}
            )
            
            # Merge attributes (primary takes precedence, but keep non-conflicting)
            merged_attributes = {**duplicate['attributes'], **primary['attributes']}
            
            # Update primary entity
            await database.execute("""
                UPDATE kg_entities
                SET attributes = :attributes,
                    updated_at = NOW()
                WHERE id = :id
            """, {
                "id": primary_id,
                "attributes": json.dumps(merged_attributes)
            })
            
            # Move all relationships from duplicate to primary
            await database.execute("""
                UPDATE kg_relationships
                SET source_entity_id = :primary_id
                WHERE source_entity_id = :duplicate_id
            """, {"primary_id": primary_id, "duplicate_id": duplicate_id})
            
            await database.execute("""
                UPDATE kg_relationships
                SET target_entity_id = :primary_id
                WHERE target_entity_id = :duplicate_id
            """, {"primary_id": primary_id, "duplicate_id": duplicate_id})
            
            # Move evidence
            await database.execute("""
                UPDATE kg_evidence
                SET entity_id = :primary_id
                WHERE entity_id = :duplicate_id
            """, {"primary_id": primary_id, "duplicate_id": duplicate_id})
            
            # Create alias for the duplicate name
            await database.execute("""
                INSERT INTO kg_entity_aliases (entity_id, alias, alias_type)
                VALUES (:entity_id, :alias, 'merged_duplicate')
            """, {
                "entity_id": primary_id,
                "alias": duplicate['name']
            })
            
            # Soft delete the duplicate
            await database.execute("""
                UPDATE kg_entities
                SET is_deleted = TRUE,
                    updated_at = NOW()
                WHERE id = :id
            """, {"id": duplicate_id})
            
            # Log the merge
            print(f"Merged entity {duplicate_id} into {primary_id}: {merge_reason}")
            
        return True
```

### 2.3 Knowledge Graph Storage Service

```python
# backend/services/kg_storage.py

from typing import List, Dict, Any, Optional
import json
from uuid import UUID
from datetime import datetime

from db.database import database
from services.kg_extractor import ExtractedEntity, ExtractedRelationship

class KnowledgeGraphStorage:
    """
    Handles storage and retrieval of KG entities and relationships.
    """
    
    async def store_entities(
        self,
        entities: List[ExtractedEntity],
        document_id: str,
        instance_id: str
    ) -> List[str]:
        """
        Store extracted entities in the database.
        Returns list of created entity IDs.
        """
        entity_ids = []
        
        for entity in entities:
            # Check for existing entity
            canonical_name = self._normalize_name(entity.name)
            
            existing = await database.fetch_one("""
                SELECT id FROM kg_entities
                WHERE canonical_name = :name
                  AND entity_type = :type
                  AND is_deleted = FALSE
            """, {
                "name": canonical_name,
                "type": entity.entity_type
            })
            
            if existing:
                entity_id = str(existing['id'])
                # Update existing entity (merge attributes)
                await self._update_entity(entity_id, entity, document_id)
            else:
                # Create new entity
                entity_id = await self._create_entity(
                    entity, document_id, instance_id
                )
            
            entity_ids.append(entity_id)
        
        return entity_ids
    
    async def store_relationships(
        self,
        relationships: List[ExtractedRelationship],
        document_id: str,
        instance_id: str
    ) -> List[str]:
        """
        Store extracted relationships in the database.
        Returns list of created relationship IDs.
        """
        relationship_ids = []
        
        for rel in relationships:
            # Find source and target entities
            source_id = await self._find_entity_by_name(
                rel.source_name, rel.source_type
            )
            target_id = await self._find_entity_by_name(
                rel.target_name, rel.target_type
            )
            
            if not source_id or not target_id:
                print(f"Cannot create relationship: entities not found")
                continue
            
            # Check for existing relationship
            existing = await database.fetch_one("""
                SELECT id FROM kg_relationships
                WHERE source_entity_id = :source
                  AND target_entity_id = :target
                  AND relationship_type = :type
                  AND is_deleted = FALSE
            """, {
                "source": source_id,
                "target": target_id,
                "type": rel.relationship_type
            })
            
            if existing:
                rel_id = str(existing['id'])
                # Update confidence if new evidence is stronger
                await self._update_relationship(rel_id, rel, document_id)
            else:
                # Create new relationship
                rel_id = await self._create_relationship(
                    rel, source_id, target_id, document_id, instance_id
                )
            
            relationship_ids.append(rel_id)
        
        return relationship_ids
    
    async def _create_entity(
        self,
        entity: ExtractedEntity,
        document_id: str,
        instance_id: str
    ) -> str:
        """Create a new entity in the database."""
        canonical_name = self._normalize_name(entity.name)
        
        # Parse location if provided
        location_point = None
        if entity.location_text:
            # TODO: Geocode location text
            pass
        
        query = """
            INSERT INTO kg_entities (
                entity_type, entity_subtype, name, canonical_name,
                attributes, confidence_score, extraction_method,
                location_text, instance_id
            )
            VALUES (
                :entity_type, :entity_subtype, :name, :canonical_name,
                :attributes, :confidence, :method,
                :location_text, :instance_id
            )
            RETURNING id
        """
        
        result = await database.fetch_one(query, {
            "entity_type": entity.entity_type,
            "entity_subtype": entity.entity_subtype,
            "name": entity.name,
            "canonical_name": canonical_name,
            "attributes": json.dumps(entity.attributes),
            "confidence": entity.confidence,
            "method": "llm_extracted",
            "location_text": entity.location_text,
            "instance_id": instance_id
        })
        
        entity_id = str(result['id'])
        
        # Store evidence
        await self._store_evidence(
            entity_id=entity_id,
            document_id=document_id,
            evidence_text=entity.context,
            confidence=entity.confidence
        )
        
        return entity_id
    
    async def _create_relationship(
        self,
        rel: ExtractedRelationship,
        source_id: str,
        target_id: str,
        document_id: str,
        instance_id: str
    ) -> str:
        """Create a new relationship in the database."""
        query = """
            INSERT INTO kg_relationships (
                source_entity_id, target_entity_id, relationship_type,
                attributes, confidence_score, extraction_method,
                instance_id
            )
            VALUES (
                :source, :target, :type,
                :attributes, :confidence, :method,
                :instance_id
            )
            RETURNING id
        """
        
        result = await database.fetch_one(query, {
            "source": source_id,
            "target": target_id,
            "type": rel.relationship_type,
            "attributes": json.dumps(rel.attributes),
            "confidence": rel.confidence,
            "method": "llm_extracted",
            "instance_id": instance_id
        })
        
        rel_id = str(result['id'])
        
        # Store evidence
        await self._store_evidence(
            relationship_id=rel_id,
            document_id=document_id,
            evidence_text=rel.context,
            confidence=rel.confidence
        )
        
        return rel_id
    
    async def _find_entity_by_name(
        self,
        name: str,
        entity_type: str
    ) -> Optional[str]:
        """Find entity ID by name and type."""
        canonical_name = self._normalize_name(name)
        
        # Try exact match first
        result = await database.fetch_one("""
            SELECT id FROM kg_entities
            WHERE canonical_name = :name
              AND entity_type = :type
              AND is_deleted = FALSE
        """, {"name": canonical_name, "type": entity_type})
        
        if result:
            return str(result['id'])
        
        # Try fuzzy match
        result = await database.fetch_one("""
            SELECT id, name
            FROM kg_entities
            WHERE entity_type = :type
              AND is_deleted = FALSE
              AND kg_text_similarity(name, :search_name) > 0.8
            ORDER BY kg_text_similarity(name, :search_name) DESC
            LIMIT 1
        """, {"type": entity_type, "search_name": name})
        
        if result:
            return str(result['id'])
        
        # Check aliases
        result = await database.fetch_one("""
            SELECT entity_id FROM kg_entity_aliases
            WHERE kg_text_similarity(alias, :search_name) > 0.8
            ORDER BY kg_text_similarity(alias, :search_name) DESC
            LIMIT 1
        """, {"search_name": name})
        
        if result:
            return str(result['entity_id'])
        
        return None
    
    async def _store_evidence(
        self,
        document_id: str,
        evidence_text: str,
        confidence: float,
        entity_id: Optional[str] = None,
        relationship_id: Optional[str] = None
    ):
        """Store evidence for an entity or relationship."""
        await database.execute("""
            INSERT INTO kg_evidence (
                entity_id, relationship_id, document_id,
                evidence_text, extraction_confidence
            )
            VALUES (:entity_id, :relationship_id, :document_id, :text, :confidence)
        """, {
            "entity_id": entity_id,
            "relationship_id": relationship_id,
            "document_id": document_id,
            "text": evidence_text,
            "confidence": confidence
        })
    
    def _normalize_name(self, name: str) -> str:
        """Normalize entity name for matching."""
        import re
        # Remove punctuation, lowercase, collapse whitespace
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.lower().strip()
    
    async def _update_entity(
        self,
        entity_id: str,
        entity: ExtractedEntity,
        document_id: str
    ):
        """Update existing entity with new information."""
        # Merge attributes
        existing = await database.fetch_one(
            "SELECT attributes, confidence_score FROM kg_entities WHERE id = :id",
            {"id": entity_id}
        )
        
        merged_attrs = {**existing['attributes'], **entity.attributes}
        
        # Update confidence (take maximum)
        new_confidence = max(existing['confidence_score'], entity.confidence)
        
        await database.execute("""
            UPDATE kg_entities
            SET attributes = :attributes,
                confidence_score = :confidence,
                updated_at = NOW()
            WHERE id = :id
        """, {
            "id": entity_id,
            "attributes": json.dumps(merged_attrs),
            "confidence": new_confidence
        })
        
        # Add new evidence
        await self._store_evidence(
            entity_id=entity_id,
            document_id=document_id,
            evidence_text=entity.context,
            confidence=entity.confidence
        )
    
    async def _update_relationship(
        self,
        rel_id: str,
        rel: ExtractedRelationship,
        document_id: str
    ):
        """Update existing relationship with new information."""
        existing = await database.fetch_one(
            "SELECT attributes, confidence_score FROM kg_relationships WHERE id = :id",
            {"id": rel_id}
        )
        
        merged_attrs = {**existing['attributes'], **rel.attributes}
        new_confidence = max(existing['confidence_score'], rel.confidence)
        
        await database.execute("""
            UPDATE kg_relationships
            SET attributes = :attributes,
                confidence_score = :confidence,
                updated_at = NOW()
            WHERE id = :id
        """, {
            "id": rel_id,
            "attributes": json.dumps(merged_attrs),
            "confidence": new_confidence
        })
        
        # Add new evidence
        await self._store_evidence(
            relationship_id=rel_id,
            document_id=document_id,
            evidence_text=rel.context,
            confidence=rel.confidence
        )
```

---

## Phase 3: Query and Dashboard API (Week 2-3)

### 3.1 Knowledge Graph Query Service

```python
# backend/services/kg_query.py

from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from db.database import database

class KnowledgeGraphQuery:
    """
    Query interface for the knowledge graph.
    Supports enumeration, coverage analysis, and dependency queries.
    """
    
    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all entities, optionally filtered by type and attributes.
        """
        conditions = ["is_deleted = FALSE"]
        params = {"limit": limit}
        
        if entity_type:
            conditions.append("entity_type = :entity_type")
            params["entity_type"] = entity_type
        
        # Build attribute filters
        if filters:
            for key, value in filters.items():
                if key.startswith("attr_"):
                    attr_name = key[5:]  # Remove 'attr_' prefix
                    conditions.append(f"attributes->>{attr_name} = :filter_{attr_name}")
                    params[f"filter_{attr_name}"] = str(value)
        
        query = f"""
            SELECT 
                id, entity_type, entity_subtype, name,
                attributes, confidence_score,
                location_text, created_at
            FROM kg_entities
            WHERE {' AND '.join(conditions)}
            ORDER BY name
            LIMIT :limit
        """
        
        results = await database.fetch_all(query, params)
        return [dict(r) for r in results]
    
    async def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get complete entity information including relationships."""
        # Get entity
        entity = await database.fetch_one("""
            SELECT * FROM kg_entities WHERE id = :id AND is_deleted = FALSE
        """, {"id": entity_id})
        
        if not entity:
            return None
        
        entity_dict = dict(entity)
        
        # Get outgoing relationships
        outgoing = await database.fetch_all("""
            SELECT 
                r.id, r.relationship_type, r.attributes, r.confidence_score,
                e.id as target_id, e.entity_type as target_type, e.name as target_name
            FROM kg_relationships r
            JOIN kg_entities e ON r.target_entity_id = e.id
            WHERE r.source_entity_id = :id
              AND r.is_deleted = FALSE
              AND e.is_deleted = FALSE
        """, {"id": entity_id})
        
        # Get incoming relationships
        incoming = await database.fetch_all("""
            SELECT 
                r.id, r.relationship_type, r.attributes, r.confidence_score,
                e.id as source_id, e.entity_type as source_type, e.name as source_name
            FROM kg_relationships r
            JOIN kg_entities e ON r.source_entity_id = e.id
            WHERE r.target_entity_id = :id
              AND r.is_deleted = FALSE
              AND e.is_deleted = FALSE
        """, {"id": entity_id})
        
        # Get evidence
        evidence = await database.fetch_all("""
            SELECT 
                e.evidence_text, e.context_text, e.extraction_confidence,
                d.filename, d.category
            FROM kg_evidence e
            JOIN documents d ON e.document_id = d.id
            WHERE e.entity_id = :id
            ORDER BY e.extraction_confidence DESC
        """, {"id": entity_id})
        
        entity_dict['outgoing_relationships'] = [dict(r) for r in outgoing]
        entity_dict['incoming_relationships'] = [dict(r) for r in incoming]
        entity_dict['evidence'] = [dict(e) for e in evidence]
        
        return entity_dict
    
    async def find_coverage_gaps(
        self,
        entity_type: str,
        required_relationship: str,
        target_type: str
    ) -> List[Dict[str, Any]]:
        """
        Find entities that lack a required relationship.
        
        Example: Communities without evacuation plans
        find_coverage_gaps("Community", "hasEvacuationPlan", "Plan")
        """
        query = """
            SELECT 
                e.id, e.name, e.entity_subtype, e.attributes, e.location_text
            FROM kg_entities e
            WHERE e.entity_type = :entity_type
              AND e.is_deleted = FALSE
              AND NOT EXISTS (
                  SELECT 1 FROM kg_relationships r
                  JOIN kg_entities target ON r.target_entity_id = target.id
                  WHERE r.source_entity_id = e.id
                    AND r.relationship_type = :relationship
                    AND target.entity_type = :target_type
                    AND r.is_deleted = FALSE
                    AND target.is_deleted = FALSE
              )
            ORDER BY e.name
        """
        
        results = await database.fetch_all(query, {
            "entity_type": entity_type,
            "relationship": required_relationship,
            "target_type": target_type
        })
        
        return [dict(r) for r in results]
    
    async def find_entities_by_relationship(
        self,
        relationship_type: str,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find all entities connected by a specific relationship type.
        
        Example: All agencies responsible for bushfire response
        """
        conditions = ["r.is_deleted = FALSE"]
        params = {"relationship": relationship_type}
        
        if source_type:
            conditions.append("source.entity_type = :source_type")
            params["source_type"] = source_type
        
        if target_type:
            conditions.append("target.entity_type = :target_type")
            params["target_type"] = target_type
        
        query = f"""
            SELECT 
                r.id as relationship_id,
                r.relationship_type,
                r.attributes as relationship_attributes,
                r.confidence_score,
                source.id as source_id,
                source.entity_type as source_type,
                source.name as source_name,
                source.attributes as source_attributes,
                target.id as target_id,
                target.entity_type as target_type,
                target.name as target_name,
                target.attributes as target_attributes
            FROM kg_relationships r
            JOIN kg_entities source ON r.source_entity_id = source.id
            JOIN kg_entities target ON r.target_entity_id = target.id
            WHERE r.relationship_type = :relationship
              AND source.is_deleted = FALSE
              AND target.is_deleted = FALSE
              AND {' AND '.join(conditions)}
            ORDER BY r.confidence_score DESC
        """
        
        results = await database.fetch_all(query, params)
        return [dict(r) for r in results]
    
    async def get_entity_network(
        self,
        entity_id: str,
        max_depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get the network of entities connected to a given entity.
        Returns nodes and edges for visualization.
        """
        nodes = {}
        edges = []
        visited = set()
        
        async def traverse(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # Get current entity
            entity = await database.fetch_one("""
                SELECT id, entity_type, name, attributes
                FROM kg_entities
                WHERE id = :id AND is_deleted = FALSE
            """, {"id": current_id})
            
            if not entity:
                return
            
            nodes[current_id] = dict(entity)
            
            # Get connected entities
            rel_filter = ""
            params = {"id": current_id}
            
            if relationship_types:
                rel_filter = "AND r.relationship_type = ANY(:rel_types)"
                params["rel_types"] = relationship_types
            
            # Outgoing relationships
            outgoing = await database.fetch_all(f"""
                SELECT 
                    r.id as rel_id,
                    r.relationship_type,
                    r.confidence_score,
                    r.target_entity_id as connected_id
                FROM kg_relationships r
                WHERE r.source_entity_id = :id
                  AND r.is_deleted = FALSE
                  {rel_filter}
            """, params)
            
            for rel in outgoing:
                edges.append({
                    "id": str(rel['rel_id']),
                    "source": current_id,
                    "target": str(rel['connected_id']),
                    "type": rel['relationship_type'],
                    "confidence": rel['confidence_score']
                })
                
                if depth < max_depth:
                    await traverse(str(rel['connected_id']), depth + 1)
            
            # Incoming relationships
            incoming = await database.fetch_all(f"""
                SELECT 
                    r.id as rel_id,
                    r.relationship_type,
                    r.confidence_score,
                    r.source_entity_id as connected_id
                FROM kg_relationships r
                WHERE r.target_entity_id = :id
                  AND r.is_deleted = FALSE
                  {rel_filter}
            """, params)
            
            for rel in incoming:
                edges.append({
                    "id": str(rel['rel_id']),
                    "source": str(rel['connected_id']),
                    "target": current_id,
                    "type": rel['relationship_type'],
                    "confidence": rel['confidence_score']
                })
                
                if depth < max_depth:
                    await traverse(str(rel['connected_id']), depth + 1)
        
        # Start traversal
        await traverse(entity_id, 0)
        
        return {
            "nodes": list(nodes.values()),
            "edges": edges
        }
    
    async def get_dependency_chain(
        self,
        entity_id: str,
        relationship_type: str = "dependsOn"
    ) -> List[List[Dict[str, Any]]]:
        """
        Get all dependency chains for an entity.
        Returns list of paths (each path is a list of entities).
        """
        paths = []
        
        async def find_paths(current_id: str, current_path: List[Dict]):
            # Get current entity
            entity = await database.fetch_one("""
                SELECT id, entity_type, name
                FROM kg_entities
                WHERE id = :id AND is_deleted = FALSE
            """, {"id": current_id})
            
            if not entity:
                return
            
            current_path = current_path + [dict(entity)]
            
            # Check for circular dependencies
            if len(current_path) > len(set(e['id'] for e in current_path)):
                # Circular dependency detected
                paths.append(current_path + [{"circular": True}])
                return
            
            # Get dependencies
            dependencies = await database.fetch_all("""
                SELECT target_entity_id
                FROM kg_relationships
                WHERE source_entity_id = :id
                  AND relationship_type = :rel_type
                  AND is_deleted = FALSE
            """, {"id": current_id, "rel_type": relationship_type})
            
            if not dependencies:
                # Leaf node - end of path
                paths.append(current_path)
            else:
                # Continue down each dependency
                for dep in dependencies:
                    await find_paths(str(dep['target_entity_id']), current_path)
        
        await find_paths(entity_id, [])
        return paths
    
    async def search_entities(
        self,
        search_term: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search for entities.
        """
        conditions = ["is_deleted = FALSE"]
        params = {"search": f"%{search_term}%", "limit": limit}
        
        if entity_types:
            conditions.append("entity_type = ANY(:types)")
            params["types"] = entity_types
        
        query = f"""
            SELECT 
                id, entity_type, entity_subtype, name,
                attributes, confidence_score, location_text,
                kg_text_similarity(name, :search_term) as name_similarity
            FROM kg_entities
            WHERE {' AND '.join(conditions)}
              AND (
                  name ILIKE :search
                  OR attributes::text ILIKE :search
                  OR location_text ILIKE :search
              )
            ORDER BY name_similarity DESC, confidence_score DESC
            LIMIT :limit
        """
        
        params["search_term"] = search_term
        results = await database.fetch_all(query, params)
        return [dict(r) for r in results]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall knowledge graph statistics.
        """
        stats = {}
        
        # Entity counts by type
        entity_counts = await database.fetch_all("""
            SELECT entity_type, COUNT(*) as count
            FROM kg_entities
            WHERE is_deleted = FALSE
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        stats['entity_counts'] = {r['entity_type']: r['count'] for r in entity_counts}
        
        # Relationship counts by type
        rel_counts = await database.fetch_all("""
            SELECT relationship_type, COUNT(*) as count
            FROM kg_relationships
            WHERE is_deleted = FALSE
            GROUP BY relationship_type
            ORDER BY count DESC
        """)
        stats['relationship_counts'] = {r['relationship_type']: r['count'] for r in rel_counts}
        
        # Average confidence scores
        confidence = await database.fetch_one("""
            SELECT 
                AVG(confidence_score) as avg_entity_confidence,
                (SELECT AVG(confidence_score) FROM kg_relationships WHERE is_deleted = FALSE) as avg_rel_confidence
            FROM kg_entities
            WHERE is_deleted = FALSE
        """)
        stats['average_confidence'] = dict(confidence)
        
        # Recent activity
        recent = await database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as entities_last_week,
                (SELECT COUNT(*) FROM kg_relationships 
                 WHERE created_at > NOW() - INTERVAL '7 days' AND is_deleted = FALSE) as relationships_last_week
            FROM kg_entities
            WHERE is_deleted = FALSE
        """)
        stats['recent_activity'] = dict(recent)
        
        # Coverage gaps (example)
        gaps = await database.fetch_one("""
            SELECT 
                COUNT(*) FILTER (WHERE entity_type = 'Community') as total_communities,
                COUNT(*) FILTER (
                    WHERE entity_type = 'Community' 
                    AND NOT EXISTS (
                        SELECT 1 FROM kg_relationships r
                        WHERE r.source_entity_id = kg_entities.id
                        AND r.relationship_type IN ('hasEvacuationPlan', 'hasPlan')
                        AND r.is_deleted = FALSE
                    )
                ) as communities_without_plans
            FROM kg_entities
            WHERE is_deleted = FALSE
        """)
        stats['coverage_gaps'] = dict(gaps)
        
        return stats
```

### 3.2 API Endpoints

```python
# backend/api/kg_routes.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel, UUID4

from services.kg_query import KnowledgeGraphQuery
from services.kg_resolver import EntityResolver
from api.dependencies import get_current_user

router = APIRouter(prefix="/api/kg", tags=["knowledge-graph"])
kg_query = KnowledgeGraphQuery()
resolver = EntityResolver()

# ================= Query Endpoints =================

@router.get("/entities")
async def list_entities(
    entity_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    user = Depends(get_current_user)
):
    """List entities with optional filtering."""
    entities = await kg_query.list_entities(
        entity_type=entity_type,
        limit=limit
    )
    return {"entities": entities, "count": len(entities)}

@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: UUID4,
    user = Depends(get_current_user)
):
    """Get detailed information about a specific entity."""
    entity = await kg_query.get_entity_by_id(str(entity_id))
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity

@router.get("/entities/search")
async def search_entities(
    q: str = Query(..., min_length=2),
    entity_types: Optional[List[str]] = Query(None),
    limit: int = Query(20, le=100),
    user = Depends(get_current_user)
):
    """Search for entities by name or attributes."""
    results = await kg_query.search_entities(
        search_term=q,
        entity_types=entity_types,
        limit=limit
    )
    return {"results": results, "count": len(results)}

@router.get("/coverage-gaps")
async def get_coverage_gaps(
    entity_type: str,
    relationship: str,
    target_type: str,
    user = Depends(get_current_user)
):
    """
    Find entities missing a required relationship.
    Example: /api/kg/coverage-gaps?entity_type=Community&relationship=hasEvacuationPlan&target_type=Plan
    """
    gaps = await kg_query.find_coverage_gaps(
        entity_type=entity_type,
        required_relationship=relationship,
        target_type=target_type
    )
    return {"gaps": gaps, "count": len(gaps)}

@router.get("/relationships/{relationship_type}")
async def get_relationships(
    relationship_type: str,
    source_type: Optional[str] = None,
    target_type: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Get all instances of a relationship type."""
    relationships = await kg_query.find_entities_by_relationship(
        relationship_type=relationship_type,
        source_type=source_type,
        target_type=target_type
    )
    return {"relationships": relationships, "count": len(relationships)}

@router.get("/entities/{entity_id}/network")
async def get_entity_network(
    entity_id: UUID4,
    max_depth: int = Query(2, ge=1, le=5),
    relationship_types: Optional[List[str]] = Query(None),
    user = Depends(get_current_user)
):
    """Get network visualization data for an entity."""
    network = await kg_query.get_entity_network(
        entity_id=str(entity_id),
        max_depth=max_depth,
        relationship_types=relationship_types
    )
    return network

@router.get("/entities/{entity_id}/dependencies")
async def get_dependencies(
    entity_id: UUID4,
    user = Depends(get_current_user)
):
    """Get dependency chains for an entity."""
    paths = await kg_query.get_dependency_chain(str(entity_id))
    return {"paths": paths, "count": len(paths)}

@router.get("/statistics")
async def get_statistics(user = Depends(get_current_user)):
    """Get knowledge graph statistics."""
    stats = await kg_query.get_statistics()
    return stats

# ================= Management Endpoints =================

@router.get("/duplicates/{entity_type}")
async def find_duplicates(
    entity_type: str,
    threshold: float = Query(0.85, ge=0.0, le=1.0),
    user = Depends(get_current_user)
):
    """Find potential duplicate entities."""
    duplicates = await resolver.find_duplicates(
        entity_type=entity_type,
        threshold=threshold
    )
    return {"duplicates": duplicates, "count": len(duplicates)}

class MergeRequest(BaseModel):
    primary_id: UUID4
    duplicate_id: UUID4
    reason: str

@router.post("/entities/merge")
async def merge_entities(
    request: MergeRequest,
    user = Depends(get_current_user)
):
    """Merge a duplicate entity into the primary entity."""
    success = await resolver.merge_entities(
        primary_id=str(request.primary_id),
        duplicate_id=str(request.duplicate_id),
        merge_reason=request.reason
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Merge failed")
    
    return {"status": "merged", "primary_id": request.primary_id}

# ================= GeoJSON Export (for maps) =================

@router.get("/geo/{entity_type}")
async def get_geojson(
    entity_type: str,
    user = Depends(get_current_user)
):
    """Export entities with locations as GeoJSON."""
    from db.database import database
    
    entities = await database.fetch_all("""
        SELECT 
            id, name, entity_type, entity_subtype, attributes,
            ST_AsGeoJSON(location_point)::json as geometry
        FROM kg_entities
        WHERE entity_type = :type
          AND location_point IS NOT NULL
          AND is_deleted = FALSE
    """, {"type": entity_type})
    
    features = []
    for entity in entities:
        features.append({
            "type": "Feature",
            "id": str(entity['id']),
            "geometry": entity['geometry'],
            "properties": {
                "name": entity['name'],
                "entity_type": entity['entity_type'],
                "entity_subtype": entity['entity_subtype'],
                **entity['attributes']
            }
        })
    
    return {
        "type": "FeatureCollection",
        "features": features
    }
```

---

## Phase 4: Integration with Document Processing (Week 2)

### 4.1 Document Processing Hook

```python
# backend/services/document_processor.py (add KG extraction)

from services.kg_extractor import KnowledgeGraphExtractor
from services.kg_storage import KnowledgeGraphStorage

class DocumentProcessor:
    """Enhanced document processor with KG extraction."""
    
    def __init__(self):
        self.docling = DoclingProcessor()
        self.kg_extractor = KnowledgeGraphExtractor()
        self.kg_storage = KnowledgeGraphStorage()
        self.instance_id = os.getenv("INSTANCE_ID")
    
    async def process_document(self, document_id: str, file_path: Path):
        """Process document: Docling + KG extraction."""
        
        # Step 1: Docling processing
        docling_result = await self.docling.process_document(file_path)
        
        # Store in documents table
        await self._update_document_content(
            document_id, 
            docling_result['content'],
            docling_result['sections']
        )
        
        # Step 2: KG extraction (runs in background)
        asyncio.create_task(
            self._extract_knowledge_graph(
                document_id,
                docling_result['content'],
                docling_result['metadata']
            )
        )
        
        return docling_result
    
    async def _extract_knowledge_graph(
        self,
        document_id: str,
        content: str,
        metadata: dict
    ):
        """Extract and store knowledge graph from document."""
        try:
            print(f"Extracting KG from document {document_id}")
            
            # Extract entities and relationships
            entities, relationships = await self.kg_extractor.extract_from_document(
                document_id=document_id,
                content=content,
                metadata=metadata
            )
            
            print(f"Extracted {len(entities)} entities, {len(relationships)} relationships")
            
            # Store in database
            entity_ids = await self.kg_storage.store_entities(
                entities, document_id, self.instance_id
            )
            
            rel_ids = await self.kg_storage.store_relationships(
                relationships, document_id, self.instance_id
            )
            
            # Update document metadata
            await database.execute("""
                UPDATE documents
                SET metadata = metadata || jsonb_build_object(
                    'kg_extracted', true,
                    'kg_entity_count', :entity_count,
                    'kg_relationship_count', :rel_count,
                    'kg_extraction_date', NOW()
                )
                WHERE id = :document_id
            """, {
                "document_id": document_id,
                "entity_count": len(entity_ids),
                "rel_count": len(rel_ids)
            })
            
            print(f"KG extraction complete for document {document_id}")
            
        except Exception as e:
            print(f"KG extraction failed for document {document_id}: {e}")
```

---

## Phase 5: Sync Strategy (Week 3)

### 5.1 KG Sync Configuration

```sql
-- Add KG sync to existing sync_metadata table
ALTER TABLE sync_metadata ADD COLUMN IF NOT EXISTS entity_type_filter VARCHAR(50);

-- Track KG sync specifically
INSERT INTO sync_metadata (entity_type, entity_id, instance_id, cloud_synced)
SELECT 'kg_entity', id, instance_id, false
FROM kg_entities
WHERE instance_id = current_setting('app.instance_id')::uuid;
```

### 5.2 Sync Service Updates

```python
# backend/services/sync_worker.py (add KG sync)

class SyncWorker:
    """Enhanced sync worker with KG synchronization."""
    
    async def sync_cycle(self):
        """Sync documents AND knowledge graph."""
        
        # 1. Sync documents (existing)
        await self.sync_documents()
        
        # 2. Sync knowledge graph
        await self.sync_knowledge_graph()
    
    async def sync_knowledge_graph(self):
        """Bidirectional KG sync."""
        
        # Pull new/updated entities from cloud
        response = await self._fetch_from_cloud("/api/sync/kg/pull")
        cloud_entities = response.get("entities", [])
        cloud_relationships = response.get("relationships", [])
        
        # Merge into local KG
        for entity in cloud_entities:
            await self._merge_entity(entity)
        
        for rel in cloud_relationships:
            await self._merge_relationship(rel)
        
        # Push local changes to cloud
        local_changes = await self._get_local_kg_changes()
        
        if local_changes:
            await self._push_to_cloud("/api/sync/kg/push", {
                "entities": local_changes['entities'],
                "relationships": local_changes['relationships']
            })
    
    async def _merge_entity(self, cloud_entity: dict):
        """Merge cloud entity with local (handle conflicts)."""
        local_entity = await database.fetch_one("""
            SELECT * FROM kg_entities
            WHERE id = :id
        """, {"id": cloud_entity['id']})
        
        if not local_entity:
            # Insert new entity
            await self._insert_entity(cloud_entity)
        else:
            # Check sync_version for conflicts
            if cloud_entity['sync_version'] > local_entity['sync_version']:
                # Cloud is newer - update local
                await self._update_entity(cloud_entity)
            elif cloud_entity['sync_version'] == local_entity['sync_version']:
                # Same version - check if attributes differ
                if cloud_entity['attributes'] != local_entity['attributes']:
                    # Conflict! Log for review
                    await self._log_conflict(cloud_entity, local_entity)
```

---

## Phase 6: Frontend Dashboard (Week 3-4)

### 6.1 KG Dashboard Components

```svelte
<!-- frontend/src/routes/knowledge-graph/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import KGStats from '$lib/components/kg/KGStats.svelte';
  import EntityList from '$lib/components/kg/EntityList.svelte';
  import NetworkVisualization from '$lib/components/kg/NetworkVisualization.svelte';
  import CoverageGapsCard from '$lib/components/kg/CoverageGapsCard.svelte';
  
  let stats = null;
  let selectedEntityType = 'Community';
  
  onMount(async () => {
    const response = await fetch('/api/kg/statistics');
    stats = await response.json();
  });
</script>

<div class="kg-dashboard">
  <h1>Knowledge Graph</h1>
  
  {#if stats}
    <KGStats {stats} />
  {/if}
  
  <div class="dashboard-grid">
    <div class="card">
      <h2>Entities by Type</h2>
      <EntityList entityType={selectedEntityType} />
    </div>
    
    <div class="card">
      <h2>Coverage Gaps</h2>
      <CoverageGapsCard />
    </div>
    
    <div class="card full-width">
      <h2>Entity Network</h2>
      <NetworkVisualization />
    </div>
  </div>
</div>

<style>
  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
    margin-top: 2rem;
  }
  
  .card.full-width {
    grid-column: 1 / -1;
  }
</style>
```

```svelte
<!-- frontend/src/lib/components/kg/CoverageGapsCard.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  
  let gaps = [];
  let loading = true;
  
  const gapQueries = [
    {
      name: "Communities without evacuation plans",
      params: {
        entity_type: "Community",
        relationship: "hasEvacuationPlan",
        target_type: "Plan"
      }
    },
    {
      name: "Hazards without mitigation measures",
      params: {
        entity_type: "HazardType",
        relationship: "hasMitigation",
        target_type: "MitigationMeasure"
      }
    }
  ];
  
  onMount(async () => {
    const results = [];
    
    for (const query of gapQueries) {
      const params = new URLSearchParams(query.params);
      const response = await fetch(`/api/kg/coverage-gaps?${params}`);
      const data = await response.json();
      
      results.push({
        name: query.name,
        count: data.count,
        items: data.gaps
      });
    }
    
    gaps = results;
    loading = false;
  });
</script>

<div class="coverage-gaps">
  {#if loading}
    <p>Loading coverage analysis...</p>
  {:else}
    {#each gaps as gap}
      <div class="gap-item">
        <h4>{gap.name}</h4>
        <span class="count" class:warning={gap.count > 0}>
          {gap.count} found
        </span>
        
        {#if gap.count > 0}
          <ul>
            {#each gap.items.slice(0, 5) as item}
              <li>{item.name}</li>
            {/each}
            {#if gap.count > 5}
              <li class="more">+ {gap.count - 5} more...</li>
            {/if}
          </ul>
        {/if}
      </div>
    {/each}
  {/if}
</div>

<style>
  .gap-item {
    border-left: 3px solid var(--border-color);
    padding-left: 1rem;
    margin-bottom: 1.5rem;
  }
  
  .count.warning {
    color: var(--warning-color);
    font-weight: bold;
  }
  
  ul {
    margin-top: 0.5rem;
    font-size: 0.9em;
  }
</style>
```

---

## Implementation Timeline

### Week 1: Foundation

- **Day 1-2**: Database schema implementation
- **Day 3-4**: Entity extraction service (basic version)
- **Day 5-7**: Storage service and testing

### Week 2: Extraction & Integration

- **Day 1-3**: Relationship extraction
- **Day 4-5**: Entity resolution service
- **Day 6-7**: Integration with document processing

### Week 3: Querying & Sync

- **Day 1-3**: Query service and API endpoints
- **Day 4-5**: Sync strategy implementation
- **Day 6-7**: Testing and refinement

### Week 4: Frontend & Polish

- **Day 1-3**: Dashboard components
- **Day 4-5**: Network visualization
- **Day 6-7**: Documentation and deployment

---

## Deployment Checklist

### Local Instance

- [ ] PostgreSQL with PostGIS extension
- [ ] pg_trgm extension enabled
- [ ] Ollama with llama3.1:70b model pulled
- [ ] KG extraction service configured
- [ ] Sync worker scheduled (optional)

### Cloud Instance

- [ ] Neon database with extensions
- [ ] Sync API endpoints deployed
- [ ] KG sync enabled (if desired)

### Testing

- [ ] Upload test documents (plans, assessments, inventories)
- [ ] Verify entity extraction
- [ ] Check relationship inference
- [ ] Test coverage gap queries
- [ ] Validate sync (if enabled)

---

## Next Steps & Iteration

### Phase 2 Enhancements (Post-MVP)

1. **Geo-coding service** - Automatically geocode location entities
2. **Temporal relationships** - Track how relationships change over time
3. **LLM-powered question answering** - Natural language queries over KG
4. **Recommendation system** - Suggest missing relationships
5. **Export capabilities** - Export to Neo4j, RDF, or GraphML

### Optional: Neo4j Integration

If you want to add Neo4j later for better graph analytics:

```yaml
# docker-compose.local.yml
neo4j:
  image: neo4j:5-community
  ports:
    - "7474:7474"  # Browser
    - "7687:7687"  # Bolt
  environment:
    NEO4J_AUTH: neo4j/password
  volumes:
    - neo4j_data:/data
```

Postgres can remain the source of truth, with Neo4j as a read-replica for complex graph queries.

---

## Key Success Metrics

Track these to evaluate KG quality:

- **Coverage**: % of documents with entities extracted
- **Precision**: % of extracted entities that are correct
- **Recall**: % of entities in documents that were found
- **Confidence scores**: Average confidence of entities/relationships
- **Duplication rate**: How many duplicate entities need merging
- **Query performance**: Response time for coverage gap queries

---

## Questions for You

Before starting implementation, confirm:

1. **Ollama model**: Is `llama3.1:70b` correct, or do you prefer a different model?
2. **Priority entity types**: Which entities are most critical for MVP? (Community, Agency, HazardType?)
3. **Document categories**: Confirm the main document types: emergency_plan, risk_assessment, contact_directory, resource_inventory, operational_manual?
4. **Sync requirement**: Do you want KG to sync between cloud and local immediately, or can that wait?
5. **Frontend priority**: Dashboard first, or map visualization first?

Let me know if you'd like me to generate specific code files or clarify any part of the implementation!
