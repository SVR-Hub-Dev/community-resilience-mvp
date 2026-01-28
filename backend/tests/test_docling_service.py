"""Unit tests for DoclingProcessor.

Since Docling may not be installed in the test environment (cloud mode),
these tests mock the docling library imports and test the processor logic.
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers – lightweight stand-ins for Docling types so we can import the
# module under test even when the real `docling` package is absent.
# ---------------------------------------------------------------------------


class _FakeInputFormat:
    PDF = "PDF"
    DOCX = "DOCX"
    PPTX = "PPTX"
    XLSX = "XLSX"
    HTML = "HTML"
    MD = "MD"
    ASCIIDOC = "ASCIIDOC"


class _FakePdfPipelineOptions:
    def __init__(self):
        self.do_ocr = True
        self.do_table_structure = True


class _FakePdfFormatOption:
    def __init__(self, pipeline_options=None):
        self.pipeline_options = pipeline_options


class _FakeDocumentConverter:
    def __init__(self, format_options=None):
        self.format_options = format_options

    def convert(self, path):
        raise NotImplementedError("Test must mock this")


# Patch docling modules before importing the module under test
_docling_mocks = {
    "docling": MagicMock(),
    "docling.document_converter": MagicMock(
        DocumentConverter=_FakeDocumentConverter,
        PdfFormatOption=_FakePdfFormatOption,
    ),
    "docling.datamodel": MagicMock(),
    "docling.datamodel.base_models": MagicMock(InputFormat=_FakeInputFormat),
    "docling.datamodel.pipeline_options": MagicMock(
        PdfPipelineOptions=_FakePdfPipelineOptions,
    ),
}


@pytest.fixture(autouse=True)
def _patch_docling(monkeypatch):
    """Ensure docling modules are available as mocks for every test."""
    import sys

    for mod_name, mock_mod in _docling_mocks.items():
        monkeypatch.setitem(sys.modules, mod_name, mock_mod)


def _import_docling_service():
    """Import the module after docling mocks are in place."""
    import importlib
    import services.docling_service as mod

    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def docling_mod():
    return _import_docling_service()


@pytest.fixture
def processor(docling_mod):
    return docling_mod.DoclingProcessor(enable_ocr=True, enable_tables=True)


# ---------------------------------------------------------------------------
# can_process tests
# ---------------------------------------------------------------------------


class TestDoclingProcessorCanProcess:

    def test_can_process_pdf(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "file.pdf") is True

    def test_can_process_docx(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "file.docx") is True

    def test_can_process_pptx(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "file.pptx") is True

    def test_can_process_xlsx(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "file.xlsx") is True

    def test_can_process_html(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "file.html") is True

    def test_can_process_md(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "file.md") is True

    def test_cannot_process_unknown(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "file.xyz") is False

    def test_cannot_process_image(self, processor, tmp_path):
        assert processor.can_process(tmp_path / "photo.jpg") is False


# ---------------------------------------------------------------------------
# process() tests
# ---------------------------------------------------------------------------


class TestDoclingProcessorProcess:

    def test_file_not_found(self, processor, tmp_path):
        result = asyncio.get_event_loop().run_until_complete(
            processor.process(tmp_path / "missing.pdf")
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_unsupported_format(self, processor, tmp_path):
        p = tmp_path / "file.xyz"
        p.write_text("content")
        result = asyncio.get_event_loop().run_until_complete(
            processor.process(p)
        )
        assert result.success is False
        assert "unsupported" in result.error.lower()

    def test_successful_processing(self, processor, docling_mod, tmp_path):
        """Test that process() delegates to _convert_document and returns success."""
        p = tmp_path / "report.pdf"
        p.write_bytes(b"%PDF-1.4 fake")

        fake_result = docling_mod.ProcessingResult(
            success=True,
            content="Extracted text",
            metadata={"word_count": 2},
            sections=[],
            needs_full_processing=False,
            processing_mode="local_full",
        )

        with patch.object(processor, "_convert_document", return_value=fake_result):
            result = asyncio.get_event_loop().run_until_complete(
                processor.process(p)
            )

        assert result.success is True
        assert result.content == "Extracted text"
        assert result.processing_mode == "local_full"

    def test_processing_exception(self, processor, tmp_path):
        """Test that process() handles converter exceptions gracefully."""
        p = tmp_path / "bad.pdf"
        p.write_bytes(b"%PDF-1.4 broken")

        with patch.object(
            processor, "_convert_document", side_effect=RuntimeError("converter crash")
        ):
            result = asyncio.get_event_loop().run_until_complete(
                processor.process(p)
            )

        assert result.success is False
        assert "converter crash" in result.error


# ---------------------------------------------------------------------------
# _convert_document tests
# ---------------------------------------------------------------------------


class TestDoclingProcessorConvertDocument:

    def _make_fake_document(
        self,
        markdown_content: str = "# Title\nBody text",
        title: str = "Doc Title",
        author: str = "",
        pages: int = 1,
        tables: int = 0,
        pictures: int = 0,
        texts: list | None = None,
    ):
        """Create a mock Docling document object."""
        doc = MagicMock()
        doc.export_to_markdown.return_value = markdown_content
        doc.export_to_text.return_value = markdown_content
        doc.title = title
        doc.author = author
        doc.creation_date = None
        doc.pages = [MagicMock()] * pages
        doc.tables = [MagicMock()] * tables
        doc.pictures = [MagicMock()] * pictures
        doc.texts = texts or []
        return doc

    def test_convert_document_success(self, processor, docling_mod, tmp_path):
        p = tmp_path / "test.pdf"
        p.write_bytes(b"%PDF-1.4 test")

        fake_doc = self._make_fake_document(
            markdown_content="Hello world content",
            title="Test Doc",
            pages=3,
            tables=1,
            pictures=2,
        )

        fake_conversion = MagicMock()
        fake_conversion.document = fake_doc

        # Mock the converter property
        mock_converter = MagicMock()
        mock_converter.convert.return_value = fake_conversion

        with patch.object(
            type(processor), "converter", new_callable=PropertyMock, return_value=mock_converter
        ):
            result = processor._convert_document(p)

        assert result.success is True
        assert result.content == "Hello world content"
        assert result.metadata["filename"] == "test.pdf"
        assert result.metadata["file_extension"] == ".pdf"
        assert result.metadata["word_count"] == 3
        assert result.metadata["page_count"] == 3
        assert result.metadata["table_count"] == 1
        assert result.metadata["image_count"] == 2
        assert result.processing_mode == "local_full"

    def test_markdown_export_fallback_to_text(self, processor, docling_mod, tmp_path):
        """If markdown export fails, fall back to plain text export."""
        p = tmp_path / "test.docx"
        p.write_bytes(b"fake docx")

        fake_doc = self._make_fake_document()
        fake_doc.export_to_markdown.side_effect = Exception("no markdown")
        fake_doc.export_to_text.return_value = "Plain text content"

        fake_conversion = MagicMock()
        fake_conversion.document = fake_doc

        mock_converter = MagicMock()
        mock_converter.convert.return_value = fake_conversion

        with patch.object(
            type(processor), "converter", new_callable=PropertyMock, return_value=mock_converter
        ):
            result = processor._convert_document(p)

        assert result.success is True
        assert result.content == "Plain text content"

    def test_section_extraction(self, processor, docling_mod, tmp_path):
        """Test that sections are extracted from document structure."""
        p = tmp_path / "doc.pdf"
        p.write_bytes(b"%PDF-1.4")

        # Create fake text items with headings
        heading_item = MagicMock()
        heading_item.label = "heading_1"
        heading_item.text = "Section Title"
        heading_item.prov = []

        body_item = MagicMock()
        body_item.label = "paragraph"
        body_item.text = "Section body text."
        body_item.prov = []

        fake_doc = self._make_fake_document(texts=[heading_item, body_item])
        fake_conversion = MagicMock()
        fake_conversion.document = fake_doc

        mock_converter = MagicMock()
        mock_converter.convert.return_value = fake_conversion

        with patch.object(
            type(processor), "converter", new_callable=PropertyMock, return_value=mock_converter
        ):
            result = processor._convert_document(p)

        assert result.success is True
        assert len(result.sections) == 1
        assert result.sections[0].title == "Section Title"
        assert result.sections[0].content == "Section body text."
        assert result.sections[0].level == 1


# ---------------------------------------------------------------------------
# Heading level detection tests
# ---------------------------------------------------------------------------


class TestDoclingProcessorHeadingLevel:

    def test_heading_1(self, processor):
        item = MagicMock()
        item.label = "heading_1"
        assert processor._get_heading_level(item) == 1

    def test_heading_2(self, processor):
        item = MagicMock()
        item.label = "heading_2"
        assert processor._get_heading_level(item) == 2

    def test_h3_format(self, processor):
        item = MagicMock()
        item.label = "h3"
        assert processor._get_heading_level(item) == 3

    def test_unknown_heading_defaults_to_1(self, processor):
        item = MagicMock()
        item.label = "heading"
        assert processor._get_heading_level(item) == 1


# ---------------------------------------------------------------------------
# Page number extraction tests
# ---------------------------------------------------------------------------


class TestDoclingProcessorPageNumbers:

    def test_with_prov_info(self, processor):
        prov_item = MagicMock()
        prov_item.page_no = 3

        item = MagicMock()
        item.prov = [prov_item]

        assert processor._get_page_numbers(item) == [3]

    def test_multiple_pages(self, processor):
        prov1 = MagicMock()
        prov1.page_no = 1
        prov2 = MagicMock()
        prov2.page_no = 3
        prov3 = MagicMock()
        prov3.page_no = 1  # duplicate

        item = MagicMock()
        item.prov = [prov1, prov2, prov3]

        assert processor._get_page_numbers(item) == [1, 3]

    def test_no_prov(self, processor):
        item = MagicMock()
        item.prov = None

        assert processor._get_page_numbers(item) == []

    def test_no_prov_attr(self, processor):
        item = MagicMock(spec=[])  # no attributes
        assert processor._get_page_numbers(item) == []


# ---------------------------------------------------------------------------
# Lazy converter initialization
# ---------------------------------------------------------------------------


class TestDoclingProcessorConverterInit:

    def test_converter_lazy_init(self, processor):
        """Converter should not be created until first access."""
        assert processor._converter is None

    def test_converter_created_on_access(self, processor, docling_mod):
        """Accessing .converter triggers _create_converter."""
        with patch.object(processor, "_create_converter", return_value=MagicMock()) as mock_create:
            _ = processor.converter
            mock_create.assert_called_once()

    def test_converter_cached(self, processor, docling_mod):
        """Second access should reuse the same converter instance."""
        fake_conv = MagicMock()
        with patch.object(processor, "_create_converter", return_value=fake_conv):
            first = processor.converter
            second = processor.converter
        assert first is second
