"""SQLAlchemy ORM models for community resilience system."""

import enum
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

# Add backend directory to path for imports when running from subdirectory
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# Embedding dimension from configuration (384 for all-MiniLM-L6-v2)
EMBEDDING_DIM = settings.embedding_dimension


class ProcessingStatus(str, enum.Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_LOCAL = "needs_local"


class CommunityKnowledge(Base):
    """
    Local wisdom table - past experiences, patterns, stories, hazard notes.

    This provides context for the reasoning model and supports
    vector similarity search.
    """

    __tablename__ = "community_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(ARRAY(String))
    location = Column(String)
    hazard_type = Column(String)  # e.g., 'flood', 'fire', 'storm'
    source = Column(String)  # e.g., 'community workshop', 'elder interview'
    embedding = Column(Vector(EMBEDDING_DIM))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<CommunityKnowledge(id={self.id}, title='{self.title[:30]}...')>"


class CommunityEvent(Base):
    """
    Real-time reports or historical incidents.

    Feeds the reasoning model during response and builds
    a historical dataset for future training.
    """

    __tablename__ = "community_event"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # 'flood', 'fire', 'power_outage'
    description = Column(Text, nullable=False)
    location = Column(String)
    severity = Column(Integer)  # 1-5 scale
    reported_by = Column(String)  # name, group, or channel
    embedding = Column(Vector(EMBEDDING_DIM))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<CommunityEvent(id={self.id}, type='{self.event_type}')>"


class CommunityAsset(Base):
    """
    Places, resources, infrastructure, and capacities.

    Helps the model recommend shelters, routes, resources and
    supports preparedness and recovery planning.
    """

    __tablename__ = "community_asset"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    asset_type = Column(String, nullable=False)  # 'shelter', 'road', 'bridge', 'clinic'
    description = Column(Text)
    location = Column(String)
    capacity = Column(Integer)  # e.g., shelter capacity
    status = Column(String)  # 'operational', 'damaged', 'unknown'
    tags = Column(ARRAY(String))
    embedding = Column(Vector(EMBEDDING_DIM))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<CommunityAsset(id={self.id}, name='{self.name}')>"


class ModelFeedbackLog(Base):
    """
    Learning loop table - tracks model performance.

    Stores retrieved knowledge + model output for future
    fine-tuning and prompt improvement.
    """

    __tablename__ = "model_feedback_log"

    id = Column(Integer, primary_key=True, index=True)
    user_input = Column(Text, nullable=False)
    retrieved_knowledge_ids = Column(ARRAY(Integer))
    retrieved_asset_ids = Column(ARRAY(Integer))
    model_output = Column(Text, nullable=False)
    rating = Column(Integer)  # 1-5 scale
    comments = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ModelFeedbackLog(id={self.id}, rating={self.rating})>"


class Document(Base):
    """Document model for storing uploaded documents."""

    __tablename__ = "documents"

    # Document fields
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(ARRAY(String))
    location = Column(String)
    hazard_type = Column(String)  # e.g., 'flood', 'fire', 'storm'
    source = Column(String)  # e.g., 'community workshop', 'elder interview'
    embedding = Column(Vector(EMBEDDING_DIM))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Document processing fields (hybrid cloud/local support)
    needs_full_processing = Column(Boolean, default=False, nullable=False)
    processing_mode = Column(String(50), default="pending", nullable=False)
    raw_file_path = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_status = Column(
        String(50), default=ProcessingStatus.PENDING.value, nullable=False
    )

    # Knowledge graph extraction status
    kg_extraction_status = Column(String(50), server_default="pending")

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title[:30]}...')>"


class SyncMetadata(Base):
    """Metadata for cloud-local synchronization."""

    __tablename__ = "sync_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Common keys used for sync
    LAST_SYNC_TIMESTAMP = "last_sync_timestamp"
    LAST_PULL_TIMESTAMP = "last_pull_timestamp"
    LAST_PUSH_TIMESTAMP = "last_push_timestamp"
    SYNC_IN_PROGRESS = "sync_in_progress"

    @classmethod
    async def get_value(cls, db: "AsyncSession", key: str) -> Optional[str]:
        """Get a sync metadata value by key."""
        from sqlalchemy import select

        result = await db.execute(select(cls.value).where(cls.key == key))
        row = result.scalar_one_or_none()
        return row

    @classmethod
    async def set_value(cls, db: "AsyncSession", key: str, value: str) -> None:
        """Set a sync metadata value."""
        from sqlalchemy.dialects.postgresql import insert

        stmt = insert(cls).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(
            index_elements=["key"], set_={"value": value, "updated_at": func.now()}
        )
        await db.execute(stmt)
        await db.commit()


class SyncLog(Base):
    """Log of synchronization operations."""

    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sync_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'pull', 'push', 'process'
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'started', 'completed', 'failed'
    documents_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    class SyncType:
        PULL = "pull"
        PUSH = "push"
        PROCESS = "process"

    class Status:
        STARTED = "started"
        COMPLETED = "completed"
        FAILED = "failed"

    @classmethod
    async def start_sync(
        cls, db: "AsyncSession", sync_type: str, details: Optional[dict] = None
    ) -> "SyncLog":
        """Create a new sync log entry."""
        log = cls(
            sync_type=sync_type,
            status=cls.Status.STARTED,
            details=details,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    async def complete(
        self,
        db: "AsyncSession",
        documents_processed: int = 0,
        details: Optional[dict] = None,
    ) -> None:
        """Mark sync as completed."""
        self.status = self.Status.COMPLETED
        self.documents_processed = documents_processed
        self.completed_at = datetime.now(timezone.utc)
        if details:
            self.details = {**(self.details or {}), **details}
        await db.commit()

    async def fail(
        self, db: "AsyncSession", error_message: str, details: Optional[dict] = None
    ) -> None:
        """Mark sync as failed."""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now(timezone.utc)
        if details:
            self.details = {**(self.details or {}), **details}
        await db.commit()
