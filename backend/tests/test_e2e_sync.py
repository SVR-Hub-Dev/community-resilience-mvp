"""End-to-end sync cycle test.

Simulates the full lifecycle:
  1. Upload a document in cloud mode (queued for full processing)
  2. Sync worker pulls unprocessed documents
  3. Sync worker downloads the raw file
  4. Local processor processes the document with Docling
  5. Sync worker pushes processed content back to cloud

All database and file-system operations are mocked.
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

from api.documents import router as documents_router
from api.sync import router as sync_router, verify_sync_api_key
from models.models import ProcessingStatus


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TEST_API_KEY = "e2e-test-key"

# In-memory "database" for the e2e test
_documents_store: dict[int, dict] = {}
_next_id = 1


def _reset_store():
    global _documents_store, _next_id
    _documents_store = {}
    _next_id = 1


def _add_document(doc_dict: dict) -> int:
    global _next_id
    doc_id = _next_id
    _next_id += 1
    doc_dict["id"] = doc_id
    _documents_store[doc_id] = doc_dict
    return doc_id


@pytest.fixture(autouse=True)
def reset_store():
    _reset_store()
    yield
    _reset_store()


@pytest.fixture
def mock_db():
    """A mock async DB session wired to our in-memory store."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def fake_refresh(obj):
        """Simulate DB refresh by assigning an ID."""
        if not hasattr(obj, "id") or obj.id is None:
            doc_dict = {
                "id": None,
                "title": getattr(obj, "title", ""),
                "description": getattr(obj, "description", ""),
                "tags": getattr(obj, "tags", []),
                "location": getattr(obj, "location", None),
                "hazard_type": getattr(obj, "hazard_type", None),
                "source": getattr(obj, "source", None),
                "processing_status": getattr(obj, "processing_status", "pending"),
                "processing_mode": getattr(obj, "processing_mode", "pending"),
                "needs_full_processing": getattr(obj, "needs_full_processing", False),
                "raw_file_path": getattr(obj, "raw_file_path", None),
                "processed_at": getattr(obj, "processed_at", None),
                "created_at": datetime.now(timezone.utc),
            }
            doc_id = _add_document(doc_dict)
            obj.id = doc_id

    db.refresh = AsyncMock(side_effect=fake_refresh)
    return db


@pytest.fixture
def e2e_app(mock_db):
    """FastAPI app with both documents and sync routers."""
    from db import get_db

    app = FastAPI()
    app.include_router(documents_router)
    app.include_router(sync_router)

    async def override_get_db():
        yield mock_db

    async def override_verify_key():
        return TEST_API_KEY

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_sync_api_key] = override_verify_key
    return app


@pytest.fixture
def e2e_client(e2e_app):
    return TestClient(e2e_app)


# ---------------------------------------------------------------------------
# End-to-end sync cycle
# ---------------------------------------------------------------------------


class TestEndToEndSyncCycle:
    """
    Simulates:
      Cloud upload → sync pull → file download → local process → sync push
    """

    @patch("api.documents.document_processor")
    @patch("api.documents.save_uploaded_file")
    @patch("api.documents.validate_file_type")
    @patch("api.documents.DeploymentConfig")
    def test_full_sync_cycle(
        self,
        mock_deploy_config,
        mock_validate_type,
        mock_save_file,
        mock_processor,
        e2e_client,
        mock_db,
        tmp_path,
    ):
        # --- Configuration ---
        mock_deploy_config.MAX_UPLOAD_SIZE_MB = 10
        mock_deploy_config.DEPLOYMENT_MODE.value = "cloud"
        mock_deploy_config.is_file_supported.return_value = True
        mock_validate_type.return_value = True

        # Create a real file on disk for download step
        raw_file = tmp_path / "community_report.docx"
        raw_file.write_bytes(b"PK\x03\x04 fake docx content for OCR testing")

        mock_save_file.return_value = raw_file

        # --- Step 1: Upload document in cloud mode ---
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

        upload_resp = e2e_client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "community_report.docx",
                    b"PK\x03\x04 fake docx",
                    "application/vnd.openxmlformats",
                )
            },
            data={"title": "Community Flood Report"},
        )

        assert upload_resp.status_code == 200
        upload_data = upload_resp.json()
        doc_id = upload_data["id"]
        assert upload_data["needs_full_processing"] is True
        assert upload_data["processing_status"] == ProcessingStatus.NEEDS_LOCAL.value

        # --- Step 2: Sync worker pulls unprocessed documents ---
        now = datetime.now(timezone.utc)
        fake_unprocessed_doc = MagicMock()
        fake_unprocessed_doc.id = doc_id
        fake_unprocessed_doc.title = "Community Flood Report"
        fake_unprocessed_doc.raw_file_path = str(raw_file)
        fake_unprocessed_doc.processing_status = ProcessingStatus.NEEDS_LOCAL.value
        fake_unprocessed_doc.created_at = now

        with patch(
            "api.sync.get_unprocessed_documents",
            new_callable=AsyncMock,
            return_value=[fake_unprocessed_doc],
        ):
            pull_resp = e2e_client.get("/api/sync/documents/unprocessed")

        assert pull_resp.status_code == 200
        unprocessed = pull_resp.json()
        assert len(unprocessed) == 1
        assert unprocessed[0]["id"] == doc_id

        # --- Step 3: Sync worker downloads the raw file ---
        fake_download_doc = MagicMock()
        fake_download_doc.raw_file_path = str(raw_file)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_download_doc
        mock_db.execute.return_value = mock_result

        with patch(
            "api.sync.mark_document_processing",
            new_callable=AsyncMock,
        ):
            download_resp = e2e_client.get(f"/api/sync/documents/{doc_id}/download")

        assert download_resp.status_code == 200
        assert b"fake docx content" in download_resp.content

        # --- Step 4: Local Docling processes the file (simulated) ---
        processed_content = """# Community Flood Report

## Executive Summary
This report documents the 2024 flooding event in the riverside community.

## Impact Assessment
- 45 homes affected
- Community center used as shelter
- Road access limited for 3 days

## Community Response
Local volunteers organized sandbagging operations within 2 hours.
"""
        processed_metadata = {
            "word_count": 42,
            "page_count": 3,
            "processing_mode": "local_full",
            "sections": 3,
        }

        # --- Step 5: Sync worker pushes processed content back ---
        fake_push_doc = MagicMock()
        fake_push_doc.id = doc_id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_push_doc
        mock_db.execute.return_value = mock_result

        with patch(
            "api.sync.update_document_processed",
            new_callable=AsyncMock,
            return_value=True,
        ):
            push_resp = e2e_client.post(
                f"/api/sync/documents/{doc_id}/processed",
                json={
                    "content": processed_content,
                    "processing_mode": "local_full",
                    "metadata": processed_metadata,
                    "sections": [
                        {"title": "Executive Summary", "content": "..."},
                        {"title": "Impact Assessment", "content": "..."},
                        {"title": "Community Response", "content": "..."},
                    ],
                },
            )

        assert push_resp.status_code == 200
        push_data = push_resp.json()
        assert push_data["success"] is True
        assert push_data["document_id"] == doc_id
        assert push_data["processing_mode"] == "local_full"

    @patch("api.documents.document_processor")
    @patch("api.documents.save_uploaded_file")
    @patch("api.documents.validate_file_type")
    @patch("api.documents.DeploymentConfig")
    def test_sync_cycle_processing_failure(
        self,
        mock_deploy_config,
        mock_validate_type,
        mock_save_file,
        mock_processor,
        e2e_client,
        mock_db,
        tmp_path,
    ):
        """Test the sync cycle when local processing fails."""
        mock_deploy_config.MAX_UPLOAD_SIZE_MB = 10
        mock_deploy_config.DEPLOYMENT_MODE.value = "cloud"
        mock_deploy_config.is_file_supported.return_value = True
        mock_validate_type.return_value = True

        raw_file = tmp_path / "corrupted.pdf"
        raw_file.write_bytes(b"not a real PDF")
        mock_save_file.return_value = raw_file

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

        # Step 1: Upload
        upload_resp = e2e_client.post(
            "/api/documents/upload",
            files={"file": ("corrupted.pdf", b"not a PDF", "application/pdf")},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["id"]

        # Step 2: Local processing fails → mark as failed
        with patch(
            "api.sync.mark_document_failed",
            new_callable=AsyncMock,
            return_value=True,
        ):
            fail_resp = e2e_client.post(
                f"/api/sync/documents/{doc_id}/failed",
                params={"error_message": "Docling conversion failed: corrupted file"},
            )

        assert fail_resp.status_code == 200
        fail_data = fail_resp.json()
        assert fail_data["success"] is True
        assert fail_data["status"] == ProcessingStatus.FAILED.value

    @patch("api.documents.document_processor")
    @patch("api.documents.save_uploaded_file")
    @patch("api.documents.validate_file_type")
    @patch("api.documents.DeploymentConfig")
    def test_bulk_sync_push(
        self,
        mock_deploy_config,
        mock_validate_type,
        mock_save_file,
        mock_processor,
        e2e_client,
        mock_db,
        tmp_path,
    ):
        """Test pushing multiple processed documents at once."""
        mock_deploy_config.MAX_UPLOAD_SIZE_MB = 10
        mock_deploy_config.DEPLOYMENT_MODE.value = "cloud"
        mock_deploy_config.is_file_supported.return_value = True
        mock_validate_type.return_value = True

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

        # Upload 3 documents
        doc_ids = []
        for i in range(3):
            f = tmp_path / f"doc_{i}.docx"
            f.write_bytes(b"PK fake")
            mock_save_file.return_value = f

            resp = e2e_client.post(
                "/api/documents/upload",
                files={"file": (f"doc_{i}.docx", b"PK fake", "application/vnd.openxmlformats")},
            )
            assert resp.status_code == 200
            doc_ids.append(resp.json()["id"])

        # Bulk push all three
        with patch("api.sync.SyncLog") as mock_sync_log, \
             patch("api.sync.SyncMetadata") as mock_sync_meta, \
             patch(
                 "api.sync.update_document_processed",
                 new_callable=AsyncMock,
                 return_value=True,
             ):
            mock_log_instance = AsyncMock()
            mock_sync_log.start_sync = AsyncMock(return_value=mock_log_instance)
            mock_sync_meta.set_value = AsyncMock()

            push_resp = e2e_client.post(
                "/api/sync/push",
                json={
                    "documents": [
                        {
                            "id": doc_id,
                            "content": f"Processed content for doc {doc_id}",
                            "processing_mode": "local_full",
                            "metadata": {"word_count": 100 * (i + 1)},
                        }
                        for i, doc_id in enumerate(doc_ids)
                    ],
                    "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        assert push_resp.status_code == 200
        data = push_resp.json()
        assert data["processed_count"] == 3
        assert data["failed_count"] == 0
        assert data["errors"] == []
