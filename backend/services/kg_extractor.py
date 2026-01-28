"""LLM-based entity and relationship extraction for the Knowledge Graph."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from llm_client import llm
from models.kg_models import ENTITY_TYPES, RELATIONSHIP_TYPES

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
TIMEOUT_SECONDS = 120


# ── Data classes for extraction results ───────────────────────────────────────

@dataclass
class ExtractedEntity:
    """An entity extracted from document text."""
    entity_type: str
    name: str
    entity_subtype: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    evidence_text: str = ""
    location_text: Optional[str] = None


@dataclass
class ExtractedRelationship:
    """A relationship extracted from document text."""
    source_name: str
    source_type: str
    target_name: str
    target_type: str
    relationship_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    evidence_text: str = ""


# ── Extraction service ────────────────────────────────────────────────────────

class KGExtractor:
    """
    Extracts entities and relationships from document text using LLM prompts.

    Uses the existing llm singleton which auto-selects between Groq (cloud),
    Ollama (local), and OpenAI based on configuration.
    """

    def __init__(self):
        self.llm = llm

    async def extract_from_text(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """
        Main extraction pipeline.

        Chunks the document, extracts entities per chunk, then extracts
        relationships given the discovered entities.

        Args:
            content: Full document text.
            metadata: Document metadata (title, tags, hazard_type, etc.)

        Returns:
            Tuple of (entities, relationships).
        """
        metadata = metadata or {}
        chunks = self._chunk_text(content)
        logger.info(f"Extracting KG from {len(chunks)} chunk(s), metadata={list(metadata.keys())}")

        all_entities: List[ExtractedEntity] = []
        all_relationships: List[ExtractedRelationship] = []

        for i, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)")

            # Step 1: Extract entities from this chunk
            entities = await self._extract_entities(chunk, metadata)
            all_entities.extend(entities)

            # Step 2: Extract relationships given the entities found so far
            if entities:
                relationships = await self._extract_relationships(chunk, entities, metadata)
                all_relationships.extend(relationships)

        # Deduplicate entities by (name_lower, entity_type)
        all_entities = self._deduplicate_entities(all_entities)
        logger.info(
            f"Extraction complete: {len(all_entities)} entities, "
            f"{len(all_relationships)} relationships"
        )
        return all_entities, all_relationships

    async def _extract_entities(
        self,
        chunk: str,
        metadata: Dict[str, Any],
    ) -> List[ExtractedEntity]:
        """Extract entities from a single chunk via LLM prompt."""
        prompt = self._build_entity_prompt(chunk, metadata)

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    self.llm.generate(prompt),
                    timeout=TIMEOUT_SECONDS,
                )
                entities = self._parse_entity_response(response)
                if entities:
                    return entities
            except asyncio.TimeoutError:
                logger.warning(f"Entity extraction timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Entity extraction error (attempt {attempt + 1}): {e}")

        logger.warning("Entity extraction failed after all retries")
        return []

    async def _extract_relationships(
        self,
        chunk: str,
        entities: List[ExtractedEntity],
        metadata: Dict[str, Any],
    ) -> List[ExtractedRelationship]:
        """Extract relationships from a single chunk given discovered entities."""
        prompt = self._build_relationship_prompt(chunk, entities, metadata)

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await asyncio.wait_for(
                    self.llm.generate(prompt),
                    timeout=TIMEOUT_SECONDS,
                )
                relationships = self._parse_relationship_response(response)
                if relationships:
                    return relationships
            except asyncio.TimeoutError:
                logger.warning(f"Relationship extraction timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Relationship extraction error (attempt {attempt + 1}): {e}")

        logger.warning("Relationship extraction failed after all retries")
        return []

    # ── Prompt builders ───────────────────────────────────────────────────────

    def _build_entity_prompt(self, chunk: str, metadata: Dict[str, Any]) -> str:
        """Build the entity extraction prompt requesting JSON output."""
        meta_lines = []
        if metadata.get("title"):
            meta_lines.append(f"Document title: {metadata['title']}")
        if metadata.get("hazard_type"):
            meta_lines.append(f"Hazard type: {metadata['hazard_type']}")
        if metadata.get("location"):
            meta_lines.append(f"Location context: {metadata['location']}")
        if metadata.get("tags"):
            tags = metadata["tags"] if isinstance(metadata["tags"], str) else ", ".join(metadata["tags"])
            meta_lines.append(f"Tags: {tags}")

        meta_section = "\n".join(meta_lines) if meta_lines else "No metadata available."

        return f"""You are a knowledge graph entity extractor for a community disaster resilience system.

Extract all relevant entities from the text below. Each entity must be one of these types:

- HazardType: Natural or human-caused hazards (e.g., bushfire, flood, cyclone, drought, earthquake)
- Community: Towns, suburbs, neighborhoods, demographic groups, vulnerable populations
- Agency: Organizations, government bodies, emergency services, NGOs, community groups
- Location: Specific places, infrastructure sites, evacuation zones, landmarks
- Resource: Physical resources, shelters, equipment, supplies, funding, personnel
- Action: Mitigation measures, response actions, recovery programs, preparedness activities

## Document metadata
{meta_section}

## Text to extract from
{chunk}

## Output format
Respond ONLY with a valid JSON object:

{{
  "entities": [
    {{
      "entity_type": "HazardType",
      "name": "Bushfire",
      "entity_subtype": "wildfire",
      "attributes": {{"severity": "high", "season": "summer"}},
      "confidence": 0.9,
      "evidence_text": "The bushfire season typically peaks in summer...",
      "location_text": null
    }}
  ]
}}

Rules:
- entity_type MUST be one of: {", ".join(ENTITY_TYPES)}
- confidence is 0.0 to 1.0 (how certain you are this entity exists in the text)
- evidence_text is the phrase or sentence from the text supporting this entity
- location_text is a place name if the entity has a geographic reference
- Do NOT invent entities not supported by the text
- Include ALL entities you can find, even low-confidence ones (0.3+)
"""

    def _build_relationship_prompt(
        self,
        chunk: str,
        entities: List[ExtractedEntity],
        metadata: Dict[str, Any],
    ) -> str:
        """Build the relationship extraction prompt."""
        entity_list = "\n".join(
            f"- {e.name} ({e.entity_type})" for e in entities
        )

        return f"""You are a knowledge graph relationship extractor for a community disaster resilience system.

Given the following entities already extracted from the text, identify relationships between them.

## Extracted entities
{entity_list}

## Relationship types to look for
{", ".join(RELATIONSHIP_TYPES)}

Relationship type meanings:
- occursIn: A hazard or event occurs in a location/community
- hasHazardType: An entity is associated with a hazard type
- serves: An agency/resource serves a community
- responsibleFor: An agency is responsible for an action or area
- locatedIn: An entity is physically located in a place
- targets: An action targets a community, hazard, or resource
- owns: An agency owns or manages a resource
- implementedBy: An action is implemented by an agency
- dependsOn: An entity depends on another entity
- partOf: An entity is part of a larger entity

## Text
{chunk}

## Output format
Respond ONLY with a valid JSON object:

{{
  "relationships": [
    {{
      "source_name": "SES",
      "source_type": "Agency",
      "target_name": "Smithville",
      "target_type": "Community",
      "relationship_type": "serves",
      "attributes": {{}},
      "confidence": 0.85,
      "evidence_text": "The SES serves the Smithville community..."
    }}
  ]
}}

Rules:
- source_name and target_name MUST match entity names from the list above
- relationship_type MUST be one of: {", ".join(RELATIONSHIP_TYPES)}
- confidence is 0.0 to 1.0
- Only include relationships supported by the text
- evidence_text is the phrase from the text supporting this relationship
"""

    # ── Response parsers ──────────────────────────────────────────────────────

    def _parse_entity_response(self, response: str) -> List[ExtractedEntity]:
        """Parse LLM JSON response into ExtractedEntity list."""
        data = self._parse_json(response)
        if not data:
            return []

        entities_raw = data.get("entities", [])
        if not isinstance(entities_raw, list):
            return []

        entities = []
        for item in entities_raw:
            try:
                entity_type = item.get("entity_type", "")
                name = item.get("name", "").strip()
                if not name or entity_type not in ENTITY_TYPES:
                    continue

                entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    name=name,
                    entity_subtype=item.get("entity_subtype"),
                    attributes=item.get("attributes", {}),
                    confidence=float(item.get("confidence", 0.5)),
                    evidence_text=item.get("evidence_text", ""),
                    location_text=item.get("location_text"),
                ))
            except (ValueError, TypeError) as e:
                logger.debug(f"Skipping malformed entity: {e}")
                continue

        return entities

    def _parse_relationship_response(self, response: str) -> List[ExtractedRelationship]:
        """Parse LLM JSON response into ExtractedRelationship list."""
        data = self._parse_json(response)
        if not data:
            return []

        rels_raw = data.get("relationships", [])
        if not isinstance(rels_raw, list):
            return []

        relationships = []
        for item in rels_raw:
            try:
                source_name = item.get("source_name", "").strip()
                target_name = item.get("target_name", "").strip()
                rel_type = item.get("relationship_type", "")

                if not source_name or not target_name or rel_type not in RELATIONSHIP_TYPES:
                    continue

                relationships.append(ExtractedRelationship(
                    source_name=source_name,
                    source_type=item.get("source_type", ""),
                    target_name=target_name,
                    target_type=item.get("target_type", ""),
                    relationship_type=rel_type,
                    attributes=item.get("attributes", {}),
                    confidence=float(item.get("confidence", 0.5)),
                    evidence_text=item.get("evidence_text", ""),
                ))
            except (ValueError, TypeError) as e:
                logger.debug(f"Skipping malformed relationship: {e}")
                continue

        return relationships

    def _parse_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response with fallback extraction."""
        # Direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Extract JSON object from surrounding text
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse JSON from LLM response: {response[:200]}...")
        return None

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _chunk_text(self, content: str, max_chars: int = 3000) -> List[str]:
        """
        Split content at paragraph boundaries with overlap.

        Ensures each chunk is under max_chars while preserving paragraph integrity.
        """
        if len(content) <= max_chars:
            return [content]

        paragraphs = content.split("\n\n")
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para) + 2  # +2 for the paragraph separator
            if current_len + para_len > max_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # Keep last paragraph for overlap/context
                current_chunk = [current_chunk[-1]] if current_chunk else []
                current_len = len(current_chunk[0]) + 2 if current_chunk else 0

            current_chunk.append(para)
            current_len += para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks if chunks else [content]

    def _deduplicate_entities(
        self, entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """Deduplicate entities by (lowered name, entity_type), keeping highest confidence."""
        seen: Dict[Tuple[str, str], ExtractedEntity] = {}
        for entity in entities:
            key = (entity.name.lower().strip(), entity.entity_type)
            existing = seen.get(key)
            if existing is None or entity.confidence > existing.confidence:
                seen[key] = entity
        return list(seen.values())
