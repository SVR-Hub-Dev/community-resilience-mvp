"""Unit tests for DocumentProcessor factory."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.simple_extractor import SimpleTextExtractor, ExtractionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_extraction_result(**overrides):
    """Create an ExtractionResult with sensible defaults."""
    defaults = {
        "text": "Extracted content",
        "needs_full_processing": False,
        "processing_mode": "simple_text",
        "metadata": {"file_extension": ".txt"},
        "error": None,
    }
    defaults.update(overrides)
    return ExtractionResult(**defaults)


# ---------------------------------------------------------------------------
# Factory mode selection tests
# ---------------------------------------------------------------------------


class TestDocumentProcessorModeSelection:

    @patch("services.document_processor.DeploymentConfig")
    def test_cloud_mode_loads_simple_extractor(self, mock_config):
        """In cloud mode, the factory should load SimpleTextExtractor."""
        from config import DeploymentMode

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        from services.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        processor._initialize()

        assert isinstance(processor._processor, SimpleTextExtractor)

    @patch("services.document_processor.DeploymentConfig")
    def test_local_mode_without_docling_falls_back(self, mock_config):
        """In local mode with docling unavailable, fall back to SimpleTextExtractor."""
        from config import DeploymentMode

        mock_config.DEPLOYMENT_MODE = DeploymentMode.LOCAL
        mock_config.DOCLING_ENABLED = True
        mock_config.FULL_OCR_ENABLED = True

        from services.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.LOCAL
        processor._initialized = False
        processor._processor = None

        # Simulate docling import failure
        with patch.object(
            processor, "_load_docling_processor", return_value=None
        ):
            processor._initialize()

        assert isinstance(processor._processor, SimpleTextExtractor)

    @patch("services.document_processor.DeploymentConfig")
    def test_local_mode_with_docling(self, mock_config):
        """In local mode with docling available, load DoclingProcessor."""
        from config import DeploymentMode

        mock_config.DEPLOYMENT_MODE = DeploymentMode.LOCAL
        mock_config.DOCLING_ENABLED = True
        mock_config.FULL_OCR_ENABLED = True

        from services.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.LOCAL
        processor._initialized = False
        processor._processor = None

        fake_docling = MagicMock()
        fake_docling.__class__.__name__ = "DoclingProcessor"

        with patch.object(
            processor, "_load_docling_processor", return_value=fake_docling
        ):
            processor._initialize()

        assert processor._processor is fake_docling

    @patch("services.document_processor.DeploymentConfig")
    def test_initialize_runs_only_once(self, mock_config):
        """_initialize() should only run once even if called multiple times."""
        from config import DeploymentMode

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        from services.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        with patch.object(
            processor, "_load_simple_extractor", wraps=processor._load_simple_extractor
        ) as mock_load:
            processor._initialize()
            processor._initialize()
            assert mock_load.call_count == 1


# ---------------------------------------------------------------------------
# process() delegation tests
# ---------------------------------------------------------------------------


class TestDocumentProcessorProcess:

    @patch("services.document_processor.DeploymentConfig")
    def test_process_delegates_to_simple_extractor(self, mock_config, tmp_path):
        """process() should call SimpleTextExtractor.extract() in cloud mode."""
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False
        mock_config.FULL_OCR_ENABLED = False
        mock_config.OFFICE_CONVERSION_ENABLED = False

        p = tmp_path / "test.txt"
        p.write_text("Hello world")

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        result = asyncio.get_event_loop().run_until_complete(processor.process(p))

        assert result.success is True
        assert "Hello world" in result.content
        assert result.processing_mode == "simple_text"

    @patch("services.document_processor.DeploymentConfig")
    def test_process_file_not_found(self, mock_config, tmp_path):
        """process() should return error for missing files."""
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        result = asyncio.get_event_loop().run_until_complete(
            processor.process(tmp_path / "nonexistent.pdf")
        )

        assert result.success is False
        assert "not found" in result.error.lower()
        assert result.processing_mode == "error"

    @patch("services.document_processor.DeploymentConfig")
    def test_process_handles_exception(self, mock_config, tmp_path):
        """process() should catch exceptions from the underlying processor."""
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        p = tmp_path / "bad.txt"
        p.write_text("content")

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        # Force an exception from the processor
        mock_extractor = MagicMock(spec=SimpleTextExtractor)
        mock_extractor.extract.side_effect = RuntimeError("extraction crash")
        # Fake that it's SimpleTextExtractor
        mock_extractor.__class__ = SimpleTextExtractor

        processor._processor = mock_extractor
        processor._initialized = True

        result = asyncio.get_event_loop().run_until_complete(processor.process(p))

        assert result.success is False
        assert "extraction crash" in result.error


# ---------------------------------------------------------------------------
# _to_processed_document conversion tests
# ---------------------------------------------------------------------------


class TestDocumentProcessorConversion:

    @patch("services.document_processor.DeploymentConfig")
    def test_converts_extraction_result(self, mock_config, tmp_path):
        """ExtractionResult (SimpleTextExtractor) should be converted correctly."""
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = True
        processor._processor = SimpleTextExtractor()

        extraction = _make_extraction_result(
            text="Sample text",
            needs_full_processing=False,
            processing_mode="simple_text",
            metadata={"file_extension": ".txt", "encoding": "utf-8"},
        )

        p = tmp_path / "doc.txt"
        now = datetime.now(timezone.utc)

        result = processor._to_processed_document(extraction, p, now)

        assert result.success is True
        assert result.content == "Sample text"
        assert result.needs_full_processing is False
        assert result.processing_mode == "simple_text"
        assert result.processed_at == now
        assert result.metadata["deployment_mode"] == "cloud"
        assert result.metadata["filename"] == "doc.txt"

    @patch("services.document_processor.DeploymentConfig")
    def test_converts_processing_result(self, mock_config, tmp_path):
        """ProcessingResult (DoclingProcessor) should be converted correctly."""
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.LOCAL
        mock_config.DOCLING_ENABLED = True

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.LOCAL
        processor._initialized = True
        processor._processor = MagicMock()
        processor._processor.__class__.__name__ = "DoclingProcessor"

        # Create a fake ProcessingResult (has .content, .success, .sections)
        fake_section = MagicMock()
        fake_section.title = "Heading"
        fake_section.level = 1
        fake_section.content = "Body"
        fake_section.page_numbers = [1]

        result_obj = MagicMock()
        result_obj.success = True
        result_obj.content = "Full document text"
        result_obj.metadata = {"word_count": 3}
        result_obj.sections = [fake_section]
        result_obj.needs_full_processing = False
        result_obj.processing_mode = "local_full"
        result_obj.error = None
        # Make hasattr checks work: .content exists but .text does not
        del result_obj.text

        p = tmp_path / "report.pdf"
        now = datetime.now(timezone.utc)

        result = processor._to_processed_document(result_obj, p, now)

        assert result.success is True
        assert result.content == "Full document text"
        assert len(result.sections) == 1
        assert result.sections[0].title == "Heading"
        assert result.processing_mode == "local_full"

    @patch("services.document_processor.DeploymentConfig")
    def test_unknown_result_type(self, mock_config, tmp_path):
        """Unknown result types should produce an error ProcessedDocument."""
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = True
        processor._processor = SimpleTextExtractor()

        # Object with neither .text nor .content
        unknown = MagicMock(spec=[])

        p = tmp_path / "weird.dat"
        now = datetime.now(timezone.utc)

        result = processor._to_processed_document(unknown, p, now)

        assert result.success is False
        assert "unknown" in result.processing_mode.lower()


# ---------------------------------------------------------------------------
# Properties and capabilities tests
# ---------------------------------------------------------------------------


class TestDocumentProcessorProperties:

    @patch("services.document_processor.DeploymentConfig")
    def test_processor_name_simple(self, mock_config):
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        assert processor.processor_name == "SimpleTextExtractor"

    @patch("services.document_processor.DeploymentConfig")
    def test_deployment_mode_property(self, mock_config):
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD

        assert processor.deployment_mode == DeploymentMode.CLOUD

    @patch("services.document_processor.DeploymentConfig")
    def test_can_process_delegates(self, mock_config, tmp_path):
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        assert processor.can_process(tmp_path / "file.txt") is True
        assert processor.can_process(tmp_path / "file.docx") is False

    @patch("services.document_processor.DeploymentConfig")
    def test_get_capabilities_cloud(self, mock_config):
        from config import DeploymentMode
        from services.document_processor import DocumentProcessor

        mock_config.DEPLOYMENT_MODE = DeploymentMode.CLOUD
        mock_config.DOCLING_ENABLED = False
        mock_config.FULL_OCR_ENABLED = False
        mock_config.OFFICE_CONVERSION_ENABLED = False
        mock_config.MAX_UPLOAD_SIZE_MB = 10
        mock_config.PROCESS_TIMEOUT_SECONDS = 30

        processor = DocumentProcessor()
        processor._mode = DeploymentMode.CLOUD
        processor._initialized = False
        processor._processor = None

        caps = processor.get_capabilities()

        assert caps["deployment_mode"] == "cloud"
        assert caps["processor"] == "SimpleTextExtractor"
        assert caps["capabilities"]["pdf_text_extraction"] is True
        assert caps["capabilities"]["pdf_ocr"] is False
        assert caps["capabilities"]["office_documents"] is False
        assert caps["max_file_size_mb"] == 10
