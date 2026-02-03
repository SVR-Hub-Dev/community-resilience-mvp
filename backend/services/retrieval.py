"""Vector similarity search service using pgvector."""

import logging
from typing import List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.models import CommunityKnowledge, CommunityAsset, CommunityEvent
from services.embeddings import embed_text

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Container for retrieval results across all entity types."""

    knowledge: List[CommunityKnowledge]
    assets: List[CommunityAsset]
    events: List[CommunityEvent]


def retrieve_relevant_knowledge(
    db: Session,
    query_embedding: List[float],
    limit: int = 5,
    hazard_type: Optional[str] = None,
    location: Optional[str] = None,
) -> List[CommunityKnowledge]:
    """
    Retrieve relevant community knowledge entries using vector similarity.

    Args:
        db: Database session
        query_embedding: The query vector
        limit: Maximum number of results
        hazard_type: Optional filter by hazard type
        location: Optional filter by location

    Returns:
        List of relevant CommunityKnowledge entries
    """
    query = db.query(CommunityKnowledge)

    # Apply optional filters
    if hazard_type:
        query = query.filter(CommunityKnowledge.hazard_type == hazard_type)
    if location:
        query = query.filter(CommunityKnowledge.location.ilike(f"%{location}%"))

    # Order by L2 distance (pgvector)
    query = query.order_by(
        CommunityKnowledge.embedding.l2_distance(query_embedding)
    ).limit(limit)

    results = query.all()
    logger.debug(f"Retrieved {len(results)} knowledge entries")
    return results


def retrieve_relevant_assets(
    db: Session,
    query_embedding: List[float],
    limit: int = 3,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[CommunityAsset]:
    """
    Retrieve relevant community assets using vector similarity.

    Args:
        db: Database session
        query_embedding: The query vector
        limit: Maximum number of results
        asset_type: Optional filter by asset type (e.g., 'shelter', 'road')
        status: Optional filter by status (e.g., 'operational')

    Returns:
        List of relevant CommunityAsset entries
    """
    query = db.query(CommunityAsset)

    if asset_type:
        query = query.filter(CommunityAsset.asset_type == asset_type)
    if status:
        query = query.filter(CommunityAsset.status == status)

    query = query.order_by(CommunityAsset.embedding.l2_distance(query_embedding)).limit(
        limit
    )

    results = query.all()
    logger.debug(f"Retrieved {len(results)} assets")
    return results


def retrieve_relevant_events(
    db: Session,
    query_embedding: List[float],
    limit: int = 3,
    event_type: Optional[str] = None,
) -> List[CommunityEvent]:
    """
    Retrieve relevant historical events using vector similarity.

    Args:
        db: Database session
        query_embedding: The query vector
        limit: Maximum number of results
        event_type: Optional filter by event type

    Returns:
        List of relevant CommunityEvent entries
    """
    query = db.query(CommunityEvent)

    if event_type:
        query = query.filter(CommunityEvent.event_type == event_type)

    query = query.order_by(CommunityEvent.embedding.l2_distance(query_embedding)).limit(
        limit
    )

    results = query.all()
    logger.debug(f"Retrieved {len(results)} events")
    return results


def retrieve_all_context(
    db: Session,
    query_text: str,
    knowledge_limit: int = 5,
    asset_limit: int = 3,
    event_limit: int = 3,
) -> RetrievalResult:
    """
    Retrieve all relevant context for a query.

    This is the main retrieval function that combines knowledge,
    assets, and events into a single result.

    Args:
        db: Database session
        query_text: The user's situation description
        knowledge_limit: Max knowledge entries to retrieve
        asset_limit: Max assets to retrieve
        event_limit: Max events to retrieve

    Returns:
        RetrievalResult containing all relevant entries
    """
    # Generate embedding for the query
    query_embedding = embed_text(query_text)

    # Retrieve from all sources
    knowledge = retrieve_relevant_knowledge(db, query_embedding, limit=knowledge_limit)
    assets = retrieve_relevant_assets(db, query_embedding, limit=asset_limit)
    events = retrieve_relevant_events(db, query_embedding, limit=event_limit)

    logger.info(
        f"Retrieved context: {len(knowledge)} knowledge, "
        f"{len(assets)} assets, {len(events)} events"
    )

    return RetrievalResult(
        knowledge=knowledge,
        assets=assets,
        events=events,
    )
