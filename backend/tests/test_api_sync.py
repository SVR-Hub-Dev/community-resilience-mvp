"""Integration tests for sync API endpoints.

These tests create a minimal FastAPI app with the sync router and mock
the database and authentication dependencies.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.sync import router as sync_router, verify_sync_api_key
from models.models import ProcessingStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_API_KEY = "test-sync-key-12345"


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(sync_router)
    return app


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def app(mock_db):
    """Create a test FastAPI app with mocked DB and auth dependencies."""
    from db import get_db

    test_app = _create_test_app()

    async def override_get_db():
        yield mock_db

    async def override_verify_key():
        return TEST_API_KEY

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[verify_sync_api_key] = override_verify_key
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def app_with_real_auth(mock_db):
    """Create a test app that uses real API key verification."""
    from db import get_db

    test_app = _create_test_app()

    async def override_get_db():
        yield mock_db

    test_app.dependency_overrides[get_db] = override_get_db
    # Do NOT override verify_sync_api_key — use the real implementation
    return test_app


@pytest.fixture
def client_real_auth(app_with_real_auth):
    return TestClient(app_with_real_auth)


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestSyncAuthentication:

    @patch("api.sync.SyncConfig")
    def test_missing_api_key_header(self, mock_sync_config, client_real_auth):
        """Should return 401 when X-Sync-API-Key header is missing."""
        mock_sync_config.SYNC_API_KEY = TEST_API_KEY

        response = client_real_auth.get("/api/sync/documents/unprocessed")
        assert response.status_code == 401
        assert "Missing" in response.json()["detail"]

    @patch("api.sync.SyncConfig")
    def test_invalid_api_key(self, mock_sync_config, client_real_auth):
        """Should return 403 when API key is invalid."""
        mock_sync_config.SYNC_API_KEY = TEST_API_KEY

        response = client_real_auth.get(
            "/api/sync/documents/unprocessed",
            headers={"X-Sync-API-Key": "wrong-key"},
        )
        assert response.status_code == 403
        assert "Invalid" in response.json()["detail"]

    @patch("api.sync.SyncConfig")
    def test_sync_not_configured(self, mock_sync_config, client_real_auth):
        """Should return 503 when sync is not configured."""
        mock_sync_config.SYNC_API_KEY = None  # Not configured

        response = client_real_auth.get(
            "/api/sync/documents/unprocessed",
            headers={"X-Sync-API-Key": "any-key"},
        )
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]

    @patch("api.sync.SyncConfig")
    def test_valid_api_key(self, mock_sync_config, client_real_auth, mock_db):
        """Should succeed with correct API key."""
        mock_sync_config.SYNC_API_KEY = TEST_API_KEY

        # Mock get_unprocessed_documents to return empty list
        with patch(
            "api.sync.get_unprocessed_documents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client_real_auth.get(
                "/api/sync/documents/unprocessed",
                headers={"X-Sync-API-Key": TEST_API_KEY},
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Unprocessed documents endpoint tests
# ---------------------------------------------------------------------------


class TestListUnprocessedDocuments:

    def test_returns_empty_list(self, client, mock_db):
        """Should return empty list when no unprocessed docs exist."""
        with patch(
            "api.sync.get_unprocessed_documents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = client.get("/api/sync/documents/unprocessed")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_unprocessed_documents(self, client, mock_db):
        """Should return list of documents needing processing."""
        now = datetime.now(timezone.utc)

        fake_doc = MagicMock()
        fake_doc.id = 1
        fake_doc.title = "Report"
        fake_doc.raw_file_path = "/data/uploads/report.docx"
        fake_doc.processing_status = ProcessingStatus.NEEDS_LOCAL.value
        fake_doc.created_at = now

        with patch(
            "api.sync.get_unprocessed_documents",
            new_callable=AsyncMock,
            return_value=[fake_doc],
        ):
            response = client.get("/api/sync/documents/unprocessed")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Report"
        assert data[0]["processing_status"] == ProcessingStatus.NEEDS_LOCAL.value

    def test_respects_limit_param(self, client, mock_db):
        """Should pass limit parameter to query function."""
        with patch(
            "api.sync.get_unprocessed_documents",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_fn:
            client.get("/api/sync/documents/unprocessed?limit=5")
            mock_fn.assert_called_once()
            # Check the limit argument
            call_kwargs = mock_fn.call_args
            assert call_kwargs[1].get("limit") == 5 or call_kwargs[0][1] == 5


# ---------------------------------------------------------------------------
# Download document file endpoint tests
# ---------------------------------------------------------------------------


class TestDownloadDocumentFile:

    def test_document_not_found(self, client, mock_db):
        """Should return 404 when document doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.get("/api/sync/documents/999/download")
        assert response.status_code == 404

    def test_document_no_raw_file(self, client, mock_db):
        """Should return 404 when document has no raw file path."""
        fake_doc = MagicMock()
        fake_doc.raw_file_path = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_doc
        mock_db.execute.return_value = mock_result

        response = client.get("/api/sync/documents/1/download")
        assert response.status_code == 404
        assert "no raw file" in response.json()["detail"]

    def test_file_missing_on_disk(self, client, mock_db, tmp_path):
        """Should return 404 when file path exists in DB but not on disk."""
        missing_path = str(tmp_path / "nonexistent.pdf")

        fake_doc = MagicMock()
        fake_doc.raw_file_path = missing_path

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_doc
        mock_db.execute.return_value = mock_result

        response = client.get("/api/sync/documents/1/download")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_successful_download(self, client, mock_db, tmp_path):
        """Should return file content when document and file exist."""
        file_path = tmp_path / "report.pdf"
        file_path.write_bytes(b"%PDF-1.4 test content")

        fake_doc = MagicMock()
        fake_doc.raw_file_path = str(file_path)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_doc
        mock_db.execute.return_value = mock_result

        with patch(
            "api.sync.mark_document_processing",
            new_callable=AsyncMock,
        ):
            response = client.get("/api/sync/documents/1/download")

        assert response.status_code == 200
        assert b"%PDF-1.4 test content" in response.content


# ---------------------------------------------------------------------------
# Submit processed content endpoint tests
# ---------------------------------------------------------------------------


class TestSubmitProcessedContent:

    def test_document_not_found(self, client, mock_db):
        """Should return 404 when document doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = client.post(
            "/api/sync/documents/999/processed",
            json={
                "content": "Processed text",
                "processing_mode": "local_full",
            },
        )
        assert response.status_code == 404

    def test_successful_submit(self, client, mock_db):
        """Should update document with processed content."""
        fake_doc = MagicMock()
        fake_doc.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_doc
        mock_db.execute.return_value = mock_result

        with patch(
            "api.sync.update_document_processed",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = client.post(
                "/api/sync/documents/1/processed",
                json={
                    "content": "Full OCR text",
                    "processing_mode": "local_full",
                    "metadata": {"word_count": 500},
                    "sections": [{"title": "Intro", "content": "..."}],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["document_id"] == 1
        assert data["processing_mode"] == "local_full"

    def test_update_conflict(self, client, mock_db):
        """Should return 409 when document update fails."""
        fake_doc = MagicMock()
        fake_doc.id = 1

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_doc
        mock_db.execute.return_value = mock_result

        with patch(
            "api.sync.update_document_processed",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = client.post(
                "/api/sync/documents/1/processed",
                json={
                    "content": "text",
                    "processing_mode": "local_full",
                },
            )

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Mark processing failed endpoint tests
# ---------------------------------------------------------------------------


class TestMarkProcessingFailed:

    def test_mark_failed_success(self, client, mock_db):
        """Should mark document as failed."""
        with patch(
            "api.sync.mark_document_failed",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = client.post(
                "/api/sync/documents/1/failed",
                params={"error_message": "OCR failed"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == ProcessingStatus.FAILED.value

    def test_mark_failed_not_found(self, client, mock_db):
        """Should return 404 when document doesn't exist."""
        with patch(
            "api.sync.mark_document_failed",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = client.post(
                "/api/sync/documents/999/failed",
                params={"error_message": "not found"},
            )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Sync pull endpoint tests
# ---------------------------------------------------------------------------


class TestSyncPull:

    def test_pull_empty(self, client, mock_db):
        """Should return empty document list when no new docs."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch("api.sync.SyncLog") as mock_sync_log, patch(
            "api.sync.SyncMetadata"
        ) as mock_sync_meta:
            mock_log_instance = AsyncMock()
            mock_sync_log.start_sync = AsyncMock(return_value=mock_log_instance)
            mock_sync_meta.set_value = AsyncMock()

            response = client.get("/api/sync/pull")

        assert response.status_code == 200
        data = response.json()
        assert data["documents"] == []
        assert data["has_more"] is False

    def test_pull_with_documents(self, client, mock_db):
        """Should return documents and pagination info."""
        now = datetime.now(timezone.utc)

        fake_doc = MagicMock()
        fake_doc.id = 1
        fake_doc.title = "Test"
        fake_doc.description = "Desc"
        fake_doc.tags = ["tag1"]
        fake_doc.location = "NYC"
        fake_doc.hazard_type = "flood"
        fake_doc.processing_status = "completed"
        fake_doc.needs_full_processing = False
        fake_doc.created_at = now

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fake_doc]
        mock_db.execute.return_value = mock_result

        with patch("api.sync.SyncLog") as mock_sync_log, patch(
            "api.sync.SyncMetadata"
        ) as mock_sync_meta:
            mock_log_instance = AsyncMock()
            mock_sync_log.start_sync = AsyncMock(return_value=mock_log_instance)
            mock_sync_meta.set_value = AsyncMock()

            response = client.get("/api/sync/pull")

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 1
        assert data["documents"][0]["id"] == 1
        assert data["has_more"] is False

    def test_pull_with_since_param(self, client, mock_db):
        """Should accept since timestamp parameter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch("api.sync.SyncLog") as mock_sync_log, patch(
            "api.sync.SyncMetadata"
        ) as mock_sync_meta:
            mock_log_instance = AsyncMock()
            mock_sync_log.start_sync = AsyncMock(return_value=mock_log_instance)
            mock_sync_meta.set_value = AsyncMock()

            response = client.get(
                "/api/sync/pull",
                params={"since": "2025-01-01T00:00:00Z"},
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Sync push endpoint tests
# ---------------------------------------------------------------------------


class TestSyncPush:

    def test_push_success(self, client, mock_db):
        """Should process pushed documents."""
        with patch("api.sync.SyncLog") as mock_sync_log, patch(
            "api.sync.SyncMetadata"
        ) as mock_sync_meta, patch(
            "api.sync.update_document_processed",
            new_callable=AsyncMock,
            return_value=True,
        ):
            mock_log_instance = AsyncMock()
            mock_sync_log.start_sync = AsyncMock(return_value=mock_log_instance)
            mock_sync_meta.set_value = AsyncMock()

            response = client.post(
                "/api/sync/push",
                json={
                    "documents": [
                        {
                            "id": 1,
                            "content": "Processed text",
                            "processing_mode": "local_full",
                            "metadata": {"word_count": 100},
                        }
                    ],
                    "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["processed_count"] == 1
        assert data["failed_count"] == 0

    def test_push_with_missing_id(self, client, mock_db):
        """Should report error for documents missing ID."""
        with patch("api.sync.SyncLog") as mock_sync_log, patch(
            "api.sync.SyncMetadata"
        ) as mock_sync_meta:
            mock_log_instance = AsyncMock()
            mock_sync_log.start_sync = AsyncMock(return_value=mock_log_instance)
            mock_sync_meta.set_value = AsyncMock()

            response = client.post(
                "/api/sync/push",
                json={
                    "documents": [{"content": "No ID doc", "processing_mode": "local"}],
                    "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["processed_count"] == 0
        assert data["failed_count"] == 1
        assert len(data["errors"]) == 1

    def test_push_partial_failure(self, client, mock_db):
        """Should handle partial failures gracefully."""
        call_count = 0

        async def update_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            # First doc succeeds, second fails
            return call_count == 1

        with patch("api.sync.SyncLog") as mock_sync_log, patch(
            "api.sync.SyncMetadata"
        ) as mock_sync_meta, patch(
            "api.sync.update_document_processed",
            new_callable=AsyncMock,
            side_effect=update_side_effect,
        ):
            mock_log_instance = AsyncMock()
            mock_sync_log.start_sync = AsyncMock(return_value=mock_log_instance)
            mock_sync_meta.set_value = AsyncMock()

            response = client.post(
                "/api/sync/push",
                json={
                    "documents": [
                        {"id": 1, "content": "Good", "processing_mode": "local"},
                        {"id": 2, "content": "Bad", "processing_mode": "local"},
                    ],
                    "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["processed_count"] == 1
        assert data["failed_count"] == 1


# ---------------------------------------------------------------------------
# Sync status endpoint tests
# ---------------------------------------------------------------------------


class TestSyncStatus:

    def test_get_status(self, client, mock_db):
        """Should return sync status and statistics."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch("api.sync.SyncConfig") as mock_sync_config, patch(
            "api.sync.SyncMetadata"
        ) as mock_sync_meta, patch(
            "api.sync.get_document_processing_stats",
            new_callable=AsyncMock,
            return_value={
                "total": 5,
                "completed": 3,
                "pending": 1,
                "needs_local": 1,
                "failed": 0,
            },
        ):
            mock_sync_config.SYNC_ENABLED = True
            mock_sync_meta.get_value = AsyncMock(return_value=None)
            mock_sync_meta.LAST_PULL_TIMESTAMP = "last_pull_timestamp"
            mock_sync_meta.LAST_PUSH_TIMESTAMP = "last_push_timestamp"
            mock_sync_meta.LAST_SYNC_TIMESTAMP = "last_sync_timestamp"

            response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["sync_enabled"] is True
        assert data["processing_stats"]["total"] == 5
        assert "recent_syncs" in data
