"""FastAPI application for Community Resilience Reasoning System."""

import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from db import get_db
from models.models import (
    CommunityKnowledge,
    CommunityAsset,
    CommunityEvent,
    ModelFeedbackLog,
)
from auth.router import router as auth_router
from api.kg_router import router as kg_router
from api.documents import router as documents_router
from api.sync import router as sync_router
from auth.dependencies import require_viewer, require_editor
from auth.models import User
from services.embeddings import embed_text
from services.retrieval import retrieve_all_context, retrieve_relevant_knowledge
from services.reasoning import run_reasoning_model
from llm_client import llm

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Pydantic Models ---


class KnowledgeIn(BaseModel):
    """Input model for creating knowledge entries."""

    title: str
    description: str
    tags: Optional[List[str]] = None
    location: Optional[str] = None
    hazard_type: Optional[str] = None
    source: Optional[str] = None


class KnowledgeOut(BaseModel):
    """Output model for knowledge entries."""

    id: int
    title: str
    description: str
    tags: Optional[List[str]]
    location: Optional[str]
    hazard_type: Optional[str]
    source: Optional[str]

    class Config:
        from_attributes = True


class QueryIn(BaseModel):
    """Input model for reasoning queries."""

    text: str


class ActionOut(BaseModel):
    """Output model for recommended actions."""

    priority: int
    action: str
    rationale: str


class QueryOut(BaseModel):
    """Output model for reasoning responses."""

    summary: str
    actions: List[ActionOut]
    retrieved_knowledge_ids: List[int]
    log_id: int
    error: Optional[bool] = None


class FeedbackIn(BaseModel):
    """Input model for feedback submission."""

    log_id: int
    rating: int
    comments: Optional[str] = None


class EventIn(BaseModel):
    """Input model for event ingestion."""

    event_type: str
    description: str
    location: Optional[str] = None
    severity: Optional[int] = None
    reported_by: Optional[str] = None


class AssetIn(BaseModel):
    """Input model for asset ingestion."""

    name: str
    asset_type: str
    description: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class HealthOut(BaseModel):
    """Output model for health check."""

    status: str
    database: bool
    llm: bool


# --- Application Lifecycle ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting Community Resilience API...")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    yield
    logger.info("Shutting down...")


# --- Create Application ---

app = FastAPI(
    title="Community Resilience Reasoning API",
    description="AI-powered disaster response recommendations using community knowledge",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(kg_router)
app.include_router(documents_router)
app.include_router(sync_router)


# --- Health Check ---


@app.get("/health", response_model=HealthOut)
async def health_check(db: Session = Depends(get_db)):
    """Check API health and dependencies."""
    # Check database
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    # Check LLM
    llm_healthy = await llm.health_check()

    status = "healthy" if (db_healthy and llm_healthy) else "degraded"

    return HealthOut(
        status=status,
        database=db_healthy,
        llm=llm_healthy,
    )


# --- Knowledge Endpoints ---


@app.post("/ingest", response_model=dict)
def ingest_knowledge(
    item: KnowledgeIn,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Add a new community knowledge entry. Requires editor role."""
    logger.info(f"Ingesting knowledge: {item.title}")

    embedding = embed_text(item.description)

    entry = CommunityKnowledge(
        title=item.title,
        description=item.description,
        tags=item.tags,
        location=item.location,
        hazard_type=item.hazard_type,
        source=item.source,
        embedding=embedding,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info(f"Knowledge entry created: id={entry.id}")
    return {"status": "ok", "id": entry.id}


@app.get("/knowledge", response_model=List[KnowledgeOut])
def list_knowledge(
    hazard_type: Optional[str] = None,
    location: Optional[str] = None,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List all community knowledge entries. Requires viewer role."""
    query = db.query(CommunityKnowledge)

    if hazard_type:
        query = query.filter(CommunityKnowledge.hazard_type == hazard_type)
    if location:
        query = query.filter(CommunityKnowledge.location.ilike(f"%{location}%"))

    entries = query.order_by(CommunityKnowledge.created_at.desc()).all()
    return entries


@app.get("/knowledge/{knowledge_id}", response_model=KnowledgeOut)
def get_knowledge(
    knowledge_id: int,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Get a specific knowledge entry. Requires viewer role."""
    entry = (
        db.query(CommunityKnowledge)
        .filter(CommunityKnowledge.id == knowledge_id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    return entry


@app.put("/knowledge/{knowledge_id}", response_model=dict)
def update_knowledge(
    knowledge_id: int,
    item: KnowledgeIn,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Update a knowledge entry. Requires editor role."""
    entry = (
        db.query(CommunityKnowledge)
        .filter(CommunityKnowledge.id == knowledge_id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    entry.title = item.title
    entry.description = item.description
    entry.tags = item.tags
    entry.location = item.location
    entry.hazard_type = item.hazard_type
    entry.source = item.source
    entry.embedding = embed_text(item.description)

    db.commit()
    return {"status": "ok", "id": entry.id}


@app.delete("/knowledge/{knowledge_id}", response_model=dict)
def delete_knowledge(
    knowledge_id: int,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Delete a knowledge entry. Requires editor role."""
    entry = (
        db.query(CommunityKnowledge)
        .filter(CommunityKnowledge.id == knowledge_id)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    db.delete(entry)
    db.commit()
    return {"status": "ok", "id": knowledge_id}


# --- Query/Reasoning Endpoint ---


@app.post("/query", response_model=QueryOut)
async def query_reasoning(
    payload: QueryIn,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """
    Main reasoning endpoint.

    Takes a situation description, retrieves relevant context,
    and returns prioritized recommendations.
    """
    logger.info(f"Processing query: {payload.text[:100]}...")

    # Retrieve relevant context
    context = retrieve_all_context(db, payload.text)

    # Run reasoning model
    result = await run_reasoning_model(payload.text, context)

    # Log the interaction
    log = ModelFeedbackLog(
        user_input=payload.text,
        retrieved_knowledge_ids=[k.id for k in context.knowledge],
        retrieved_asset_ids=[a.id for a in context.assets],
        model_output=str(result),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Format response
    actions = [
        ActionOut(
            priority=a.get("priority", i + 1),
            action=a.get("action", ""),
            rationale=a.get("rationale", ""),
        )
        for i, a in enumerate(result.get("actions", []))
    ]

    return QueryOut(
        summary=result.get("summary", ""),
        actions=actions,
        retrieved_knowledge_ids=[k.id for k in context.knowledge],
        log_id=log.id,
        error=result.get("error"),
    )


# --- Feedback Endpoint ---


@app.post("/feedback", response_model=dict)
def submit_feedback(
    payload: FeedbackIn,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """Submit feedback on a reasoning response. Requires viewer role."""
    log = (
        db.query(ModelFeedbackLog).filter(ModelFeedbackLog.id == payload.log_id).first()
    )

    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")

    log.rating = payload.rating
    log.comments = payload.comments
    db.commit()

    logger.info(f"Feedback recorded: log_id={payload.log_id}, rating={payload.rating}")
    return {"status": "feedback recorded"}


# --- Event Endpoints ---


@app.post("/events", response_model=dict)
def ingest_event(
    event: EventIn,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Ingest a real-time or historical event. Requires editor role."""
    embedding = embed_text(event.description)

    entry = CommunityEvent(
        event_type=event.event_type,
        description=event.description,
        location=event.location,
        severity=event.severity,
        reported_by=event.reported_by,
        embedding=embedding,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info(f"Event created: id={entry.id}, type={entry.event_type}")
    return {"status": "ok", "id": entry.id}


@app.get("/events")
def list_events(
    event_type: Optional[str] = None,
    limit: int = 20,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List recent events. Requires viewer role."""
    query = db.query(CommunityEvent)

    if event_type:
        query = query.filter(CommunityEvent.event_type == event_type)

    events = query.order_by(CommunityEvent.timestamp.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "description": e.description,
            "location": e.location,
            "severity": e.severity,
            "reported_by": e.reported_by,
            "timestamp": e.timestamp,
        }
        for e in events
    ]


# --- Asset Endpoints ---


@app.post("/assets", response_model=dict)
def ingest_asset(
    asset: AssetIn,
    user: User = Depends(require_editor),
    db: Session = Depends(get_db),
):
    """Ingest a community asset. Requires editor role."""
    embedding = embed_text(asset.description or asset.name)

    entry = CommunityAsset(
        name=asset.name,
        asset_type=asset.asset_type,
        description=asset.description,
        location=asset.location,
        capacity=asset.capacity,
        status=asset.status,
        tags=asset.tags,
        embedding=embedding,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    logger.info(f"Asset created: id={entry.id}, name={entry.name}")
    return {"status": "ok", "id": entry.id}


@app.get("/assets")
def list_assets(
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    user: User = Depends(require_viewer),
    db: Session = Depends(get_db),
):
    """List community assets. Requires viewer role."""
    query = db.query(CommunityAsset)

    if asset_type:
        query = query.filter(CommunityAsset.asset_type == asset_type)
    if status:
        query = query.filter(CommunityAsset.status == status)

    assets = query.order_by(CommunityAsset.updated_at.desc()).all()

    return [
        {
            "id": a.id,
            "name": a.name,
            "asset_type": a.asset_type,
            "description": a.description,
            "location": a.location,
            "capacity": a.capacity,
            "status": a.status,
            "tags": a.tags,
        }
        for a in assets
    ]


# --- Run with uvicorn ---

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
