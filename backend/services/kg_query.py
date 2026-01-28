"""Query service for the Knowledge Graph."""

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func as sa_func, or_
from sqlalchemy.orm import Session

from models.kg_models import KGEntity, KGEvidence, KGRelationship
from services.embeddings import embed_text

logger = logging.getLogger(__name__)


class KGQueryService:
    """
    Read-only service for querying the knowledge graph.

    Provides listing, search (text + vector), statistics,
    coverage gap detection, and network traversal.
    """

    # ── List & filter ─────────────────────────────────────────────────────────

    def list_entities(
        self,
        db: Session,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[KGEntity], int]:
        """
        List entities with optional type filter and text search.

        Returns:
            Tuple of (entities, total_count).
        """
        query = db.query(KGEntity).filter(KGEntity.is_deleted.is_(False))

        if entity_type:
            query = query.filter(KGEntity.entity_type == entity_type)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    KGEntity.name.ilike(search_pattern),
                    KGEntity.location_text.ilike(search_pattern),
                )
            )

        total = query.count()
        entities = (
            query
            .order_by(KGEntity.confidence_score.desc(), KGEntity.name)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return entities, total

    def list_relationships(
        self,
        db: Session,
        relationship_type: Optional[str] = None,
        source_entity_id: Optional[int] = None,
        target_entity_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[KGRelationship], int]:
        """List relationships with optional filters."""
        query = db.query(KGRelationship).filter(KGRelationship.is_deleted.is_(False))

        if relationship_type:
            query = query.filter(KGRelationship.relationship_type == relationship_type)
        if source_entity_id:
            query = query.filter(KGRelationship.source_entity_id == source_entity_id)
        if target_entity_id:
            query = query.filter(KGRelationship.target_entity_id == target_entity_id)

        total = query.count()
        relationships = (
            query
            .order_by(KGRelationship.confidence_score.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return relationships, total

    # ── Detail ────────────────────────────────────────────────────────────────

    def get_entity_detail(
        self, db: Session, entity_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get full entity detail including relationships and evidence.

        Returns:
            Dict with entity data, outgoing/incoming relationships, and evidence.
            None if the entity doesn't exist.
        """
        entity = db.query(KGEntity).filter(
            KGEntity.id == entity_id,
            KGEntity.is_deleted.is_(False),
        ).first()

        if not entity:
            return None

        # Outgoing relationships
        outgoing = (
            db.query(KGRelationship)
            .filter(
                KGRelationship.source_entity_id == entity_id,
                KGRelationship.is_deleted.is_(False),
            )
            .all()
        )

        # Incoming relationships
        incoming = (
            db.query(KGRelationship)
            .filter(
                KGRelationship.target_entity_id == entity_id,
                KGRelationship.is_deleted.is_(False),
            )
            .all()
        )

        # Evidence records
        evidence = (
            db.query(KGEvidence)
            .filter(KGEvidence.entity_id == entity_id)
            .all()
        )

        def format_relationship(rel: KGRelationship, direction: str) -> Dict[str, Any]:
            """Format a relationship with the connected entity's info."""
            if direction == "outgoing":
                connected = db.query(KGEntity).filter(KGEntity.id == rel.target_entity_id).first()
            else:
                connected = db.query(KGEntity).filter(KGEntity.id == rel.source_entity_id).first()

            return {
                "id": rel.id,
                "relationship_type": rel.relationship_type,
                "confidence_score": rel.confidence_score,
                "attributes": rel.attributes,
                "entity_id": connected.id if connected else None,
                "entity_name": connected.name if connected else "Unknown",
                "entity_type": connected.entity_type if connected else "Unknown",
            }

        return {
            "id": entity.id,
            "entity_type": entity.entity_type,
            "entity_subtype": entity.entity_subtype,
            "name": entity.name,
            "attributes": entity.attributes,
            "location_text": entity.location_text,
            "confidence_score": entity.confidence_score,
            "extraction_method": entity.extraction_method,
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
            "outgoing_relationships": [
                format_relationship(r, "outgoing") for r in outgoing
            ],
            "incoming_relationships": [
                format_relationship(r, "incoming") for r in incoming
            ],
            "evidence": [
                {
                    "id": e.id,
                    "document_id": e.document_id,
                    "evidence_text": e.evidence_text,
                    "extraction_confidence": e.extraction_confidence,
                }
                for e in evidence
            ],
        }

    # ── Search ────────────────────────────────────────────────────────────────

    def search_entities(
        self,
        db: Session,
        query: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[KGEntity]:
        """
        Search entities using text matching and vector similarity.

        Text matches are prioritized, then vector similarity for fuzzy results.
        """
        results: List[KGEntity] = []
        seen_ids = set()

        base_filter = [KGEntity.is_deleted.is_(False)]
        if entity_types:
            base_filter.append(KGEntity.entity_type.in_(entity_types))

        # Phase 1: Exact/ILIKE text matches
        search_pattern = f"%{query}%"
        text_matches = (
            db.query(KGEntity)
            .filter(
                *base_filter,
                or_(
                    KGEntity.name.ilike(search_pattern),
                    KGEntity.location_text.ilike(search_pattern),
                ),
            )
            .order_by(KGEntity.confidence_score.desc())
            .limit(limit)
            .all()
        )
        for entity in text_matches:
            if entity.id not in seen_ids:
                results.append(entity)
                seen_ids.add(entity.id)

        # Phase 2: Vector similarity (if we still need more results)
        remaining = limit - len(results)
        if remaining > 0:
            query_embedding = embed_text(query)
            vector_matches = (
                db.query(KGEntity)
                .filter(*base_filter)
                .order_by(KGEntity.embedding.l2_distance(query_embedding))
                .limit(remaining + len(seen_ids))  # Fetch extra to account for overlaps
                .all()
            )
            for entity in vector_matches:
                if entity.id not in seen_ids and len(results) < limit:
                    results.append(entity)
                    seen_ids.add(entity.id)

        return results

    # ── Statistics ─────────────────────────────────────────────────────────────

    def get_statistics(self, db: Session) -> Dict[str, Any]:
        """Get summary statistics for the knowledge graph."""
        # Entity counts by type
        entity_counts_raw = (
            db.query(KGEntity.entity_type, sa_func.count(KGEntity.id))
            .filter(KGEntity.is_deleted.is_(False))
            .group_by(KGEntity.entity_type)
            .all()
        )
        entity_counts = {row[0]: row[1] for row in entity_counts_raw}
        total_entities = sum(entity_counts.values())

        # Relationship counts by type
        rel_counts_raw = (
            db.query(KGRelationship.relationship_type, sa_func.count(KGRelationship.id))
            .filter(KGRelationship.is_deleted.is_(False))
            .group_by(KGRelationship.relationship_type)
            .all()
        )
        relationship_counts = {row[0]: row[1] for row in rel_counts_raw}
        total_relationships = sum(relationship_counts.values())

        # Average confidence
        avg_confidence_result = (
            db.query(sa_func.avg(KGEntity.confidence_score))
            .filter(KGEntity.is_deleted.is_(False))
            .scalar()
        )
        avg_confidence = round(float(avg_confidence_result or 0), 3)

        return {
            "total_entities": total_entities,
            "total_relationships": total_relationships,
            "entity_counts": entity_counts,
            "relationship_counts": relationship_counts,
            "avg_confidence": avg_confidence,
        }

    # ── Coverage gaps ─────────────────────────────────────────────────────────

    def find_coverage_gaps(
        self,
        db: Session,
        entity_type: str,
        required_relationship: str,
        target_type: str,
    ) -> List[KGEntity]:
        """
        Find entities that are missing a required relationship.

        Example: Communities without any "responsibleFor" Agency —
            find_coverage_gaps(db, "Community", "responsibleFor", "Agency")

        This finds entities of `entity_type` that do NOT have an outgoing
        relationship of `required_relationship` to any entity of `target_type`.
        """
        # Subquery: entity IDs that DO have the required relationship
        has_relationship = (
            db.query(KGRelationship.source_entity_id)
            .join(
                KGEntity,
                KGEntity.id == KGRelationship.target_entity_id,
            )
            .filter(
                KGRelationship.relationship_type == required_relationship,
                KGRelationship.is_deleted.is_(False),
                KGEntity.entity_type == target_type,
                KGEntity.is_deleted.is_(False),
            )
            .subquery()
        )

        # Entities that lack the relationship
        gaps = (
            db.query(KGEntity)
            .filter(
                KGEntity.entity_type == entity_type,
                KGEntity.is_deleted.is_(False),
                ~KGEntity.id.in_(db.query(has_relationship)),
            )
            .order_by(KGEntity.name)
            .all()
        )
        return gaps

    # ── Network visualization ─────────────────────────────────────────────────

    def get_entity_network(
        self,
        db: Session,
        entity_id: int,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """
        BFS traversal from an entity to build a network visualization payload.

        Returns:
            Dict with "nodes" and "edges" lists for frontend rendering.
        """
        nodes: Dict[int, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []
        visited = set()
        queue = deque([(entity_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            # Load entity
            entity = db.query(KGEntity).filter(
                KGEntity.id == current_id,
                KGEntity.is_deleted.is_(False),
            ).first()
            if not entity:
                continue

            nodes[current_id] = {
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "entity_subtype": entity.entity_subtype,
                "confidence_score": entity.confidence_score,
            }

            if depth < max_depth:
                # Outgoing relationships
                outgoing = (
                    db.query(KGRelationship)
                    .filter(
                        KGRelationship.source_entity_id == current_id,
                        KGRelationship.is_deleted.is_(False),
                    )
                    .all()
                )
                for rel in outgoing:
                    edges.append({
                        "id": rel.id,
                        "source": rel.source_entity_id,
                        "target": rel.target_entity_id,
                        "relationship_type": rel.relationship_type,
                        "confidence_score": rel.confidence_score,
                    })
                    if rel.target_entity_id not in visited:
                        queue.append((rel.target_entity_id, depth + 1))

                # Incoming relationships
                incoming = (
                    db.query(KGRelationship)
                    .filter(
                        KGRelationship.target_entity_id == current_id,
                        KGRelationship.is_deleted.is_(False),
                    )
                    .all()
                )
                for rel in incoming:
                    edges.append({
                        "id": rel.id,
                        "source": rel.source_entity_id,
                        "target": rel.target_entity_id,
                        "relationship_type": rel.relationship_type,
                        "confidence_score": rel.confidence_score,
                    })
                    if rel.source_entity_id not in visited:
                        queue.append((rel.source_entity_id, depth + 1))

        # Deduplicate edges
        seen_edges = set()
        unique_edges = []
        for edge in edges:
            key = (edge["source"], edge["target"], edge["relationship_type"])
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append(edge)

        return {
            "nodes": list(nodes.values()),
            "edges": unique_edges,
        }
