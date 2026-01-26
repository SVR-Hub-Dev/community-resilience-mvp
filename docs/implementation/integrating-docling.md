# Integrating Docling into the Community Resilience Hub Workflow

Docling is an excellent choice for document processing - it handles multiple formats (PDF, DOCX, PPTX, etc.) and can extract structured content. Here's how to integrate it into our hybrid architecture:

Docling Integration Architecture
Bash

Copy
┌─────────────────────────────────────────────────────────────┐
│                   DOCUMENT PROCESSING PIPELINE              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Document   │  │   Docling   │  │  Content Extraction │ │
│  │   Upload    │  │  Parser     │  │   & Chunking        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│         │               │                     │            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Embedding  │  │  Vector DB  │  │   Knowledge Graph   │ │
│  │  Generation │  │  Storage     │  │     Relations        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

## Implementation Strategy

### 1. Backend Service Integration

Add Docling as a document processing service in the FastAPI backend:

```Python
# backend/services/docling_service.py

import docling
from docling.document_converter import DocumentConverter
from typing import List, Dict, Optional
import asyncio
from pathlib import Path

class DoclingProcessor:
    def __init__(self):
        self.converter = DocumentConverter()

    async def process_document(self, file_path: Path) -> Dict:
        """Process document and extract structured content"""
        try:
            # Convert document to structured format
            result = await asyncio.to_thread(
                self.converter.convert, str(file_path)
            )
            
            return {
                'success': True,
                'content': self._extract_structured_content(result),
                'metadata': self._extract_metadata(result),
                'sections': self._extract_sections(result)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _extract_structured_content(self, result) -> str:
        """Extract main content as text"""
        return result.document.export_to_text()
    
    def _extract_metadata(self, result) -> Dict:
        """Extract document metadata"""
        doc = result.document
        return {
            'title': getattr(doc, 'title', ''),
            'author': getattr(doc, 'author', ''),
            'creation_date': getattr(doc, 'creation_date', ''),
            'page_count': len(doc.pages) if hasattr(doc, 'pages') else 0,
            'word_count': len(doc.export_to_text().split())
        }
    
    def _extract_sections(self, result) -> List[Dict]:
        """Extract document sections with hierarchy"""
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

### 2. Enhanced Document Upload Endpoint

Modify the document upload API to use Docling:

```Python
# backend/app/api/documents.py

from fastapi import UploadFile, File, BackgroundTasks
from services.docling_service import DoclingProcessor
from services.embedding_service import EmbeddingService
from models.document import DocumentCreate, DocumentStatus

docling_processor = DoclingProcessor()
embedding_service = EmbeddingService()

@app.post("/api/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = "general",
    tags: List[str] = []
):
    # Save uploaded file temporarily
    file_path = Path(f"/tmp/{file.filename}")
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Process document asynchronously
    background_tasks.add_task(
        process_document_async,
        file_path, file.filename, category, tags
    )
    
    return {
        "message": "Document uploaded and processing started",
        "filename": file.filename,
        "status": "processing"
    }

async def process_document_async(
    file_path: Path, filename: str, category: str, tags: List[str]
):
    """Background task to process document"""
    try:
        # Step 1: Process with Docling
        docling_result = await docling_processor.process_document(file_path)

        if not docling_result['success']:
            await update_document_status(filename, DocumentStatus.FAILED)
            return
        
        # Step 2: Create embeddings for searchable content
        chunks = chunk_content(docling_result['content'])
        embeddings = await embedding_service.create_embeddings(chunks)
        
        # Step 3: Store in database
        document_data = DocumentCreate(
            filename=filename,
            title=docling_result['metadata'].get('title', filename),
            content=docling_result['content'],
            metadata=docling_result['metadata'],
            category=category,
            tags=tags,
            embeddings=embeddings,
            sections=docling_result['sections']
        )
        
        document_id = await store_document(document_data)
        
        # Step 4: Update status
        await update_document_status(filename, DocumentStatus.PROCESSED, document_id)
        
    except Exception as e:
        await update_document_status(filename, DocumentStatus.FAILED)
        logger.error(f"Document processing failed: {e}")
    finally:
        # Cleanup temporary file
        file_path.unlink(missing_ok=True)
```

### 3. Content Chunking Strategy

```Python
# backend/services/chunking_service.py

import re
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter

class SmartChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def chunk_content(self, content: str, metadata: Dict) -> List[Dict]:
        """Chunk content intelligently based on document structure"""
        chunks = []
        
        # Use Docling sections if available
        if metadata.get('sections'):
            for section in metadata['sections']:
                section_chunks = self.splitter.split_text(section['content'])
                for i, chunk in enumerate(section_chunks):
                    chunks.append({
                        'content': chunk,
                        'section_title': section['title'],
                        'section_level': section['level'],
                        'chunk_index': i,
                        'metadata': {
                            'source': metadata.get('title', ''),
                            'page': section.get('page_numbers', [])[0] if section.get('page_numbers') else None
                        }
                    })
        else:
            # Fallback to simple chunking
            text_chunks = self.splitter.split_text(content)
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    'content': chunk,
                    'chunk_index': i,
                    'metadata': {
                        'source': metadata.get('title', ''),
                        'page': None
                    }
                })
        
        return chunks
```

### 4. Docker Configuration Updates

Update the Docker setup to include Docling dependencies:

```Dockerfile

# backend/Dockerfile (add these lines)

FROM python:3.11-slim

# Install system dependencies for Docling

RUN apt-get update && apt-get install -y \
    poppler-utils \      # For PDF processing
    tesseract-ocr \      # For OCR
    libtesseract-dev \   # OCR development files
    libreoffice \        # For Office documents
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add Docling to requirements.txt

# docling>=1.0.0

# python-magic>=0.4.27

# pdf2image>=1.16.3
```

### 5. Enhanced Document Search

```Python
# backend/services/search_service.py

class EnhancedSearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDatabase()

    async def semantic_search(self, query: str, filters: Dict = None) -> List[Dict]:
        """Enhanced search using document structure"""
        query_embedding = await self.embedding_service.create_embedding(query)
        
        # Search with section-based boosting
        results = await self.vector_db.similarity_search(
            query_embedding,
            filters=filters,
            boost_sections=True  # Boost matches in section titles
        )
        
        return self._format_search_results(results)
    
    async def search_by_section(self, query: str, section_title: str) -> List[Dict]:
        """Search within specific document sections"""
        # Create embedding for query + section context
        contextual_query = f"{section_title}: {query}"
        return await self.semantic_search(contextual_query)
```

### 6. Frontend Integration

Add document upload and processing status to the SvelteKit frontend:

```Svelte
  No file chosen handleUpload(e.target.files)}
    disabled={uploading}
  />
  
  {#if uploading}

  {/if}

Deployment Considerations
Cloud Deployment (Render)
Docling runs in the same container as the FastAPI app
No additional services needed
Free tier compatible
Local/Offline Deployment
Docling works completely offline
All document processing happens locally
No external dependencies for parsing
Sync Strategy for Documents
Python

Copy

# backend/services/sync_service.py

class DocumentSyncService:
    async def sync_documents(self, local_instance_id: UUID, last_sync: datetime):
        """Sync documents between cloud and local instances"""
        # Push local document changes to cloud
        local_changes = await self.get_local_changes_since(last_sync)
        await self.push_to_cloud(local_changes, local_instance_id)

        # Pull cloud changes to local
        cloud_changes = await self.pull_from_cloud(last_sync)
        await self.apply_cloud_changes(cloud_changes)
        
        # Handle conflicts
        conflicts = await self.detect_conflicts(local_changes, cloud_changes)
        if conflicts:
            await self.resolve_conflicts(conflicts)
Benefits of This Integration
Multi-format Support: Handle PDFs, Word docs, PowerPoint, etc.
Structured Extraction: Preserve document hierarchy and metadata
Offline Capable: Works without internet connection
Enhanced Search: Better semantic search with document structure
Automated Processing: Background processing with status tracking
This integration makes the resilience hub much more powerful for handling real-world documents like emergency plans, government guidelines, and community resources in their native formats.
