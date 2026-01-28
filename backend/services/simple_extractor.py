"""
Simple text extractor for cloud deployment.

Extracts text from PDFs (using PyMuPDF), plain text, and markdown files.
Returns needs_full_processing=True for formats requiring Docling (OCR, Office docs).
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# File extensions that can be processed with simple extraction
SIMPLE_TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".text"}
SIMPLE_PDF_EXTENSIONS = {".pdf"}

# Extensions that require full Docling processing
FULL_PROCESSING_EXTENSIONS = {
    ".doc",
    ".docx",  # Word documents
    ".xls",
    ".xlsx",  # Excel spreadsheets
    ".ppt",
    ".pptx",  # PowerPoint presentations
    ".odt",
    ".ods",
    ".odp",  # OpenDocument formats
    ".rtf",  # Rich Text Format
    ".html",
    ".htm",  # HTML (for complex extraction)
}


@dataclass
class ExtractionResult:
    """Result of document text extraction."""

    text: str
    needs_full_processing: bool
    processing_mode: str
    metadata: dict
    error: Optional[str] = None


class SimpleTextExtractor:
    """
    Simple text extractor for cloud deployment.

    Handles basic text extraction without heavy dependencies like Docling.
    For formats requiring OCR or Office conversion, marks them for full processing.
    """

    def __init__(self):
        self.supported_extensions = SIMPLE_TEXT_EXTENSIONS | SIMPLE_PDF_EXTENSIONS

    def can_process(self, file_path: str | Path) -> bool:
        """Check if this extractor can process the given file."""
        path = Path(file_path)
        return path.suffix.lower() in self.supported_extensions

    def extract(self, file_path: str | Path) -> ExtractionResult:
        """
        Extract text from a document.

        Args:
            file_path: Path to the document file.

        Returns:
            ExtractionResult with extracted text and processing metadata.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if not path.exists():
            return ExtractionResult(
                text="",
                needs_full_processing=False,
                processing_mode="error",
                metadata={},
                error=f"File not found: {file_path}",
            )

        try:
            if suffix in SIMPLE_TEXT_EXTENSIONS:
                return self._extract_text_file(path)
            elif suffix in SIMPLE_PDF_EXTENSIONS:
                return self._extract_pdf(path)
            elif suffix in FULL_PROCESSING_EXTENSIONS:
                return self._mark_for_full_processing(path, suffix)
            else:
                return ExtractionResult(
                    text="",
                    needs_full_processing=True,
                    processing_mode="unsupported",
                    metadata={"file_extension": suffix},
                    error=f"Unsupported file format: {suffix}",
                )
        except Exception as e:
            logger.exception(f"Error extracting text from {file_path}")
            return ExtractionResult(
                text="",
                needs_full_processing=True,
                processing_mode="error",
                metadata={"file_extension": suffix},
                error=str(e),
            )

    def _extract_text_file(self, path: Path) -> ExtractionResult:
        """Extract text from plain text or markdown files."""
        # Try common encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

        for encoding in encodings:
            try:
                text = path.read_text(encoding=encoding)
                return ExtractionResult(
                    text=text,
                    needs_full_processing=False,
                    processing_mode="simple_text",
                    metadata={
                        "file_extension": path.suffix.lower(),
                        "encoding": encoding,
                        "file_size": path.stat().st_size,
                        "character_count": len(text),
                    },
                )
            except UnicodeDecodeError:
                continue

        return ExtractionResult(
            text="",
            needs_full_processing=True,
            processing_mode="encoding_error",
            metadata={"file_extension": path.suffix.lower()},
            error="Could not decode file with any common encoding",
        )

    def _extract_pdf(self, path: Path) -> ExtractionResult:
        """
        Extract text from PDF using PyMuPDF.

        If the PDF has minimal extractable text (likely scanned/image-based),
        marks it for full OCR processing.
        """
        try:
            doc = fitz.open(path)
            text_parts = []
            total_pages = len(doc)
            pages_with_text = 0

            for page in doc:
                page_text = page.get_text()
                if isinstance(page_text, str):
                    if page_text.strip():
                        pages_with_text += 1
                    text_parts.append(page_text)
                else:
                    # If not a string, skip counting and joining, but append string representation for debugging
                    text_parts.append(str(page_text))

            doc.close()

            full_text = "\n\n".join(text_parts)

            # Heuristic: if less than 10% of pages have text, likely needs OCR
            text_coverage = pages_with_text / total_pages if total_pages > 0 else 0
            needs_ocr = text_coverage < 0.1 or len(full_text.strip()) < 100

            if needs_ocr:
                return ExtractionResult(
                    text=full_text,
                    needs_full_processing=True,
                    processing_mode="pdf_needs_ocr",
                    metadata={
                        "file_extension": ".pdf",
                        "page_count": total_pages,
                        "pages_with_text": pages_with_text,
                        "text_coverage": text_coverage,
                        "file_size": path.stat().st_size,
                    },
                )

            return ExtractionResult(
                text=full_text,
                needs_full_processing=False,
                processing_mode="pdf_text",
                metadata={
                    "file_extension": ".pdf",
                    "page_count": total_pages,
                    "pages_with_text": pages_with_text,
                    "text_coverage": text_coverage,
                    "character_count": len(full_text),
                    "file_size": path.stat().st_size,
                },
            )

        except Exception as e:
            logger.exception(f"Error extracting PDF: {path}")
            return ExtractionResult(
                text="",
                needs_full_processing=True,
                processing_mode="pdf_error",
                metadata={"file_extension": ".pdf"},
                error=str(e),
            )

    def _mark_for_full_processing(self, path: Path, suffix: str) -> ExtractionResult:
        """Mark a file as requiring full Docling processing."""
        return ExtractionResult(
            text="",
            needs_full_processing=True,
            processing_mode="pending_full_processing",
            metadata={
                "file_extension": suffix,
                "file_size": path.stat().st_size,
                "reason": f"Format {suffix} requires Docling for proper extraction",
            },
        )


# Singleton instance for easy import
simple_extractor = SimpleTextExtractor()
