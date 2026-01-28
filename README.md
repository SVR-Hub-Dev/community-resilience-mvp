# Community Resilience Reasoning Model MVP

An AI-powered system to help community coordinators prioritize disaster response actions using local community knowledge.

## Features

- **Knowledge Base**: Store community-specific disaster knowledge (flood patterns, vulnerable populations, resources)
- **Semantic Search**: Find relevant knowledge using vector similarity (pgvector)
- **AI Reasoning**: Generate prioritized action recommendations using LLM
- **Document Processing**: Upload and extract text from PDFs, Office documents, and more with hybrid cloud/local processing
- **Cloud-Local Sync**: Automatically sync documents between cloud and local instances for full Docling processing
- **Feedback Loop**: Collect user feedback to improve the system over time

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Ollama installed locally for LLM inference

### 1. Clone and Setup

```bash
cd community-resilience-mvp
cp .env.example .env
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:

- PostgreSQL with pgvector extension (port 5432)
- Ollama for local LLM inference (port 11434)
- FastAPI backend (port 8000)
- SvelteKit frontend (port 5173)

### 3. Pull LLM Model (if using Ollama)

```bash
docker exec community_resilience_ollama ollama pull llama3.2
```

### 4. Run Database Migrations

```bash
docker exec community_resilience_backend alembic upgrade head
```

### 5. Load Seed Data

```bash
docker exec community_resilience_backend python scripts/load_seed_data.py
```

### 6. Access the Application

- **Frontend**: <http://localhost:5173>
- **API Docs**: <http://localhost:8000/docs>
- **Health Check**: <http://localhost:8000/health>

## API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/query` | Submit situation, get prioritized recommendations |
| POST | `/ingest` | Add new knowledge entry |
| GET | `/knowledge` | List all knowledge entries |
| GET | `/knowledge/{id}` | Get specific knowledge entry |
| PUT | `/knowledge/{id}` | Update knowledge entry |
| DELETE | `/knowledge/{id}` | Delete knowledge entry |
| POST | `/feedback` | Submit feedback on recommendations |
| POST | `/events` | Ingest real-time events |
| GET | `/events` | List recent events |
| POST | `/assets` | Add community assets |
| GET | `/assets` | List community assets |
| POST | `/api/documents/upload` | Upload and process a document |
| GET | `/api/documents/{id}/status` | Get document processing status |
| GET | `/api/documents/processing/stats` | Get processing statistics |
| GET | `/api/sync/documents/unprocessed` | List documents needing local processing |
| POST | `/api/sync/documents/{id}/processed` | Submit processed content from local |
| GET | `/api/sync/pull` | Pull changes since timestamp |
| POST | `/api/sync/push` | Push processed documents from local |
| GET | `/api/sync/status` | Get sync status and statistics |
| GET | `/health` | Health check |

## Example Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"text": "Heavy rain, Riverside Street flooding, power out in the area"}'
```

Response:

```json
{
  "summary": "Heavy rainfall has caused flooding on Riverside Street with power outages affecting the area...",
  "actions": [
    {
      "priority": 1,
      "action": "Evacuate elderly residents from 45 Riverside Street to Hilltop Community Hall",
      "rationale": "Elderly residents often become isolated during floods and the hall has backup generator"
    },
    {
      "priority": 2,
      "action": "Contact SES for flood boat deployment",
      "rationale": "SES has 2 flood boats available for water rescues"
    }
  ],
  "retrieved_knowledge_ids": [1, 2, 7],
  "log_id": 1
}
```

## Document Processing

The application supports a hybrid cloud/local document processing architecture:

- **Cloud mode** (`DEPLOYMENT_MODE=cloud`): Uses PyMuPDF for basic PDF text extraction and direct reading of TXT/MD files. Office documents (.docx, .pptx, .xlsx) and scanned PDFs are queued for full processing by a local instance.
- **Local mode** (`DEPLOYMENT_MODE=local`): Uses [Docling](https://github.com/DS4SD/docling) for full document processing including OCR (Tesseract), Office document conversion (LibreOffice), structured section extraction, and table detection.

### Supported Formats

| Format | Cloud | Local |
| ------ | ----- | ----- |
| PDF (text-based) | Extracted | Extracted with sections |
| PDF (scanned) | Queued | OCR extraction |
| DOCX, DOC | Queued | Full extraction |
| PPTX, PPT | Queued | Full extraction |
| XLSX, XLS | Queued | Full extraction |
| TXT, MD | Extracted | Extracted |
| HTML | Queued | Full extraction |

### Sync Configuration

To enable cloud-local sync, configure these environment variables on the **local** instance:

```bash
SYNC_ENABLED=true
SYNC_SERVER_URL=https://your-cloud-backend.onrender.com
SYNC_API_KEY=your-shared-secret-key
SYNC_INTERVAL_MINUTES=15
```

The cloud instance needs the matching `SYNC_API_KEY`. Start the sync worker:

```bash
docker-compose -f docker-compose.local.yml --profile sync up -d
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions.

## Development

### Local Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Start PostgreSQL separately or use docker-compose up db
uvicorn app:app --reload
```

### Environment Variables

See `.env.example` for all configuration options:

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/community_resilience` |
| `LLM_PROVIDER` | LLM backend (`ollama` or `openai` or `groq`) | `ollama` |
| `LLM_MODEL` | Ollama model name | `llama3.2` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) | - |
| `GROQ_API_KEY` | Groq API key (if using Groq) | - |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `DEPLOYMENT_MODE` | Document processing mode (`cloud` or `local`) | `cloud` |
| `SYNC_ENABLED` | Enable cloud-local sync | `false` |
| `SYNC_SERVER_URL` | Cloud backend URL (for local sync) | - |
| `SYNC_API_KEY` | Shared secret for sync authentication | - |
| `SYNC_INTERVAL_MINUTES` | Minutes between sync cycles | `15` |

## Architecture

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   SvelteKit     │────▶│   FastAPI       │────▶│   PostgreSQL    │
│   Frontend      │     │   Backend       │     │   + pgvector    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   LLM (Ollama   │
                        │   or OpenAI)    │
                        └─────────────────┘
```

## Project Structure

```text
community-resilience-mvp/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── config.py           # Environment configuration
│   ├── db.py               # Database connection
│   ├── llm_client.py       # LLM wrapper
│   ├── models/
│   │   └── models.py       # SQLAlchemy models
│   ├── api/
│   │   ├── documents.py    # Document upload endpoints
│   │   └── sync.py         # Cloud-local sync endpoints
│   ├── services/
│   │   ├── embeddings.py   # Text embeddings
│   │   ├── retrieval.py    # Vector search
│   │   ├── reasoning.py    # LLM reasoning
│   │   ├── simple_extractor.py    # Cloud text extraction (PyMuPDF)
│   │   ├── docling_service.py     # Local full processing (Docling)
│   │   └── document_processor.py  # Processor factory
│   ├── tests/              # Unit, integration, and e2e tests
│   ├── alembic/            # Database migrations
│   ├── seed_data/          # Initial data
│   └── scripts/            # Utility scripts
├── frontend/
│   ├── src/
│   │   ├── routes/         # SvelteKit pages
│   │   ├── lib/            # Shared components and API client
│   │   └── app.css         # Global styles
│   ├── package.json
│   └── svelte.config.js
├── docs/                   # Documentation
├── docker-compose.yml
├── .env.example
└── README.md
```

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Cloud and local deployment instructions
- [Gap Analysis](docs/GAP-ANALYSIS.md) - Identified gaps and priorities
- [Implementation Plan](docs/IMPLEMENTATION-PLAN.md) - Detailed implementation guide
- [MVP Scope](docs/5.minimal-viable-prototype.md) - MVP definition
- [Docling Integration](docs/implementation/DOCLING_TODO.md) - Document processing implementation checklist

## License

MIT
