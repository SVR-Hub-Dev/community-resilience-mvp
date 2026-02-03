"""Database queries for document processing."""

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Document, ProcessingStatus


async def get_unprocessed_documents(
    db: AsyncSession,
    limit: int = 100,
) -> Sequence[Document]:
    """
    Get documents that need full processing.

    Returns documents where:
    - needs_full_processing = True
    - processing_status is PENDING or NEEDS_LOCAL
    """
    result = await db.execute(
        select(Document)
        .where(Document.needs_full_processing == True)
        .where(
            Document.processing_status.in_(
                [
                    ProcessingStatus.PENDING.value,
                    ProcessingStatus.NEEDS_LOCAL.value,
                ]
            )
        )
        .order_by(Document.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def mark_document_processing(
    db: AsyncSession,
    document_id: int,
) -> bool:
    """Mark a document as currently being processed."""
    result = await db.execute(
        update(Document)
        .where(Document.id == document_id)
        .where(
            Document.processing_status.in_(
                [
                    ProcessingStatus.PENDING.value,
                    ProcessingStatus.NEEDS_LOCAL.value,
                ]
            )
        )
        .values(processing_status=ProcessingStatus.PROCESSING.value)
    )
    await db.commit()
    # For UPDATE statements, rowcount is available on the CursorResult
    return result.rowcount > 0  # type: ignore[union-attr]


async def update_document_processed(
    db: AsyncSession,
    document_id: int,
    content: str,
    processing_mode: str,
    metadata: Optional[dict] = None,
) -> bool:
    """
    Update a document with processed content.

    Called after local Docling processing completes.
    """
    values = {
        "content": content,
        "processing_mode": processing_mode,
        "processing_status": ProcessingStatus.COMPLETED.value,
        "processed_at": datetime.now(timezone.utc),
        "needs_full_processing": False,
    }

    result = await db.execute(
        update(Document).where(Document.id == document_id).values(**values)
    )
    await db.commit()
    return result.rowcount > 0  # type: ignore[union-attr]


async def mark_document_failed(
    db: AsyncSession,
    document_id: int,
    error_message: Optional[str] = None,
) -> bool:
    """Mark a document as failed to process."""
    result = await db.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(
            processing_status=ProcessingStatus.FAILED.value,
            processed_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return result.rowcount > 0  # type: ignore[union-attr]


async def get_document_processing_stats(db: AsyncSession) -> dict:
    """Get statistics about document processing."""
    from sqlalchemy import func

    result = await db.execute(
        select(
            Document.processing_status,
            func.count(Document.id).label("doc_count"),
        ).group_by(Document.processing_status)
    )

    stats: dict[str, int] = {}
    for row in result:
        stats[row.processing_status] = row.doc_count

    # Get count of documents needing full processing
    needs_processing = await db.execute(
        select(func.count(Document.id)).where(Document.needs_full_processing == True)
    )

    return {
        "by_status": stats,
        "needs_full_processing": needs_processing.scalar() or 0,
        "total": sum(stats.values()) if stats else 0,
    }
