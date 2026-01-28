"""Document upload and management API endpoints."""

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from config import DeploymentConfig, DeploymentMode
from db import get_db, SessionLocal
from models.models import Document, ProcessingStatus
from services.document_processor import document_processor
from services.kg_extractor import KGExtractor
from services.kg_storage import KGStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# KG extraction services
_kg_extractor = KGExtractor()
_kg_storage = KGStorageService()


async def _extract_kg_background(
    document_id: int, content: str, metadata: dict
) -> None:
    """Background task: extract KG entities from a processed document."""
    db = SessionLocal()
    try:
        # Mark as processing
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.kg_extraction_status = "processing"
            db.commit()

        # Run extraction
        entities, relationships = await _kg_extractor.extract_from_text(
            content, metadata
        )

        # Store results
        _kg_storage.store_extraction_results(db, document_id, entities, relationships)

        # Mark as completed
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.kg_extraction_status = "completed"
            db.commit()

        logger.info(
            f"KG extraction complete for document {document_id}: "
            f"{len(entities)} entities, {len(relationships)} relationships"
        )
    except Exception:
        logger.exception(f"KG extraction failed for document {document_id}")
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.kg_extraction_status = "failed"
                db.commit()
        except Exception:
            logger.exception("Failed to update kg_extraction_status to failed")
    finally:
        db.close()


# Storage directory for uploaded files
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    processing_mode: str
    processing_status: str
    needs_full_processing: bool
    message: str


class DocumentStatusResponse(BaseModel):
    """Response model for document status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    processing_mode: str
    processing_status: str
    needs_full_processing: bool
    processed_at: Optional[datetime] = None


def validate_file_size(file: UploadFile) -> None:
    """Validate file size based on deployment mode."""
    max_size_bytes = DeploymentConfig.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Check Content-Length header if available
    if file.size and file.size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {DeploymentConfig.MAX_UPLOAD_SIZE_MB}MB",
        )


def validate_file_type(filename: str) -> bool:
    """Check if file type is supported in current deployment mode."""
    if not DeploymentConfig.is_file_supported(filename):
        supported = ", ".join(DeploymentConfig.get_supported_extensions())
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type not supported in {DeploymentConfig.DEPLOYMENT_MODE.value} mode. "
            f"Supported types: {supported}",
        )
    return True


async def save_uploaded_file(file: UploadFile) -> Path:
    """Save uploaded file to storage directory."""
    # Generate unique filename
    ext = Path(file.filename or "file").suffix
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / unique_name

    # Save file
    content = await file.read()
    file_path.write_bytes(content)

    return file_path


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(""),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    location: Optional[str] = Form(None),
    hazard_type: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Upload and process a document.

    In cloud mode:
    - Basic text extraction for PDFs, TXT, MD files
    - Unsupported formats are queued for local processing

    In local mode:
    - Full Docling processing with OCR and Office conversion
    - Structured section extraction
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Validate file size
    validate_file_size(file)

    # Use filename as title if not provided
    doc_title = title or Path(file.filename).stem

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Save the uploaded file
    file_path = await save_uploaded_file(file)
    logger.info(f"Saved uploaded file to {file_path}")

    try:
        # Process the document
        result = await document_processor.process(file_path)

        # Determine processing status
        if result.success:
            if result.needs_full_processing:
                proc_status = ProcessingStatus.NEEDS_LOCAL.value
                message = (
                    "Document uploaded. Basic processing complete, "
                    "full processing will occur during sync."
                )
            else:
                proc_status = ProcessingStatus.COMPLETED.value
                message = "Document uploaded and fully processed."
        else:
            proc_status = ProcessingStatus.FAILED.value
            message = f"Document upload failed: {result.error}"

        # Create document record
        document = Document(
            title=doc_title,
            description=description or result.content[:500] if result.content else "",
            tags=tag_list,
            location=location,
            hazard_type=hazard_type,
            source=source,
            needs_full_processing=result.needs_full_processing,
            processing_mode=result.processing_mode,
            processing_status=proc_status,
            processed_at=result.processed_at if result.success else None,
            raw_file_path=str(file_path) if result.needs_full_processing else None,
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)

        logger.info(
            f"Created document {document.id}: mode={result.processing_mode}, "
            f"needs_full={result.needs_full_processing}"
        )

        # Trigger KG extraction in background if document was processed successfully
        if result.success and result.content:
            background_tasks.add_task(
                _extract_kg_background,
                document_id=document.id,
                content=result.content,
                metadata={
                    "title": doc_title,
                    "tags": tag_list,
                    "hazard_type": hazard_type,
                    "location": location,
                    "source": source,
                },
            )

        return DocumentUploadResponse.model_validate(
            {
                "id": document.id,
                "title": document.title,
                "processing_mode": result.processing_mode,
                "processing_status": proc_status,
                "needs_full_processing": result.needs_full_processing,
                "message": message,
            }
        )

    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        logger.exception(f"Error processing document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}",
        )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    """Get the processing status of a document."""
    from sqlalchemy import select

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return DocumentStatusResponse.model_validate(document)


@router.get("/processing/stats")
async def get_processing_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get document processing statistics."""
    from models.document_queries import get_document_processing_stats

    stats = await get_document_processing_stats(db)
    stats["deployment_mode"] = DeploymentConfig.DEPLOYMENT_MODE.value
    stats["capabilities"] = document_processor.get_capabilities()

    return stats
