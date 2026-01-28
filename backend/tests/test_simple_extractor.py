"""Unit tests for SimpleTextExtractor."""

from pathlib import Path

import pytest

from services.simple_extractor import SimpleTextExtractor, ExtractionResult


class TestSimpleTextExtractorCanProcess:
    """Tests for can_process() method."""

    def setup_method(self):
        self.extractor = SimpleTextExtractor()

    def test_can_process_txt(self, tmp_dir: Path):
        assert self.extractor.can_process(tmp_dir / "file.txt") is True

    def test_can_process_md(self, tmp_dir: Path):
        assert self.extractor.can_process(tmp_dir / "file.md") is True

    def test_can_process_markdown(self, tmp_dir: Path):
        assert self.extractor.can_process(tmp_dir / "file.markdown") is True

    def test_can_process_pdf(self, tmp_dir: Path):
        assert self.extractor.can_process(tmp_dir / "file.pdf") is True

    def test_cannot_process_docx(self, tmp_dir: Path):
        assert self.extractor.can_process(tmp_dir / "file.docx") is False

    def test_cannot_process_pptx(self, tmp_dir: Path):
        assert self.extractor.can_process(tmp_dir / "file.pptx") is False

    def test_cannot_process_unknown(self, tmp_dir: Path):
        assert self.extractor.can_process(tmp_dir / "file.xyz") is False


class TestSimpleTextExtractorTextFiles:
    """Tests for text file extraction."""

    def setup_method(self):
        self.extractor = SimpleTextExtractor()

    def test_extract_txt(self, sample_txt_file: Path):
        result = self.extractor.extract(sample_txt_file)
        assert result.error is None
        assert result.needs_full_processing is False
        assert result.processing_mode == "simple_text"
        assert "sample text document" in result.text

    def test_extract_md(self, sample_md_file: Path):
        result = self.extractor.extract(sample_md_file)
        assert result.error is None
        assert result.needs_full_processing is False
        assert result.processing_mode == "simple_text"
        assert "# Heading" in result.text

    def test_extract_txt_metadata(self, sample_txt_file: Path):
        result = self.extractor.extract(sample_txt_file)
        assert result.metadata["file_extension"] == ".txt"
        assert result.metadata["encoding"] == "utf-8"
        assert result.metadata["character_count"] > 0
        assert result.metadata["file_size"] > 0

    def test_extract_empty_file(self, sample_empty_file: Path):
        result = self.extractor.extract(sample_empty_file)
        assert result.error is None
        assert result.needs_full_processing is False
        assert result.text == ""

    def test_extract_latin1_file(self, tmp_dir: Path):
        p = tmp_dir / "latin1.txt"
        p.write_bytes("caf\xe9".encode("latin-1"))
        result = self.extractor.extract(p)
        assert result.error is None
        assert "caf" in result.text


class TestSimpleTextExtractorPDF:
    """Tests for PDF extraction."""

    def setup_method(self):
        self.extractor = SimpleTextExtractor()

    def test_extract_pdf_with_text(self, sample_pdf_with_text: Path):
        result = self.extractor.extract(sample_pdf_with_text)
        assert result.error is None
        assert result.needs_full_processing is False
        assert result.processing_mode == "pdf_text"
        assert "test PDF" in result.text

    def test_extract_pdf_metadata(self, sample_pdf_with_text: Path):
        result = self.extractor.extract(sample_pdf_with_text)
        assert result.metadata["file_extension"] == ".pdf"
        assert result.metadata["page_count"] == 1
        assert result.metadata["pages_with_text"] == 1
        assert result.metadata["text_coverage"] == 1.0

    def test_extract_pdf_no_text_needs_ocr(self, sample_pdf_no_text: Path):
        result = self.extractor.extract(sample_pdf_no_text)
        assert result.needs_full_processing is True
        assert result.processing_mode == "pdf_needs_ocr"


class TestSimpleTextExtractorFullProcessing:
    """Tests for files that need full processing."""

    def setup_method(self):
        self.extractor = SimpleTextExtractor()

    def test_docx_needs_full_processing(self, sample_docx_path: Path):
        result = self.extractor.extract(sample_docx_path)
        assert result.needs_full_processing is True
        assert result.processing_mode == "pending_full_processing"
        assert result.text == ""

    def test_xlsx_needs_full_processing(self, sample_xlsx_path: Path):
        result = self.extractor.extract(sample_xlsx_path)
        assert result.needs_full_processing is True
        assert result.processing_mode == "pending_full_processing"

    def test_pptx_needs_full_processing(self, sample_pptx_path: Path):
        result = self.extractor.extract(sample_pptx_path)
        assert result.needs_full_processing is True
        assert result.processing_mode == "pending_full_processing"


class TestSimpleTextExtractorErrors:
    """Tests for error handling."""

    def setup_method(self):
        self.extractor = SimpleTextExtractor()

    def test_file_not_found(self, nonexistent_path: Path):
        result = self.extractor.extract(nonexistent_path)
        assert result.error is not None
        assert "not found" in result.error.lower()
        assert result.needs_full_processing is False
        assert result.processing_mode == "error"

    def test_unsupported_format(self, tmp_dir: Path):
        p = tmp_dir / "file.xyz"
        p.write_text("content")
        result = self.extractor.extract(p)
        assert result.needs_full_processing is True
        assert result.processing_mode == "unsupported"
        assert result.error is not None
