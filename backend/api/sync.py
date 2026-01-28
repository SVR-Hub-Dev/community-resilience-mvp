"""Sync API endpoints for cloud-local document synchronization."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import SyncConfig
from db import get_db
from models.document_queries import (
    get_unprocessed_documents,
    mark_document_processing,
    update_document_processed,
    mark_document_failed,
)
from models.models import Document, ProcessingStatus, SyncLog, SyncMetadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


# =============================================================================
# Request/Response Models
# =============================================================================


class UnprocessedDocumentResponse(BaseModel):
    """Response model for unprocessed document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    raw_file_path: Optional[str]
    processing_status: str
    created_at: datetime


class ProcessedContentRequest(BaseModel):
    """Request model for submitting processed content."""

    content: str
    processing_mode: str
    metadata: Optional[dict] = None
    sections: Optional[list[dict]] = None


class SyncPullResponse(BaseModel):
    """Response model for sync pull."""

    documents: list[dict]
    sync_timestamp: datetime
    has_more: bool


class SyncPushRequest(BaseModel):
    """Request model for sync push from local."""

    documents: list[dict]
    sync_timestamp: datetime


class SyncPushResponse(BaseModel):
    """Response model for sync push."""

    processed_count: int
    failed_count: int
    errors: list[dict]


# =============================================================================
# API Key Authentication
# =============================================================================


async def verify_sync_api_key(
    x_sync_api_key: Optional[str] = Header(None, alias="X-Sync-API-Key"),
) -> str:
    """Verify the sync API key from request header."""
    if not SyncConfig.SYNC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sync not configured on this server",
        )

    if not x_sync_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Sync-API-Key header",
        )

    if x_sync_api_key != SyncConfig.SYNC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_sync_api_key


# =============================================================================
# Sync Endpoints
# =============================================================================


@router.get("/documents/unprocessed", response_model=list[UnprocessedDocumentResponse])
async def list_unprocessed_documents(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_sync_api_key),
) -> list[UnprocessedDocumentResponse]:
    """
    List documents that need full processing.

    Used by local sync workers to discover documents to process.
    """
    documents = await get_unprocessed_documents(db, limit=limit)

    return [UnprocessedDocumentResponse.model_validate(doc) for doc in documents]


@router.get("/documents/{document_id}/download")
async def download_document_file(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_sync_api_key),
):
    """
    Download the raw file for a document.

    Used by local sync workers to get files for processing.
    """
    from fastapi.responses import FileResponse
    from pathlib import Path

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    raw_path: Optional[str] = document.raw_file_path  # type: ignore[assignment]
    if not raw_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} has no raw file",
        )

    file_path = Path(raw_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found on server",
        )

    # Mark as processing
    await mark_document_processing(db, document_id)

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.post("/documents/{document_id}/processed")
async def submit_processed_content(
    document_id: int,
    request: ProcessedContentRequest,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_sync_api_key),
) -> dict:
    """
    Submit processed content for a document.

    Called by local sync workers after Docling processing completes.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Update document with processed content
    success = await update_document_processed(
        db=db,
        document_id=document_id,
        content=request.content,
        processing_mode=request.processing_mode,
        metadata=request.metadata,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Failed to update document {document_id}",
        )

    logger.info(f"Document {document_id} processed successfully")

    return {
        "success": True,
        "document_id": document_id,
        "processing_mode": request.processing_mode,
    }


@router.post("/documents/{document_id}/failed")
async def mark_processing_failed(
    document_id: int,
    error_message: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_sync_api_key),
) -> dict:
    """
    Mark a document as failed to process.

    Called by local sync workers when processing fails.
    """
    success = await mark_document_failed(db, document_id, error_message)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    logger.warning(f"Document {document_id} marked as failed: {error_message}")

    return {
        "success": True,
        "document_id": document_id,
        "status": ProcessingStatus.FAILED.value,
    }


@router.get("/pull", response_model=SyncPullResponse)
async def sync_pull(
    since: Optional[datetime] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_sync_api_key),
) -> SyncPullResponse:
    """
    Pull changes since a given timestamp.

    Used by local instances to sync new/updated documents from cloud.
    """
    # Start sync log
    sync_log = await SyncLog.start_sync(
        db, SyncLog.SyncType.PULL, {"since": since.isoformat() if since else None}
    )

    try:
        # Query documents updated since timestamp
        query = select(Document).order_by(Document.created_at.asc()).limit(limit + 1)

        if since:
            query = query.where(Document.created_at > since)

        result = await db.execute(query)
        documents = list(result.scalars().all())

        # Check if there are more documents
        has_more = len(documents) > limit
        if has_more:
            documents = documents[:limit]

        # Convert to response format
        doc_list = [
            {
                "id": doc.id,
                "title": doc.title,
                "description": doc.description,
                "tags": doc.tags,
                "location": doc.location,
                "hazard_type": doc.hazard_type,
                "processing_status": doc.processing_status,
                "needs_full_processing": doc.needs_full_processing,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,  # type: ignore[union-attr]
            }
            for doc in documents
        ]

        sync_timestamp = datetime.now(timezone.utc)

        # Update sync metadata
        await SyncMetadata.set_value(
            db, SyncMetadata.LAST_PULL_TIMESTAMP, sync_timestamp.isoformat()
        )

        # Complete sync log
        await sync_log.complete(db, documents_processed=len(doc_list))

        return SyncPullResponse(
            documents=doc_list,
            sync_timestamp=sync_timestamp,
            has_more=has_more,
        )

    except Exception as e:
        await sync_log.fail(db, str(e))
        raise


@router.post("/push", response_model=SyncPushResponse)
async def sync_push(
    request: SyncPushRequest,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_sync_api_key),
) -> SyncPushResponse:
    """
    Accept changes pushed from a local instance.

    Used by local instances to push processed documents to cloud.
    """
    # Start sync log
    sync_log = await SyncLog.start_sync(
        db,
        SyncLog.SyncType.PUSH,
        {"document_count": len(request.documents)},
    )

    processed_count = 0
    failed_count = 0
    errors: list[dict] = []

    try:
        for doc_data in request.documents:
            try:
                doc_id = doc_data.get("id")
                if not doc_id:
                    errors.append({"error": "Missing document ID", "data": doc_data})
                    failed_count += 1
                    continue

                # Update document with processed content
                success = await update_document_processed(
                    db=db,
                    document_id=doc_id,
                    content=doc_data.get("content", ""),
                    processing_mode=doc_data.get("processing_mode", "local"),
                    metadata=doc_data.get("metadata"),
                )

                if success:
                    processed_count += 1
                else:
                    errors.append(
                        {"document_id": doc_id, "error": "Failed to update document"}
                    )
                    failed_count += 1

            except Exception as e:
                errors.append({"document_id": doc_data.get("id"), "error": str(e)})
                failed_count += 1

        # Update sync metadata
        await SyncMetadata.set_value(
            db,
            SyncMetadata.LAST_PUSH_TIMESTAMP,
            datetime.now(timezone.utc).isoformat(),
        )

        # Complete sync log
        await sync_log.complete(
            db,
            documents_processed=processed_count,
            details={"failed_count": failed_count, "errors": errors[:10]},
        )

        return SyncPushResponse(
            processed_count=processed_count,
            failed_count=failed_count,
            errors=errors,
        )

    except Exception as e:
        await sync_log.fail(db, str(e))
        raise


@router.get("/status")
async def sync_status(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_sync_api_key),
) -> dict:
    """Get sync status and statistics."""
    from models.document_queries import get_document_processing_stats

    # Get processing stats
    stats = await get_document_processing_stats(db)

    # Get last sync timestamps
    last_pull = await SyncMetadata.get_value(db, SyncMetadata.LAST_PULL_TIMESTAMP)
    last_push = await SyncMetadata.get_value(db, SyncMetadata.LAST_PUSH_TIMESTAMP)
    last_sync = await SyncMetadata.get_value(db, SyncMetadata.LAST_SYNC_TIMESTAMP)

    # Get recent sync logs
    recent_logs = await db.execute(
        select(SyncLog).order_by(SyncLog.started_at.desc()).limit(10)
    )

    return {
        "sync_enabled": SyncConfig.SYNC_ENABLED,
        "processing_stats": stats,
        "last_pull": last_pull,
        "last_push": last_push,
        "last_sync": last_sync,
        "recent_syncs": [
            {
                "id": log.id,
                "sync_type": log.sync_type,
                "status": log.status,
                "documents_processed": log.documents_processed,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": (
                    log.completed_at.isoformat() if log.completed_at else None
                ),
            }
            for log in recent_logs.scalars().all()
        ],
    }
