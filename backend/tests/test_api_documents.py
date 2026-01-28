"""Integration tests for document upload API endpoints.

These tests create a minimal FastAPI app with the document router and mock
the database / document processor dependencies.
"""

import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.documents import router as documents_router
from models.models import ProcessingStatus


# ---------------------------------------------------------------------------
# Test app and fixtures
# ---------------------------------------------------------------------------


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(documents_router)
    return app


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    # db.add, db.commit, db.refresh all need to be async
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def app(mock_db):
    """Create a test FastAPI app with mocked DB dependency."""
    from db import get_db

    test_app = _create_test_app()

    async def override_get_db():
        yield mock_db

    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Upload endpoint tests
# ---------------------------------------------------------------------------


class TestDocumentUpload:

    @patch("api.documents.document_processor")
    @patch("api.documents.save_uploaded_file")
    @patch("api.documents.validate_file_type")
    @patch("api.documents.DeploymentConfig")
    def test_upload_txt_cloud_mode(
        self, mock_config, mock_validate_type, mock_save, mock_processor, client, mock_db
    ):
        """Upload a text file in cloud mode should succeed."""
        mock_config.MAX_UPLOAD_SIZE_MB = 10
        mock_config.DEPLOYMENT_MODE.value = "cloud"
        mock_config.is_file_supported.return_value = True
        mock_validate_type.return_value = True

        # Simulate saving file
        mock_save.return_value = Path("/tmp/uploads/test.txt")

        # Simulate successful processing
        from services.document_processor import ProcessedDocument

        mock_processor.process = AsyncMock(
            return_value=ProcessedDocument(
                success=True,
                content="Hello world",
                metadata={},
                sections=[],
                needs_full_processing=False,
                processing_mode="simple_text",
                processed_at=datetime.now(timezone.utc),
            )
        )

        # Mock the document after db.refresh
        fake_doc = MagicMock()
        fake_doc.id = 1
        fake_doc.title = "test"
        mock_db.refresh.side_effect = lambda doc: setattr(doc, "id", 1)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
            data={"title": "Test Doc"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Doc"
        assert data["processing_mode"] == "simple_text"
        assert data["needs_full_processing"] is False
        assert "fully processed" in data["message"].lower()

    @patch("api.documents.document_processor")
    @patch("api.documents.save_uploaded_file")
    @patch("api.documents.validate_file_type")
    @patch("api.documents.DeploymentConfig")
    def test_upload_docx_needs_full_processing(
        self, mock_config, mock_validate_type, mock_save, mock_processor, client, mock_db
    ):
        """Uploading a DOCX in cloud mode should mark for full processing."""
        mock_config.MAX_UPLOAD_SIZE_MB = 10
        mock_config.is_file_supported.return_value = True
        mock_validate_type.return_value = True

        mock_save.return_value = Path("/tmp/uploads/report.docx")

        from services.document_processor import ProcessedDocument

        mock_processor.process = AsyncMock(
            return_value=ProcessedDocument(
                success=True,
                content="",
                metadata={},
                sections=[],
                needs_full_processing=True,
                processing_mode="pending_full_processing",
                processed_at=datetime.now(timezone.utc),
            )
        )

        mock_db.refresh.side_effect = lambda doc: setattr(doc, "id", 2)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("report.docx", b"fake docx", "application/vnd.openxmlformats")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["needs_full_processing"] is True
        assert data["processing_mode"] == "pending_full_processing"
        assert "sync" in data["message"].lower()

    def test_upload_no_filename(self, client):
        """Upload without filename should return 400."""
        response = client.post(
            "/api/documents/upload",
            files={"file": ("", b"content", "application/octet-stream")},
        )
        assert response.status_code == 400

    @patch("api.documents.document_processor")
    @patch("api.documents.save_uploaded_file")
    @patch("api.documents.validate_file_type")
    @patch("api.documents.DeploymentConfig")
    def test_upload_processing_failure(
        self, mock_config, mock_validate_type, mock_save, mock_processor, client, mock_db
    ):
        """Processing failure should still create a document with failed status."""
        mock_config.MAX_UPLOAD_SIZE_MB = 10
        mock_config.is_file_supported.return_value = True
        mock_validate_type.return_value = True

        mock_save.return_value = Path("/tmp/uploads/bad.pdf")

        from services.document_processor import ProcessedDocument

        mock_processor.process = AsyncMock(
            return_value=ProcessedDocument(
                success=False,
                content="",
                metadata={},
                sections=[],
                needs_full_processing=False,
                processing_mode="error",
                processed_at=datetime.now(timezone.utc),
                error="Extraction failed",
            )
        )

        mock_db.refresh.side_effect = lambda doc: setattr(doc, "id", 3)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("bad.pdf", b"%PDF-1.4", "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["processing_status"] == ProcessingStatus.FAILED.value
        assert "failed" in data["message"].lower()

    @patch("api.documents.document_processor")
    @patch("api.documents.save_uploaded_file")
    @patch("api.documents.validate_file_type")
    @patch("api.documents.DeploymentConfig")
    def test_upload_uses_filename_as_title(
        self, mock_config, mock_validate_type, mock_save, mock_processor, client, mock_db
    ):
        """When no title is provided, filename stem should be used."""
        mock_config.MAX_UPLOAD_SIZE_MB = 10
        mock_config.is_file_supported.return_value = True
        mock_validate_type.return_value = True
        mock_save.return_value = Path("/tmp/uploads/my_document.txt")

        from services.document_processor import ProcessedDocument

        mock_processor.process = AsyncMock(
            return_value=ProcessedDocument(
                success=True,
                content="content",
                metadata={},
                sections=[],
                needs_full_processing=False,
                processing_mode="simple_text",
                processed_at=datetime.now(timezone.utc),
            )
        )

        mock_db.refresh.side_effect = lambda doc: setattr(doc, "id", 4)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("my_document.txt", b"content", "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "my_document"


# ---------------------------------------------------------------------------
# Document status endpoint tests
# ---------------------------------------------------------------------------


class TestDocumentStatus:

    def test_get_status_found(self, client, mock_db):
        """Should return document status when found."""
        fake_doc = MagicMock()
        fake_doc.id = 1
        fake_doc.title = "Test Doc"
        fake_doc.processing_mode = "simple_text"
        fake_doc.processing_status = "completed"
        fake_doc.needs_full_processing = False
        fake_doc.processed_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_doc
        mock_db.execute.return_value = mock_result

        response = client.get("/api/documents/1/status")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Test Doc"
        assert data["processing_status"] == "completed"

    def test_get_status_not_found(self, client, mock_db):
        """Should return 404 when document not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get("/api/documents/999/status")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Processing stats endpoint tests
# ---------------------------------------------------------------------------


class TestProcessingStats:

    @patch("api.documents.document_processor")
    def test_get_processing_stats(self, mock_processor, client, mock_db):
        """Should return processing statistics."""
        # Mock the queries module
        with patch("api.documents.get_processing_stats") as mock_stats_fn:
            # This will fail because the import is inside the function
            pass

        # Instead, mock at the module level where it's used
        mock_processor.get_capabilities.return_value = {
            "deployment_mode": "cloud",
            "processor": "SimpleTextExtractor",
            "capabilities": {"pdf_text_extraction": True},
        }

        stats_data = {
            "total": 10,
            "completed": 7,
            "pending": 1,
            "needs_local": 1,
            "failed": 1,
        }

        with patch(
            "models.document_queries.get_document_processing_stats",
            new_callable=AsyncMock,
            return_value=stats_data,
        ):
            response = client.get("/api/documents/processing/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["deployment_mode"] == "cloud"
        assert "capabilities" in data
