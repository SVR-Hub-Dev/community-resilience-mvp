"""
Docling document processor for local deployment.

Provides full document processing capabilities including:
- PDF text extraction with OCR fallback
- Office document conversion (DOCX, PPTX, XLSX)
- Structured section extraction
- Rich metadata extraction
"""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Represents a document section."""

    title: str
    level: int
    content: str
    page_numbers: list[int] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """Result of full document processing."""

    success: bool
    content: str
    metadata: dict
    sections: list[Section]
    needs_full_processing: bool = False
    processing_mode: str = "local_full"
    error: Optional[str] = None


class DoclingProcessor:
    """
    Full document processor using Docling.

    Handles PDF, DOCX, PPTX, XLSX, and other formats with:
    - OCR for scanned documents
    - Table extraction
    - Section hierarchy detection
    - Rich metadata extraction
    """

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        ".pdf": InputFormat.PDF,
        ".docx": InputFormat.DOCX,
        ".doc": InputFormat.DOCX,  # Docling handles conversion
        ".pptx": InputFormat.PPTX,
        ".ppt": InputFormat.PPTX,
        ".xlsx": InputFormat.XLSX,
        ".xls": InputFormat.XLSX,
        ".html": InputFormat.HTML,
        ".htm": InputFormat.HTML,
        ".md": InputFormat.MD,
        ".asciidoc": InputFormat.ASCIIDOC,
    }

    def __init__(self, enable_ocr: bool = True, enable_tables: bool = True):
        """
        Initialize the Docling processor.

        Args:
            enable_ocr: Enable OCR for scanned documents.
            enable_tables: Enable table structure extraction.
        """
        self.enable_ocr = enable_ocr
        self.enable_tables = enable_tables
        self._converter: Optional[DocumentConverter] = None
        logger.info(
            f"DoclingProcessor initialized (OCR: {enable_ocr}, Tables: {enable_tables})"
        )

    @property
    def converter(self) -> DocumentConverter:
        """Lazy initialization of DocumentConverter."""
        if self._converter is None:
            self._converter = self._create_converter()
        return self._converter

    def _create_converter(self) -> DocumentConverter:
        """Create and configure the DocumentConverter."""
        # Configure PDF pipeline with OCR support
        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = self.enable_ocr
        pdf_options.do_table_structure = self.enable_tables

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        )

        return converter

    def can_process(self, file_path: str | Path) -> bool:
        """Check if this processor can handle the given file."""
        path = Path(file_path)
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def process(self, file_path: str | Path) -> ProcessingResult:
        """
        Process a document with full Docling capabilities.

        Args:
            file_path: Path to the document file.

        Returns:
            ProcessingResult with extracted content, metadata, and sections.
        """
        path = Path(file_path)

        if not path.exists():
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                sections=[],
                error=f"File not found: {file_path}",
            )

        if not self.can_process(path):
            return ProcessingResult(
                success=False,
                content="",
                metadata={},
                sections=[],
                error=f"Unsupported file format: {path.suffix}",
            )

        try:
            # Run conversion in thread pool to avoid blocking
            result = await asyncio.to_thread(self._convert_document, path)
            return result
        except Exception as e:
            logger.exception(f"Error processing document: {path}")
            return ProcessingResult(
                success=False,
                content="",
                metadata={"file_extension": path.suffix.lower()},
                sections=[],
                error=str(e),
            )

    def _convert_document(self, file_path: Path) -> ProcessingResult:
        """
        Synchronous document conversion using Docling.

        This runs in a thread pool via asyncio.to_thread().
        """
        logger.info(f"Processing document: {file_path.name}")

        # Convert document
        conversion_result = self.converter.convert(str(file_path))
        document = conversion_result.document

        # Extract content
        content = self._extract_content(document)

        # Extract metadata
        metadata = self._extract_metadata(document, file_path, content)

        # Extract sections
        sections = self._extract_sections(document)

        logger.info(
            f"Processed {file_path.name}: "
            f"{metadata.get('word_count', 0)} words, "
            f"{len(sections)} sections"
        )

        return ProcessingResult(
            success=True,
            content=content,
            metadata=metadata,
            sections=sections,
            needs_full_processing=False,
            processing_mode="local_full",
        )

    def _extract_content(self, document) -> str:
        """Extract full text content from document."""
        try:
            # Try markdown export first for better formatting
            content = document.export_to_markdown()
        except Exception:
            try:
                # Fall back to plain text
                content = document.export_to_text()
            except Exception as e:
                logger.warning(f"Content extraction fallback failed: {e}")
                content = ""

        return content

    def _extract_metadata(self, document, file_path: Path, content: str) -> dict:
        """Extract document metadata."""
        metadata = {
            "filename": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size": file_path.stat().st_size,
            "word_count": len(content.split()) if content else 0,
            "character_count": len(content) if content else 0,
            "processing_mode": "local_full",
        }

        # Try to extract document-level metadata
        try:
            if hasattr(document, "title") and document.title:
                metadata["title"] = document.title
            else:
                metadata["title"] = file_path.stem

            if hasattr(document, "author") and document.author:
                metadata["author"] = document.author

            if hasattr(document, "creation_date") and document.creation_date:
                metadata["creation_date"] = str(document.creation_date)

            if hasattr(document, "pages"):
                metadata["page_count"] = len(document.pages)

        except Exception as e:
            logger.debug(f"Could not extract some metadata: {e}")

        # Extract table information if available
        try:
            if hasattr(document, "tables"):
                metadata["table_count"] = len(document.tables)
        except Exception:
            pass

        # Extract image information if available
        try:
            if hasattr(document, "pictures"):
                metadata["image_count"] = len(document.pictures)
        except Exception:
            pass

        return metadata

    def _extract_sections(self, document) -> list[Section]:
        """Extract document sections with hierarchy."""
        sections = []

        try:
            # Try to extract sections from document structure
            if hasattr(document, "texts"):
                current_section = None
                current_content = []

                for item in document.texts:
                    # Check if this is a heading
                    if hasattr(item, "label") and "heading" in str(item.label).lower():
                        # Save previous section
                        if current_section is not None:
                            current_section.content = "\n".join(current_content).strip()
                            if current_section.content or current_section.title:
                                sections.append(current_section)

                        # Determine heading level
                        level = self._get_heading_level(item)

                        # Start new section
                        current_section = Section(
                            title=item.text if hasattr(item, "text") else "",
                            level=level,
                            content="",
                            page_numbers=self._get_page_numbers(item),
                        )
                        current_content = []
                    else:
                        # Add to current section content
                        if hasattr(item, "text"):
                            current_content.append(item.text)

                # Don't forget the last section
                if current_section is not None:
                    current_section.content = "\n".join(current_content).strip()
                    if current_section.content or current_section.title:
                        sections.append(current_section)

        except Exception as e:
            logger.debug(f"Section extraction failed: {e}")
            # Return empty sections list - content is still available

        return sections

    def _get_heading_level(self, item) -> int:
        """Determine heading level from item properties."""
        try:
            label = str(item.label).lower() if hasattr(item, "label") else ""

            # Try to extract level from label (e.g., "heading_1", "h2")
            for i in range(1, 7):
                if f"_{i}" in label or f"h{i}" in label or f"level{i}" in label:
                    return i

            # Default to level 1 for unspecified headings
            return 1
        except Exception:
            return 1

    def _get_page_numbers(self, item) -> list[int]:
        """Extract page numbers from item if available."""
        try:
            if hasattr(item, "prov") and item.prov:
                pages = set()
                for prov in item.prov:
                    if hasattr(prov, "page_no"):
                        pages.add(prov.page_no)
                return sorted(pages)
        except Exception:
            pass
        return []


# Singleton instance for easy import
docling_processor = DoclingProcessor()
