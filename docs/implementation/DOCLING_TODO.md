# Docling Integration Implementation Checklist

## Phase 1: Backend Configuration ✅

- [x] **Create deployment configuration**
  - [x] Add `DeploymentMode` enum to `backend/config.py`
  - [x] Add feature flags (`DOCLING_ENABLED`, `FULL_OCR_ENABLED`, `OFFICE_CONVERSION_ENABLED`)
  - [x] Add processing settings (`MAX_UPLOAD_SIZE_MB`, `PROCESS_TIMEOUT_SECONDS`)

- [x] **Create requirements files**
  - [x] Update `backend/requirements.txt` with cloud-only dependencies (PyMuPDF, etc.)
  - [x] Create `backend/requirements-local.txt` with Docling dependencies

## Phase 2: Document Processing Services

- [x] **Create simple text extractor (cloud)**
  - [x] Create `backend/services/simple_extractor.py`
  - [x] Implement PDF text extraction with PyMuPDF
  - [x] Implement plain text/markdown reading
  - [x] Return `needs_full_processing=True` for unsupported formats

- [x] **Create Docling processor (local)**
  - [x] Create `backend/services/docling_service.py`
  - [x] Implement full document conversion
  - [x] Implement structured section extraction
  - [x] Implement metadata extraction

- [x] **Create document processor factory**
  - [x] Create `backend/services/document_processor.py`
  - [x] Implement conditional loading based on `DEPLOYMENT_MODE`
  - [x] Add processing metadata to results

## Phase 3: Database Schema

- [x] **Create Alembic migration for document processing fields**
  - [x] Add `needs_full_processing` boolean column
  - [x] Add `processing_mode` varchar column
  - [x] Add `raw_file_path` text column
  - [x] Add `processed_at` timestamp column
  - [x] Add `processing_status` column

- [x] **Create sync metadata tables**
  - [x] Create `sync_metadata` table
  - [x] Create `sync_log` table

## Phase 4: API Endpoints

- [x] **Update document upload endpoint**
  - [x] Add file size validation based on deployment mode
  - [x] Implement background processing task
  - [x] Store raw file path for cloud uploads
  - [x] Return processing mode in response

- [x] **Create sync endpoints**
  - [x] `GET /api/sync/documents/unprocessed` - list documents needing processing
  - [x] `POST /api/sync/documents/{id}/processed` - receive processed content
  - [x] `POST /api/sync/push` - accept changes from local
  - [x] `GET /api/sync/pull` - return changes since timestamp
  - [x] Add API key authentication for sync endpoints

## Phase 5: Sync Service

- [x] **Create document sync service**
  - [x] Create `backend/services/document_sync.py`
  - [x] Implement `pull_unprocessed_documents()`
  - [x] Implement `push_processed_documents()`
  - [x] Implement `sync_processed_document()`

- [x] **Create sync worker**
  - [x] Create `backend/services/sync_worker.py`
  - [x] Implement main sync loop with configurable interval
  - [x] Implement document download from cloud
  - [x] Implement Docling processing of downloaded documents
  - [x] Implement push of processed results

## Phase 6: Docker Configuration ✅

- [x] **Create cloud Dockerfile**
  - [x] Minimal system dependencies (libpq-dev only)
  - [x] Set `DEPLOYMENT_MODE=cloud`

- [x] **Create local Dockerfile**
  - [x] Create `backend/Dockerfile.local`
  - [x] Add Docling system dependencies (poppler-utils, tesseract-ocr, libreoffice)
  - [x] Install both requirements files
  - [x] Set `DEPLOYMENT_MODE=local`

- [x] **Create local docker-compose**
  - [x] Create `docker-compose.local.yml`
  - [x] Configure database service with pgvector
  - [x] Configure Ollama service with memory limits
  - [x] Configure backend with local environment
  - [x] Configure sync-worker service (optional profile)
  - [x] Add document storage volume

## Phase 7: Frontend Updates ✅

- [x] **Update document upload component**
  - [x] Display processing mode in response
  - [x] Show info message for cloud mode limitations
  - [x] Indicate when full processing will occur

- [x] **Add document status indicators**
  - [x] Show "basic processing" vs "full processing" badge
  - [x] Show "pending sync" status for unprocessed documents

## Phase 8: Testing ✅

- [x] **Unit tests**
  - [x] Test `SimpleTextExtractor` with PDF, TXT, MD files
  - [x] Test `DoclingProcessor` with various document types
  - [x] Test `DocumentProcessor` factory logic

- [x] **Integration tests**
  - [x] Test document upload in cloud mode
  - [x] Test document upload in local mode
  - [x] Test sync endpoints with mock data

- [x] **End-to-end tests**
  - [x] Test full sync cycle: upload → sync → process → push back
  - [x] Test offline local operation

## Phase 9: Documentation ✅

- [x] **Update DEPLOYMENT.md**
  - [x] Document cloud vs local processing differences
  - [x] Add troubleshooting for document processing issues

- [x] **Update README**
  - [x] Add section on document processing capabilities
  - [x] Document sync configuration options

---

## Quick Start Commands

```bash
# Run migration
cd backend && alembic revision --autogenerate -m "add document processing fields"
alembic upgrade head

# Test cloud mode locally
DEPLOYMENT_MODE=cloud python -m pytest tests/test_document_processor.py

# Build local Docker image
docker build -f backend/Dockerfile.local -t community-resilience-backend:local ./backend

# Start local instance with sync
docker-compose -f docker-compose.local.yml --profile sync up -d
```
