"""
Document processor factory for hybrid deployment.

Automatically selects the appropriate document processor based on:
- DEPLOYMENT_MODE environment variable
- Available dependencies (Docling may not be installed in cloud)

Cloud mode: Uses SimpleTextExtractor (lightweight, PyMuPDF only)
Local mode: Uses DoclingProcessor (full OCR, Office conversion, structure extraction)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol, Union

from config import DeploymentConfig, DeploymentMode

if TYPE_CHECKING:
    from services.docling_service import DoclingProcessor
    from services.simple_extractor import SimpleTextExtractor

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Represents a document section."""

    title: str
    level: int
    content: str
    page_numbers: list[int] = field(default_factory=list)


@dataclass
class ProcessedDocument:
    """Unified result from document processing."""

    success: bool
    content: str
    metadata: dict
    sections: list[Section]
    needs_full_processing: bool
    processing_mode: str
    processed_at: datetime
    error: Optional[str] = None


class DocumentProcessorProtocol(Protocol):
    """Protocol defining the document processor interface."""

    def can_process(self, file_path: Union[str, Path]) -> bool:
        """Check if the processor can handle the given file."""
        ...


# Type alias for processor union - use strings for forward references
ProcessorType = Optional[Union["SimpleTextExtractor", "DoclingProcessor"]]


class DocumentProcessor:
    """
    Factory that provides the appropriate document processor based on deployment mode.

    Usage:
        processor = DocumentProcessor()
        result = await processor.process("/path/to/document.pdf")
    """

    def __init__(self):
        self._processor: ProcessorType = None
        self._mode = DeploymentConfig.DEPLOYMENT_MODE
        self._initialized = False
        logger.info(f"DocumentProcessor created for mode: {self._mode.value}")

    def _initialize(self) -> None:
        """Lazy initialization of the underlying processor."""
        if self._initialized:
            return

        if self._mode == DeploymentMode.LOCAL and DeploymentConfig.DOCLING_ENABLED:
            self._processor = self._load_docling_processor()

        if self._processor is None:
            # Fall back to simple extractor (always available)
            self._processor = self._load_simple_extractor()

        self._initialized = True

    def _load_docling_processor(self) -> Optional["DoclingProcessor"]:
        """Attempt to load the Docling processor."""
        try:
            from services.docling_service import DoclingProcessor

            processor = DoclingProcessor(
                enable_ocr=DeploymentConfig.FULL_OCR_ENABLED, enable_tables=True
            )
            logger.info("Loaded DoclingProcessor for local processing")
            return processor
        except ImportError as e:
            logger.warning(
                f"Docling not available, falling back to simple extractor: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to initialize DoclingProcessor: {e}")
            return None

    def _load_simple_extractor(self) -> "SimpleTextExtractor":
        """Load the simple text extractor."""
        from services.simple_extractor import SimpleTextExtractor

        processor = SimpleTextExtractor()
        logger.info("Loaded SimpleTextExtractor for cloud/fallback processing")
        return processor

    @property
    def processor(self) -> Union["SimpleTextExtractor", "DoclingProcessor"]:
        """Get the underlying processor, initializing if needed."""
        self._initialize()
        if self._processor is None:
            raise RuntimeError("Failed to initialize any document processor")
        return self._processor

    @property
    def deployment_mode(self) -> DeploymentMode:
        """Get the current deployment mode."""
        return self._mode

    @property
    def processor_name(self) -> str:
        """Get the name of the active processor."""
        self._initialize()
        if self._processor is None:
            return "None"
        return type(self._processor).__name__

    def can_process(self, file_path: Union[str, Path]) -> bool:
        """Check if the current processor can handle the given file."""
        return self.processor.can_process(file_path)

    async def process(self, file_path: Union[str, Path]) -> ProcessedDocument:
        """
        Process a document using the appropriate processor.

        Args:
            file_path: Path to the document file.

        Returns:
            ProcessedDocument with unified result format.
        """
        path = Path(file_path)
        processed_at = datetime.now(timezone.utc)

        if not path.exists():
            return ProcessedDocument(
                success=False,
                content="",
                metadata={"filename": path.name},
                sections=[],
                needs_full_processing=False,
                processing_mode="error",
                processed_at=processed_at,
                error=f"File not found: {file_path}",
            )

        try:
            # Get the appropriate processor
            proc = self.processor

            # Check processor type and call appropriate method
            # DoclingProcessor has async process(), SimpleTextExtractor has sync extract()
            proc_name = type(proc).__name__

            if proc_name == "DoclingProcessor":
                # DoclingProcessor.process() is async
                result = await proc.process(path)  # type: ignore
            else:
                # SimpleTextExtractor.extract() is sync
                result = proc.extract(path)  # type: ignore

            # Convert to unified ProcessedDocument format
            return self._to_processed_document(result, path, processed_at)

        except Exception as e:
            logger.exception(f"Error processing document: {path}")
            return ProcessedDocument(
                success=False,
                content="",
                metadata={
                    "filename": path.name,
                    "file_extension": path.suffix.lower(),
                },
                sections=[],
                needs_full_processing=True,
                processing_mode="error",
                processed_at=processed_at,
                error=str(e),
            )

    def _to_processed_document(
        self, result, path: Path, processed_at: datetime
    ) -> ProcessedDocument:
        """Convert processor-specific result to unified ProcessedDocument."""
        # Handle SimpleTextExtractor's ExtractionResult
        if hasattr(result, "text"):
            return ProcessedDocument(
                success=result.error is None,
                content=result.text,
                metadata=self._enrich_metadata(result.metadata, path),
                sections=[],  # Simple extractor doesn't extract sections
                needs_full_processing=result.needs_full_processing,
                processing_mode=result.processing_mode,
                processed_at=processed_at,
                error=result.error,
            )

        # Handle DoclingProcessor's ProcessingResult
        if hasattr(result, "content"):
            sections = [
                Section(
                    title=s.title,
                    level=s.level,
                    content=s.content,
                    page_numbers=s.page_numbers,
                )
                for s in (result.sections or [])
            ]

            return ProcessedDocument(
                success=result.success,
                content=result.content,
                metadata=self._enrich_metadata(result.metadata, path),
                sections=sections,
                needs_full_processing=result.needs_full_processing,
                processing_mode=result.processing_mode,
                processed_at=processed_at,
                error=result.error,
            )

        # Unknown result type
        logger.warning(f"Unknown result type: {type(result)}")
        return ProcessedDocument(
            success=False,
            content="",
            metadata={"filename": path.name},
            sections=[],
            needs_full_processing=True,
            processing_mode="unknown",
            processed_at=processed_at,
            error="Unknown processor result type",
        )

    def _enrich_metadata(self, metadata: dict, path: Path) -> dict:
        """Add processing metadata to the result."""
        enriched = dict(metadata)
        enriched.update(
            {
                "processor": self.processor_name,
                "deployment_mode": self._mode.value,
                "filename": path.name,
            }
        )
        return enriched

    def get_capabilities(self) -> dict:
        """Get the capabilities of the current processor configuration."""
        self._initialize()

        is_docling = "Docling" in self.processor_name

        return {
            "deployment_mode": self._mode.value,
            "processor": self.processor_name,
            "capabilities": {
                "pdf_text_extraction": True,
                "pdf_ocr": is_docling and DeploymentConfig.FULL_OCR_ENABLED,
                "office_documents": is_docling
                and DeploymentConfig.OFFICE_CONVERSION_ENABLED,
                "structured_sections": is_docling,
                "table_extraction": is_docling,
            },
            "supported_formats": self._get_supported_formats(),
            "max_file_size_mb": DeploymentConfig.MAX_UPLOAD_SIZE_MB,
            "process_timeout_seconds": DeploymentConfig.PROCESS_TIMEOUT_SECONDS,
        }

    def _get_supported_formats(self) -> list[str]:
        """Get list of supported file formats."""
        if "Docling" in self.processor_name:
            return [
                ".pdf",
                ".docx",
                ".doc",
                ".pptx",
                ".ppt",
                ".xlsx",
                ".xls",
                ".html",
                ".htm",
                ".md",
                ".txt",
                ".markdown",
                ".asciidoc",
            ]
        else:
            return [".pdf", ".txt", ".md", ".markdown", ".text"]


# Singleton instance for easy import
document_processor = DocumentProcessor()


async def process_document(file_path: Union[str, Path]) -> ProcessedDocument:
    """
    Convenience function to process a document.

    Args:
        file_path: Path to the document file.

    Returns:
        ProcessedDocument with processing results.
    """
    return await document_processor.process(file_path)
