"""Knowledge Graph API endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from auth.dependencies import require_editor, require_viewer
from auth.models import User
from db import get_db
from models.kg_models import ENTITY_TYPES, KGEntity, RELATIONSHIP_TYPES
from services.embeddings import embed_text
from services.kg_query import KGQueryService
from services.kg_storage import KGStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kg", tags=["knowledge-graph"])

# Service singletons
query_service = KGQueryService()
storage_service = KGStorageService()


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class KGEntityOut(BaseModel):
    """Output model for a KG entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_subtype: Optional[str] = None
    name: str
    attributes: Dict[str, Any] = {}
    location_text: Optional[str] = None
    confidence_score: float
    extraction_method: Optional[str] = None
    created_at: Optional[datetime] = None


class KGEntityListOut(BaseModel):
    """Paginated list of entities."""

    entities: List[KGEntityOut]
    total: int


class KGEntityDetailOut(KGEntityOut):
    """Entity with relationships and evidence."""

    outgoing_relationships: List[Dict[str, Any]] = []
    incoming_relationships: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    updated_at: Optional[datetime] = None


class KGRelationshipOut(BaseModel):
    """Output model for a KG relationship."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_entity_id: int
    target_entity_id: int
    relationship_type: str
    attributes: Dict[str, Any] = {}
    confidence_score: float
    created_at: Optional[datetime] = None


class KGRelationshipListOut(BaseModel):
    """Paginated list of relationships."""

    relationships: List[KGRelationshipOut]
    total: int


class KGStatsOut(BaseModel):
    """Knowledge graph statistics."""

    total_entities: int
    total_relationships: int
    entity_counts: Dict[str, int]
    relationship_counts: Dict[str, int]
    avg_confidence: float


class KGCoverageGapsOut(BaseModel):
    """Coverage gap analysis results."""

    gaps: List[KGEntityOut]
    count: int
    entity_type: str
    required_relationship: str
    target_type: str


class KGNetworkOut(BaseModel):
    """Network visualization data."""

    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class KGEntityCreateIn(BaseModel):
    """Input model for manually creating an entity."""

    entity_type: str
    name: str
    entity_subtype: Optional[str] = None
    attributes: Dict[str, Any] = {}
    location_text: Optional[str] = None
    confidence_score: float = 1.0  # Manual entries are high confidence


class KGEntityUpdateIn(BaseModel):
    """Input model for updating an entity."""

    name: Optional[str] = None
    entity_subtype: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    location_text: Optional[str] = None
    confidence_score: Optional[float] = None


# ── Read endpoints ────────────────────────────────────────────────────────────


@router.get("/entities", response_model=KGEntityListOut)
def list_entities(
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List knowledge graph entities with optional filtering."""
    if entity_type and entity_type not in ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type. Must be one of: {', '.join(ENTITY_TYPES)}",
        )

    entities, total = query_service.list_entities(
        db, entity_type=entity_type, search=search, limit=limit, offset=offset
    )
    return KGEntityListOut(
        entities=[KGEntityOut.model_validate(e) for e in entities],
        total=total,
    )


@router.get("/entities/search")
def search_entities(
    q: str = Query(..., min_length=1),
    entity_types: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=20, le=100),
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Search entities by text and vector similarity."""
    entities = query_service.search_entities(
        db, query=q, entity_types=entity_types, limit=limit
    )
    return {
        "results": [KGEntityOut.model_validate(e) for e in entities],
        "count": len(entities),
    }


@router.get("/entities/{entity_id}", response_model=KGEntityDetailOut)
def get_entity_detail(
    entity_id: int,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Get full entity detail with relationships and evidence."""
    detail = query_service.get_entity_detail(db, entity_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Entity not found")
    return detail


@router.get("/entities/{entity_id}/network", response_model=KGNetworkOut)
def get_entity_network(
    entity_id: int,
    max_depth: int = Query(default=2, ge=1, le=4),
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Get network visualization data centered on an entity."""
    # Verify entity exists
    entity = (
        db.query(KGEntity)
        .filter(KGEntity.id == entity_id, KGEntity.is_deleted.is_(False))
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    network = query_service.get_entity_network(db, entity_id, max_depth=max_depth)
    return network


@router.get("/relationships", response_model=KGRelationshipListOut)
def list_relationships(
    relationship_type: Optional[str] = None,
    source_entity_id: Optional[int] = None,
    target_entity_id: Optional[int] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List knowledge graph relationships with optional filtering."""
    relationships, total = query_service.list_relationships(
        db,
        relationship_type=relationship_type,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        limit=limit,
        offset=offset,
    )
    return KGRelationshipListOut(
        relationships=[KGRelationshipOut.model_validate(r) for r in relationships],
        total=total,
    )


@router.get("/statistics", response_model=KGStatsOut)
def get_statistics(
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Get knowledge graph summary statistics."""
    stats = query_service.get_statistics(db)
    return stats


@router.get("/coverage-gaps", response_model=KGCoverageGapsOut)
def get_coverage_gaps(
    entity_type: str = Query(...),
    required_relationship: str = Query(...),
    target_type: str = Query(...),
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """
    Find entities missing a required relationship.

    Example: entity_type=Community, required_relationship=serves, target_type=Agency
    → finds communities not served by any agency.
    """
    if entity_type not in ENTITY_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Invalid entity_type: {entity_type}"
        )
    if target_type not in ENTITY_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Invalid target_type: {target_type}"
        )
    if required_relationship not in RELATIONSHIP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid required_relationship: {required_relationship}",
        )

    gaps = query_service.find_coverage_gaps(
        db, entity_type, required_relationship, target_type
    )
    return KGCoverageGapsOut(
        gaps=[KGEntityOut.model_validate(e) for e in gaps],
        count=len(gaps),
        entity_type=entity_type,
        required_relationship=required_relationship,
        target_type=target_type,
    )


# ── Write endpoints ───────────────────────────────────────────────────────────


@router.post("/entities", response_model=dict)
def create_entity(
    payload: KGEntityCreateIn,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Manually create a knowledge graph entity."""
    if payload.entity_type not in ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity_type. Must be one of: {', '.join(ENTITY_TYPES)}",
        )

    canonical = storage_service._normalize_name(payload.name)
    embedding = embed_text(f"{payload.name} {payload.entity_type}")

    entity = KGEntity(
        entity_type=payload.entity_type,
        entity_subtype=payload.entity_subtype,
        name=payload.name,
        canonical_name=canonical,
        attributes=payload.attributes,
        location_text=payload.location_text,
        confidence_score=payload.confidence_score,
        extraction_method="manual",
        embedding=embedding,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)

    logger.info(f"Manually created entity: {entity.name} (id={entity.id})")
    return {"status": "ok", "id": entity.id}


@router.put("/entities/{entity_id}", response_model=dict)
def update_entity(
    entity_id: int,
    payload: KGEntityUpdateIn,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Update an existing knowledge graph entity."""
    entity = (
        db.query(KGEntity)
        .filter(KGEntity.id == entity_id, KGEntity.is_deleted.is_(False))
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    if payload.name is not None:
        entity.name = payload.name
        entity.canonical_name = storage_service._normalize_name(payload.name)
        entity.embedding = embed_text(f"{payload.name} {entity.entity_type}")
    if payload.entity_subtype is not None:
        entity.entity_subtype = payload.entity_subtype
    if payload.attributes is not None:
        entity.attributes = payload.attributes
    if payload.location_text is not None:
        entity.location_text = payload.location_text
    if payload.confidence_score is not None:
        entity.confidence_score = payload.confidence_score

    db.commit()
    logger.info(f"Updated entity: {entity.name} (id={entity.id})")
    return {"status": "ok", "id": entity.id}


@router.delete("/entities/{entity_id}", response_model=dict)
def delete_entity(
    entity_id: int,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Soft-delete a knowledge graph entity."""
    entity = (
        db.query(KGEntity)
        .filter(KGEntity.id == entity_id, KGEntity.is_deleted.is_(False))
        .first()
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    entity.is_deleted = True
    db.commit()
    logger.info(f"Soft-deleted entity: {entity.name} (id={entity.id})")
    return {"status": "ok", "id": entity.id}


# ── Metadata endpoints ────────────────────────────────────────────────────────


@router.get("/types")
def get_types(user: User = Depends(require_viewer)):
    """Get supported entity and relationship types."""
    return {
        "entity_types": ENTITY_TYPES,
        "relationship_types": RELATIONSHIP_TYPES,
    }
