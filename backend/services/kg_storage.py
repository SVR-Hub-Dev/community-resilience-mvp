"""Storage service for Knowledge Graph entities and relationships."""

import logging
import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from models.kg_models import KGEntity, KGEvidence, KGRelationship
from services.embeddings import embed_text
from services.kg_extractor import ExtractedEntity, ExtractedRelationship

logger = logging.getLogger(__name__)


class KGStorageService:
    """
    Stores extracted entities and relationships in the knowledge graph tables.

    Handles deduplication via canonical name matching and maintains
    evidence provenance linking facts back to source documents.
    """

    def store_extraction_results(
        self,
        db: Session,
        document_id: int,
        entities: List[ExtractedEntity],
        relationships: List[ExtractedRelationship],
    ) -> Tuple[List[int], List[int]]:
        """
        Store extracted entities and relationships, returning created/updated IDs.

        Args:
            db: Database session.
            document_id: Source document ID for evidence tracking.
            entities: Extracted entities from the LLM.
            relationships: Extracted relationships from the LLM.

        Returns:
            Tuple of (entity_ids, relationship_ids).
        """
        entity_ids: List[int] = []
        relationship_ids: List[int] = []

        # Store entities first (relationships need entity IDs)
        for entity in entities:
            try:
                eid = self._store_entity(db, entity, document_id)
                entity_ids.append(eid)
            except Exception as e:
                logger.error(f"Failed to store entity '{entity.name}': {e}")
                db.rollback()

        # Store relationships
        for rel in relationships:
            try:
                rid = self._store_relationship(db, rel, document_id)
                if rid is not None:
                    relationship_ids.append(rid)
            except Exception as e:
                logger.error(f"Failed to store relationship '{rel.source_name} -> {rel.target_name}': {e}")
                db.rollback()

        logger.info(
            f"Stored {len(entity_ids)} entities and {len(relationship_ids)} relationships "
            f"from document {document_id}"
        )
        return entity_ids, relationship_ids

    def _store_entity(
        self,
        db: Session,
        entity: ExtractedEntity,
        document_id: int,
    ) -> int:
        """
        Store or update a single entity. Returns the entity ID.

        If an entity with the same canonical name and type already exists,
        merges attributes and takes the higher confidence score.
        """
        canonical = self._normalize_name(entity.name)
        existing_id = self._find_entity_by_name(db, canonical, entity.entity_type)

        if existing_id is not None:
            # Update existing entity
            existing = db.query(KGEntity).filter(KGEntity.id == existing_id).first()
            if existing:
                existing.confidence_score = max(
                    existing.confidence_score or 0, entity.confidence
                )
                # Merge attributes (existing wins conflicts)
                merged_attrs = {**entity.attributes, **(existing.attributes or {})}
                existing.attributes = merged_attrs
                if entity.location_text and not existing.location_text:
                    existing.location_text = entity.location_text
                existing.updated_at = sa_func.now()
                db.flush()

            # Add evidence for this document
            self._store_evidence(
                db, document_id, entity.evidence_text,
                entity.confidence, entity_id=existing_id,
            )
            db.commit()
            logger.debug(f"Updated existing entity: {entity.name} (id={existing_id})")
            return existing_id

        # Create new entity
        embedding = embed_text(f"{entity.name} {entity.entity_type}")

        new_entity = KGEntity(
            entity_type=entity.entity_type,
            entity_subtype=entity.entity_subtype,
            name=entity.name,
            canonical_name=canonical,
            attributes=entity.attributes or {},
            location_text=entity.location_text,
            confidence_score=entity.confidence,
            extraction_method="llm_extracted",
            embedding=embedding,
        )
        db.add(new_entity)
        db.flush()  # Get the ID

        # Add evidence
        self._store_evidence(
            db, document_id, entity.evidence_text,
            entity.confidence, entity_id=new_entity.id,
        )
        db.commit()
        logger.debug(f"Created new entity: {entity.name} (id={new_entity.id})")
        return new_entity.id

    def _store_relationship(
        self,
        db: Session,
        rel: ExtractedRelationship,
        document_id: int,
    ) -> Optional[int]:
        """
        Store a single relationship. Returns relationship ID or None if
        source/target entities cannot be resolved.
        """
        source_canonical = self._normalize_name(rel.source_name)
        target_canonical = self._normalize_name(rel.target_name)

        source_id = self._find_entity_by_name(db, source_canonical, rel.source_type)
        target_id = self._find_entity_by_name(db, target_canonical, rel.target_type)

        if source_id is None or target_id is None:
            # Try looser matching without type constraint
            if source_id is None:
                source_id = self._find_entity_by_name_any_type(db, source_canonical)
            if target_id is None:
                target_id = self._find_entity_by_name_any_type(db, target_canonical)

        if source_id is None or target_id is None:
            logger.warning(
                f"Cannot resolve relationship: {rel.source_name} ({rel.source_type}) "
                f"-> {rel.target_name} ({rel.target_type}). "
                f"source_id={source_id}, target_id={target_id}"
            )
            return None

        # Check for existing relationship
        existing = db.query(KGRelationship).filter(
            KGRelationship.source_entity_id == source_id,
            KGRelationship.target_entity_id == target_id,
            KGRelationship.relationship_type == rel.relationship_type,
        ).first()

        if existing:
            existing.confidence_score = max(
                existing.confidence_score or 0, rel.confidence
            )
            merged_attrs = {**rel.attributes, **(existing.attributes or {})}
            existing.attributes = merged_attrs
            existing.updated_at = sa_func.now()
            db.flush()

            self._store_evidence(
                db, document_id, rel.evidence_text,
                rel.confidence, relationship_id=existing.id,
            )
            db.commit()
            logger.debug(f"Updated existing relationship: id={existing.id}")
            return existing.id

        # Create new relationship
        new_rel = KGRelationship(
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=rel.relationship_type,
            attributes=rel.attributes or {},
            confidence_score=rel.confidence,
            extraction_method="llm_extracted",
        )
        db.add(new_rel)
        db.flush()

        self._store_evidence(
            db, document_id, rel.evidence_text,
            rel.confidence, relationship_id=new_rel.id,
        )
        db.commit()
        logger.debug(f"Created new relationship: id={new_rel.id}")
        return new_rel.id

    def _find_entity_by_name(
        self, db: Session, canonical_name: str, entity_type: str
    ) -> Optional[int]:
        """Find an existing entity by canonical name and type."""
        result = db.query(KGEntity.id).filter(
            KGEntity.canonical_name == canonical_name,
            KGEntity.entity_type == entity_type,
            KGEntity.is_deleted.is_(False),
        ).first()
        return result[0] if result else None

    def _find_entity_by_name_any_type(
        self, db: Session, canonical_name: str
    ) -> Optional[int]:
        """Find an existing entity by canonical name regardless of type."""
        result = db.query(KGEntity.id).filter(
            KGEntity.canonical_name == canonical_name,
            KGEntity.is_deleted.is_(False),
        ).first()
        return result[0] if result else None

    def _store_evidence(
        self,
        db: Session,
        document_id: int,
        evidence_text: str,
        confidence: float,
        entity_id: Optional[int] = None,
        relationship_id: Optional[int] = None,
    ) -> int:
        """Create an evidence record linking a fact to its source document."""
        evidence = KGEvidence(
            entity_id=entity_id,
            relationship_id=relationship_id,
            document_id=document_id,
            evidence_text=evidence_text,
            extraction_confidence=confidence,
        )
        db.add(evidence)
        db.flush()
        return evidence.id

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalize an entity name for deduplication.

        Lowercases, strips whitespace, collapses internal whitespace,
        and removes punctuation except hyphens.
        """
        name = name.lower().strip()
        name = re.sub(r'[^\w\s-]', '', name)  # Remove punctuation except hyphens
        name = re.sub(r'\s+', ' ', name)       # Collapse whitespace
        return name
