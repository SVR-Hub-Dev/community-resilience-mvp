# Integrating Docling into the Community Resilience Hub Workflow

Docling is an excellent choice for document processing - it handles multiple formats (PDF, DOCX, PPTX, etc.) and can extract structured content. This document describes the **hybrid processing strategy** that works within free-tier cloud constraints.

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                   HYBRID DOCUMENT PROCESSING PIPELINE                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CLOUD (Render Free Tier)              LOCAL INSTANCE                   │
│  ┌─────────────────────┐               ┌─────────────────────┐          │
│  │  Document Upload    │               │  Full Docling       │          │
│  │  Basic Text Extract │───sync───────▶│  Processing         │          │
│  │  Store Raw File     │               │  OCR + Structure    │          │
│  └─────────────────────┘               └─────────────────────┘          │
│           │                                      │                       │
│           ▼                                      ▼                       │
│  ┌─────────────────────┐               ┌─────────────────────┐          │
│  │  Basic Embeddings   │◀───sync───────│  Rich Embeddings    │          │
│  │  Limited Search     │               │  Full Search        │          │
│  └─────────────────────┘               └─────────────────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Deployment Mode Comparison

| Feature | Cloud (Free Tier) | Local Instance |
| ------- | ----------------- | -------------- |
| Document Upload | ✅ Yes | ✅ Yes |
| Basic Text Extraction | ✅ PyMuPDF | ✅ PyMuPDF |
| Full Docling Processing | ❌ No (RAM limited) | ✅ Yes |
| OCR Support | ❌ No | ✅ Tesseract |
| Office Document Conversion | ❌ No | ✅ LibreOffice |
| Structured Section Extraction | ❌ No | ✅ Yes |
| Memory Requirements | 512MB | 4GB+ recommended |

## Implementation

### 1. Deployment Configuration

```python
# backend/config.py

import os
from enum import Enum

class DeploymentMode(Enum):
    CLOUD = "cloud"
    LOCAL = "local"

class DeploymentConfig:
    DEPLOYMENT_MODE = DeploymentMode(os.getenv("DEPLOYMENT_MODE", "cloud"))
    
    # Feature flags based on deployment
    DOCLING_ENABLED = DEPLOYMENT_MODE == DeploymentMode.LOCAL
    FULL_OCR_ENABLED = DEPLOYMENT_MODE == DeploymentMode.LOCAL
    OFFICE_CONVERSION_ENABLED = DEPLOYMENT_MODE == DeploymentMode.LOCAL
    
    # Processing settings
    MAX_UPLOAD_SIZE_MB = 50 if DEPLOYMENT_MODE == DeploymentMode.LOCAL else 10
    PROCESS_TIMEOUT_SECONDS = 300 if DEPLOYMENT_MODE == DeploymentMode.LOCAL else 30
```

### 2. Document Processor Factory

```python
# backend/services/document_processor.py

from config import DeploymentConfig, DeploymentMode
from typing import Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Factory that returns appropriate processor based on deployment mode."""
    
    def __init__(self):
        self.deployment_mode = DeploymentConfig.DEPLOYMENT_MODE
        
        if self.deployment_mode == DeploymentMode.LOCAL:
            from services.docling_service import DoclingProcessor
            self.processor = DoclingProcessor()
            logger.info("Using full Docling processor (local mode)")
        else:
            from services.simple_extractor import SimpleTextExtractor
            self.processor = SimpleTextExtractor()
            logger.info("Using simple text extractor (cloud mode)")
    
    async def process(self, file_path: Path) -> Dict:
        """Process document using appropriate strategy."""
        result = await self.processor.process_document(file_path)
        
        # Add processing metadata
        result['processing_mode'] = self.deployment_mode.value
        result['needs_full_processing'] = self.deployment_mode == DeploymentMode.CLOUD
        
        return result
```

### 3. Simple Text Extractor (Cloud)

```python
# backend/services/simple_extractor.py

from pathlib import Path
from typing import Dict
import fitz  # PyMuPDF - lightweight, no system deps

class SimpleTextExtractor:
    """Lightweight text extraction for cloud deployment."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md'}
    
    async def process_document(self, file_path: Path) -> Dict:
        """Extract basic text content without heavy processing."""
        extension = file_path.suffix.lower()
        
        if extension not in self.SUPPORTED_EXTENSIONS:
            return {
                'success': False,
                'error': f'File type {extension} requires local processing',
                'content': None,
                'needs_full_processing': True
            }
        
        try:
            if extension == '.pdf':
                content = self._extract_pdf_text(file_path)
            else:
                content = file_path.read_text()
            
            return {
                'success': True,
                'content': content,
                'metadata': {
                    'filename': file_path.name,
                    'word_count': len(content.split()),
                    'processing_mode': 'cloud_simple'
                },
                'sections': [],  # No section extraction in cloud mode
                'needs_full_processing': True
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF."""
        doc = fitz.open(str(file_path))
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return '\n'.join(text_parts)
```

### 4. Full Docling Processor (Local Only)

```python
# backend/services/docling_service.py

from docling.document_converter import DocumentConverter
from typing import List, Dict
import asyncio
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DoclingProcessor:
    """Full document processing with Docling - local deployment only."""
    
    def __init__(self):
        self.converter = DocumentConverter()
        logger.info("Docling processor initialized")

    async def process_document(self, file_path: Path) -> Dict:
        """Process document and extract structured content."""
        try:
            # Convert document to structured format
            result = await asyncio.to_thread(
                self.converter.convert, str(file_path)
            )
            
            return {
                'success': True,
                'content': self._extract_structured_content(result),
                'metadata': self._extract_metadata(result, file_path),
                'sections': self._extract_sections(result),
                'needs_full_processing': False
            }
        except Exception as e:
            logger.error(f"Docling processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _extract_structured_content(self, result) -> str:
        """Extract main content as text."""
        return result.document.export_to_text()
    
    def _extract_metadata(self, result, file_path: Path) -> Dict:
        """Extract document metadata."""
        doc = result.document
        content = doc.export_to_text()
        return {
            'filename': file_path.name,
            'title': getattr(doc, 'title', '') or file_path.stem,
            'author': getattr(doc, 'author', ''),
            'creation_date': getattr(doc, 'creation_date', ''),
            'page_count': len(doc.pages) if hasattr(doc, 'pages') else 0,
            'word_count': len(content.split()),
            'processing_mode': 'local_full'
        }
    
    def _extract_sections(self, result) -> List[Dict]:
        """Extract document sections with hierarchy."""
        sections = []
        if hasattr(result.document, 'sections'):
            for section in result.document.sections:
                sections.append({
                    'title': section.title,
                    'level': section.level,
                    'content': section.export_to_text(),
                    'page_numbers': getattr(section, 'page_numbers', [])
                })
        return sections
```

### 5. Document Upload API

```python
# backend/app/api/documents.py

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from services.document_processor import DocumentProcessor
from config import DeploymentConfig
from pathlib import Path
from typing import List
import tempfile
import uuid

router = APIRouter(prefix="/api/documents", tags=["documents"])
processor = DocumentProcessor()

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = "general",
    tags: List[str] = []
):
    """Upload and process a document."""
    
    # Check file size
    max_size = DeploymentConfig.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {DeploymentConfig.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Save to temp file
    temp_dir = Path(tempfile.gettempdir())
    file_id = str(uuid.uuid4())
    file_path = temp_dir / f"{file_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # Process in background
    background_tasks.add_task(
        process_document_async,
        file_path, file.filename, category, tags, file_id
    )
    
    return {
        "message": "Document uploaded and processing started",
        "file_id": file_id,
        "filename": file.filename,
        "status": "processing",
        "processing_mode": DeploymentConfig.DEPLOYMENT_MODE.value
    }

async def process_document_async(
    file_path: Path, 
    filename: str, 
    category: str, 
    tags: List[str],
    file_id: str
):
    """Background task to process document."""
    try:
        result = await processor.process(file_path)
        
        if result['success']:
            # Store document with processing status
            await store_document(
                file_id=file_id,
                filename=filename,
                content=result['content'],
                metadata=result['metadata'],
                sections=result.get('sections', []),
                category=category,
                tags=tags,
                needs_full_processing=result.get('needs_full_processing', False),
                raw_file_path=str(file_path) if result.get('needs_full_processing') else None
            )
        else:
            await update_document_status(file_id, 'failed', result.get('error'))
    
    except Exception as e:
        await update_document_status(file_id, 'failed', str(e))
    finally:
        # Cleanup temp file (unless needed for sync)
        if not result.get('needs_full_processing'):
            file_path.unlink(missing_ok=True)
```

### 6. Sync Service for Document Processing

```python
# backend/services/document_sync.py

from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DocumentSyncService:
    """Handles syncing documents between cloud and local instances."""
    
    async def get_documents_needing_processing(self) -> List[Dict]:
        """Get documents uploaded to cloud that need full Docling processing."""
        # Query for documents with needs_full_processing = True
        documents = await db.fetch_all("""
            SELECT id, filename, raw_file_path, category, tags
            FROM documents 
            WHERE needs_full_processing = TRUE
            AND processing_status != 'processing'
        """)
        return documents
    
    async def sync_processed_document(self, document_id: str, processed_data: Dict):
        """Sync fully processed document data back to cloud."""
        await db.execute("""
            UPDATE documents 
            SET content = :content,
                metadata = :metadata,
                sections = :sections,
                needs_full_processing = FALSE,
                processing_status = 'completed',
                processed_at = :processed_at
            WHERE id = :document_id
        """, {
            'document_id': document_id,
            'content': processed_data['content'],
            'metadata': processed_data['metadata'],
            'sections': processed_data.get('sections', []),
            'processed_at': datetime.utcnow()
        })
        
        logger.info(f"Synced processed document {document_id}")
    
    async def pull_unprocessed_documents(self, cloud_url: str, api_key: str) -> List[Dict]:
        """Pull unprocessed documents from cloud to local instance."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{cloud_url}/api/sync/documents/unprocessed",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            return response.json()
    
    async def push_processed_documents(self, cloud_url: str, api_key: str, documents: List[Dict]):
        """Push locally processed documents back to cloud."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            for doc in documents:
                await client.post(
                    f"{cloud_url}/api/sync/documents/{doc['id']}/processed",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=doc
                )
```

## Docker Configuration

### Cloud Dockerfile (Lightweight)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Minimal system dependencies - NO Docling deps
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DEPLOYMENT_MODE=cloud

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Local Dockerfile (Full Docling)

```dockerfile
# backend/Dockerfile.local
FROM python:3.11-slim

WORKDIR /app

# Full system dependencies for Docling
RUN apt-get update && apt-get install -y \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-local.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-local.txt

COPY . .

ENV DEPLOYMENT_MODE=local

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Requirements Files

```text
# requirements.txt (cloud - lightweight)
fastapi>=0.109.0
uvicorn>=0.27.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
pydantic>=2.0.0
pymupdf>=1.23.0
sentence-transformers>=2.2.0
httpx>=0.26.0
```

```text
# requirements-local.txt (local - add Docling)
docling>=1.0.0
python-magic>=0.4.27
pdf2image>=1.16.3
```

## Sync Workflow

### Automatic Processing Pipeline

```text
1. User uploads document to CLOUD
   └─▶ Basic text extraction (PyMuPDF)
   └─▶ Document stored with needs_full_processing=True

2. LOCAL instance syncs (every 15 minutes)
   └─▶ Pulls unprocessed documents
   └─▶ Downloads raw files
   └─▶ Full Docling processing
   └─▶ Pushes processed content back to cloud

3. CLOUD receives processed content
   └─▶ Updates document with rich metadata
   └─▶ Creates enhanced embeddings
   └─▶ Sets needs_full_processing=False
```

## Frontend Integration

```svelte
<!-- frontend/src/lib/components/DocumentUpload.svelte -->
<script>
  import { onMount } from 'svelte';
  
  let file = null;
  let uploading = false;
  let status = '';
  let processingMode = '';
  
  async function handleUpload() {
    if (!file) return;
    
    uploading = true;
    status = 'Uploading...';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      processingMode = result.processing_mode;
      
      if (processingMode === 'cloud') {
        status = 'Uploaded. Basic processing complete. Full processing will occur on next local sync.';
      } else {
        status = 'Uploaded. Full processing in progress...';
      }
    } catch (error) {
      status = `Error: ${error.message}`;
    } finally {
      uploading = false;
    }
  }
</script>

<div class="upload-container">
  <input 
    type="file" 
    accept=".pdf,.docx,.pptx,.txt,.md"
    on:change={(e) => file = e.target.files[0]}
    disabled={uploading}
  />
  
  <button on:click={handleUpload} disabled={!file || uploading}>
    {uploading ? 'Uploading...' : 'Upload Document'}
  </button>
  
  {#if status}
    <p class="status">{status}</p>
  {/if}
  
  {#if processingMode === 'cloud'}
    <p class="info">
      ℹ️ You're using cloud mode. For full document analysis (OCR, Office docs, 
      structured sections), documents will be processed when a local instance syncs.
    </p>
  {/if}
</div>
```

## Summary

This hybrid approach provides:

1. **Free-tier compatibility**: Cloud deployment stays within 512MB RAM limit
2. **Full functionality locally**: Complete Docling processing on local instances
3. **Automatic sync**: Processed content flows back to cloud
4. **Graceful degradation**: Basic functionality always available in cloud
5. **User transparency**: UI indicates processing status and limitations
