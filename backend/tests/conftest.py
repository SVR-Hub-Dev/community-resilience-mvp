"""Shared test fixtures for document processing tests."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_txt_file(tmp_dir: Path) -> Path:
    """Create a sample text file."""
    p = tmp_dir / "sample.txt"
    p.write_text("This is a sample text document.\nIt has multiple lines.\n")
    return p


@pytest.fixture
def sample_md_file(tmp_dir: Path) -> Path:
    """Create a sample markdown file."""
    p = tmp_dir / "sample.md"
    p.write_text("# Heading\n\nThis is a **markdown** document.\n\n## Section\n\nSome content.\n")
    return p


@pytest.fixture
def sample_empty_file(tmp_dir: Path) -> Path:
    """Create an empty text file."""
    p = tmp_dir / "empty.txt"
    p.write_text("")
    return p


@pytest.fixture
def sample_docx_path(tmp_dir: Path) -> Path:
    """Create a dummy .docx file (not a real docx, just for path-based tests)."""
    p = tmp_dir / "report.docx"
    p.write_bytes(b"fake docx content")
    return p


@pytest.fixture
def sample_xlsx_path(tmp_dir: Path) -> Path:
    """Create a dummy .xlsx file."""
    p = tmp_dir / "data.xlsx"
    p.write_bytes(b"fake xlsx content")
    return p


@pytest.fixture
def sample_pptx_path(tmp_dir: Path) -> Path:
    """Create a dummy .pptx file."""
    p = tmp_dir / "slides.pptx"
    p.write_bytes(b"fake pptx content")
    return p


@pytest.fixture
def nonexistent_path(tmp_dir: Path) -> Path:
    """Return a path to a file that does not exist."""
    return tmp_dir / "does_not_exist.pdf"


@pytest.fixture
def sample_pdf_with_text(tmp_dir: Path) -> Path:
    """Create a minimal PDF with extractable text using PyMuPDF."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a test PDF with extractable text content.\n" * 5)
    path = tmp_dir / "with_text.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def sample_pdf_no_text(tmp_dir: Path) -> Path:
    """Create a minimal PDF with no text (simulating a scanned document)."""
    import fitz

    doc = fitz.open()
    doc.new_page()  # Empty page — no text
    path = tmp_dir / "no_text.pdf"
    doc.save(str(path))
    doc.close()
    return path
