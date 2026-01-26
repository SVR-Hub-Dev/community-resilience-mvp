# Implementation Plan: Community Resilience Reasoning Model MVP

This document provides a detailed, actionable implementation plan addressing the gaps identified in [GAP-ANALYSIS.md](GAP-ANALYSIS.md).

---

## Overview

### Goal

Build a functional MVP that allows community coordinators to:

1. Input a disaster situation description
2. Retrieve relevant community knowledge
3. Receive prioritized, actionable recommendations
4. Provide feedback to improve the system

### Tech Stack

| Component | Technology | Rationale |
| --- | --- | --- |
| Frontend | SvelteKit | Fast, modern, good DX |
| Backend | Python + FastAPI | Async, auto-docs, Pydantic |
| Database | PostgreSQL + pgvector | Vector search built-in |
| Embeddings | all-MiniLM-L6-v2 (384-dim) | Free, local, fast |
| LLM | Ollama (local) or OpenAI API | Flexible deployment |
| Containerization | Docker Compose | Reproducible dev environment |

---

## Project Structure

```text
community-resilience-mvp/
├── backend/
│   ├── app.py                 # FastAPI application entry point
│   ├── config.py              # Environment configuration
│   ├── db.py                  # Database connection and session
│   ├── llm_client.py          # LLM wrapper (Ollama/OpenAI)
│   ├── models/
│   │   └── models.py          # SQLAlchemy ORM models
│   ├── services/
│   │   ├── embeddings.py      # Text embedding service
│   │   ├── retrieval.py       # Vector similarity search
│   │   └── reasoning.py       # LLM reasoning service
│   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial.py
│   ├── seed_data/
│   │   └── knowledge.json     # Initial community knowledge
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte
│   │   │   ├── +page.ts
│   │   │   ├── admin/
│   │   │   │   ├── +page.svelte
│   │   │   │   └── +page.ts
│   │   │   └── api/
│   │   │       ├── query/+server.ts
│   │   │       ├── knowledge/+server.ts
│   │   │       └── feedback/+server.ts
│   │   └── lib/
│   │       └── api.ts
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
└── docs/
    ├── GAP-ANALYSIS.md
    └── IMPLEMENTATION-PLAN.md
```

---

## Phase 1: Make It Run (Critical)

### Task 1.1: Environment Configuration

**Files to create:**

#### `.env.example`

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/community_resilience
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=community_resilience

# LLM Configuration
LLM_PROVIDER=ollama           # Options: ollama, openai
LLM_MODEL=llama3.2            # For Ollama
OPENAI_API_KEY=               # For OpenAI (if used)
OPENAI_MODEL=gpt-4o-mini      # For OpenAI (if used)

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Frontend
VITE_API_URL=http://localhost:8000
```

#### `backend/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/community_resilience"

    # LLM
    llm_provider: Literal["ollama", "openai"] = "ollama"
    llm_model: str = "llama3.2"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
```

---

### Task 1.2: Database Connection

#### `backend/db.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Session:
    """Context manager for non-FastAPI usage."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

### Task 1.3: Fix Embedding Dimensions

Update SQLAlchemy models to use 384 dimensions (matching all-MiniLM-L6-v2).

#### `backend/models/models.py`

```python
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ARRAY
)
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

from config import settings

Base = declarative_base()

EMBEDDING_DIM = settings.embedding_dimension  # 384


class CommunityKnowledge(Base):
    __tablename__ = "community_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    tags = Column(ARRAY(String))
    location = Column(String)
    hazard_type = Column(String)
    source = Column(String)
    embedding = Column(Vector(EMBEDDING_DIM))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CommunityEvent(Base):
    __tablename__ = "community_event"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String)
    severity = Column(Integer)
    reported_by = Column(String)
    embedding = Column(Vector(EMBEDDING_DIM))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class CommunityAsset(Base):
    __tablename__ = "community_asset"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    asset_type = Column(String, nullable=False)
    description = Column(Text)
    location = Column(String)
    capacity = Column(Integer)
    status = Column(String)
    tags = Column(ARRAY(String))
    embedding = Column(Vector(EMBEDDING_DIM))
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelFeedbackLog(Base):
    __tablename__ = "model_feedback_log"

    id = Column(Integer, primary_key=True, index=True)
    user_input = Column(Text, nullable=False)
    retrieved_knowledge_ids = Column(ARRAY(Integer))
    retrieved_asset_ids = Column(ARRAY(Integer))
    model_output = Column(Text, nullable=False)
    rating = Column(Integer)
    comments = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
```

---

### Task 1.4: LLM Client Implementation

#### `backend/llm_client.py`

```python
import json
import httpx
from typing import Optional
from config import settings


class LLMClient:
    """Unified LLM client supporting Ollama and OpenAI."""

    def __init__(self):
        self.provider = settings.llm_provider
        self.model = (
            settings.llm_model if self.provider == "ollama"
            else settings.openai_model
        )

    async def generate(self, prompt: str, timeout: float = 60.0) -> str:
        """Generate a response from the LLM."""
        if self.provider == "ollama":
            return await self._generate_ollama(prompt, timeout)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, timeout)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _generate_ollama(self, prompt: str, timeout: float) -> str:
        """Generate using Ollama API."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def _generate_openai(self, prompt: str, timeout: float) -> str:
        """Generate using OpenAI API."""
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


# Singleton instance
llm = LLMClient()
```

---

### Task 1.5: Docker Compose

#### `docker-compose.yml`

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    container_name: community_resilience_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-community_resilience}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    container_name: community_resilience_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # Pull the model on first run:
    # docker exec community_resilience_ollama ollama pull llama3.2

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: community_resilience_backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@db:5432/${POSTGRES_DB:-community_resilience}
      LLM_PROVIDER: ${LLM_PROVIDER:-ollama}
      LLM_MODEL: ${LLM_MODEL:-llama3.2}
      OLLAMA_BASE_URL: http://ollama:11434
    depends_on:
      db:
        condition: service_healthy
      ollama:
        condition: service_started
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: community_resilience_frontend
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  pgdata:
  ollama_data:
```

---

### Task 1.6: Alembic Migrations

#### `backend/alembic/versions/001_initial.py`

```python
"""Initial migration - create core tables

Revision ID: 001
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # community_knowledge
    op.create_table(
        'community_knowledge',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tags', sa.ARRAY(sa.String())),
        sa.Column('location', sa.String()),
        sa.Column('hazard_type', sa.String()),
        sa.Column('source', sa.String()),
        sa.Column('embedding', Vector(EMBEDDING_DIM)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('ix_community_knowledge_id', 'community_knowledge', ['id'])

    # community_event
    op.create_table(
        'community_event',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('location', sa.String()),
        sa.Column('severity', sa.Integer()),
        sa.Column('reported_by', sa.String()),
        sa.Column('embedding', Vector(EMBEDDING_DIM)),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('ix_community_event_id', 'community_event', ['id'])

    # community_asset
    op.create_table(
        'community_asset',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('asset_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('location', sa.String()),
        sa.Column('capacity', sa.Integer()),
        sa.Column('status', sa.String()),
        sa.Column('tags', sa.ARRAY(sa.String())),
        sa.Column('embedding', Vector(EMBEDDING_DIM)),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('ix_community_asset_id', 'community_asset', ['id'])

    # model_feedback_log
    op.create_table(
        'model_feedback_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_input', sa.Text(), nullable=False),
        sa.Column('retrieved_knowledge_ids', sa.ARRAY(sa.Integer())),
        sa.Column('retrieved_asset_ids', sa.ARRAY(sa.Integer())),
        sa.Column('model_output', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer()),
        sa.Column('comments', sa.Text()),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    op.create_index('ix_model_feedback_log_id', 'model_feedback_log', ['id'])


def downgrade() -> None:
    op.drop_table('model_feedback_log')
    op.drop_table('community_asset')
    op.drop_table('community_event')
    op.drop_table('community_knowledge')
```

---

### Task 1.7: Requirements

#### `backend/requirements.txt`

```text
# Web framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.9
alembic>=1.13.0
pgvector>=0.2.4

# Embeddings
sentence-transformers>=2.2.0

# HTTP client
httpx>=0.26.0

# Configuration
pydantic-settings>=2.1.0
python-dotenv>=1.0.0

# Utilities
python-multipart>=0.0.6
```

---

## Phase 2: Make It Usable (High)

### Task 2.1: Seed Data

#### `backend/seed_data/knowledge.json`

```json
[
  {
    "title": "Riverside Street Flooding Pattern",
    "description": "Riverside Street floods after heavy rain above 100mm. The low-lying section between Oak Avenue and Pine Street becomes impassable within 2 hours of sustained rainfall. Elderly residents in the apartment complex at 45 Riverside often become isolated and require evacuation assistance.",
    "tags": ["flood", "elderly", "evacuation", "road-closure"],
    "location": "Riverside Street",
    "hazard_type": "flood",
    "source": "Community workshop 2023"
  },
  {
    "title": "Hilltop Community Hall - Emergency Shelter",
    "description": "Hilltop Community Hall on Hilltop Road serves as the primary emergency shelter. Capacity of 120 people. Has backup generator, accessible toilets, and basic medical supplies. Kitchen facilities available. Keys held by Martha Chen (0412-XXX-XXX) and the council.",
    "tags": ["shelter", "generator", "accessible", "medical"],
    "location": "Hilltop Road",
    "hazard_type": "flood",
    "source": "Emergency planning committee"
  },
  {
    "title": "Miller Bridge Closure History",
    "description": "Miller Bridge over Willow Creek closes when water reaches the 2.5m marker on the upstream pylon. During the 2019 flood, the bridge was closed for 3 days. Alternative route via Highway 7 adds 25 minutes to travel time. School buses cannot use the alternative route.",
    "tags": ["bridge", "road-closure", "transport", "school"],
    "location": "Miller Bridge, Willow Creek",
    "hazard_type": "flood",
    "source": "Council records"
  },
  {
    "title": "Sunrise Aged Care - Vulnerable Population",
    "description": "Sunrise Aged Care facility houses 45 residents, 12 of whom require oxygen equipment. Located in flood-prone zone. Evacuation requires 4 hours minimum and 3 accessible vehicles. Contact: Director James Okonkwo (0423-XXX-XXX). Has mutual aid agreement with Hilltop Community Hall.",
    "tags": ["aged-care", "medical", "evacuation", "oxygen"],
    "location": "23 Sunrise Avenue",
    "hazard_type": "flood",
    "source": "Emergency services liaison"
  },
  {
    "title": "Local SES Contact and Capabilities",
    "description": "Local SES unit based at 15 Industrial Drive. Has 2 flood boats, sandbag supplies, and 12 active volunteers. Response time averages 45 minutes. Contact: Unit Commander Sarah Kim (0434-XXX-XXX). Busiest during flood events - prioritize requests.",
    "tags": ["SES", "emergency-services", "boats", "sandbags"],
    "location": "15 Industrial Drive",
    "hazard_type": "flood",
    "source": "SES briefing"
  },
  {
    "title": "Willow Creek Early Warning Signs",
    "description": "When Willow Creek reaches 1.8m at the town gauge, flooding of low-lying areas is imminent (typically 4-6 hours). Local knowledge: watch for debris buildup at the old railway bridge - when debris appears, water is rising fast upstream.",
    "tags": ["early-warning", "creek", "monitoring"],
    "location": "Willow Creek",
    "hazard_type": "flood",
    "source": "Elder interview - Tom Nguyen"
  },
  {
    "title": "Power Outage Pattern",
    "description": "Substation on Creek Road floods at 2.2m creek level, causing power outages to Riverside, Oak, and Pine Street areas. Typical restoration time is 8-12 hours after floodwaters recede. Residents with medical equipment should evacuate early.",
    "tags": ["power", "electricity", "medical", "infrastructure"],
    "location": "Creek Road Substation",
    "hazard_type": "flood",
    "source": "Power company liaison"
  },
  {
    "title": "St. Mary's Church - Secondary Shelter",
    "description": "St. Mary's Church on Church Street can serve as overflow shelter for 60 people. No generator but has gas cooking. Accessible entry via side ramp. Contact: Pastor David (0445-XXX-XXX). Often used for families with young children.",
    "tags": ["shelter", "church", "families", "children"],
    "location": "Church Street",
    "hazard_type": "flood",
    "source": "Community workshop 2023"
  },
  {
    "title": "Medication Access During Emergencies",
    "description": "Riverside Pharmacy at 12 Main Street stays open during emergencies when safe. Pharmacist Jenny maintains list of residents with critical medications. Has emergency medication dispensing agreement with hospital. Contact: 0456-XXX-XXX.",
    "tags": ["pharmacy", "medication", "medical", "health"],
    "location": "12 Main Street",
    "hazard_type": "flood",
    "source": "Health services network"
  },
  {
    "title": "Pet-Friendly Evacuation",
    "description": "Agricultural showgrounds on Farm Road accepts evacuees with pets. Open paddock space for large animals. Small animal crates available. Managed by agricultural society volunteers. Coordinate with SES for pet transport if needed.",
    "tags": ["pets", "animals", "evacuation", "livestock"],
    "location": "Farm Road Showgrounds",
    "hazard_type": "flood",
    "source": "Agricultural society"
  },
  {
    "title": "Communication Backup - Radio Network",
    "description": "When mobile networks fail, tune to local FM 98.5 for emergency broadcasts. Amateur radio operators active on 146.5 MHz. Radio base station at SES headquarters. Community Facebook group 'Rivertown Emergency Updates' moderated by council.",
    "tags": ["communication", "radio", "emergency-broadcast"],
    "location": "Town-wide",
    "hazard_type": "flood",
    "source": "Communications plan"
  },
  {
    "title": "School Evacuation Protocol",
    "description": "Rivertown Primary and High School have coordinated evacuation protocols. Buses pre-positioned during flood warnings. Children can be collected from Hilltop Community Hall if schools close early. Parents notified via SMS and school app.",
    "tags": ["school", "children", "evacuation", "transport"],
    "location": "School precinct",
    "hazard_type": "flood",
    "source": "School emergency plan"
  },
  {
    "title": "Sandbagging Locations",
    "description": "Sandbags available at: SES HQ (15 Industrial Drive), Council depot (8 Works Road), and Fire station. Self-fill sand at council depot. Pre-filled bags limited - priority for elderly and disabled residents. Request early during flood warnings.",
    "tags": ["sandbags", "flood-protection", "supplies"],
    "location": "Multiple locations",
    "hazard_type": "flood",
    "source": "Council emergency plan"
  },
  {
    "title": "Historic Flood Levels",
    "description": "Major floods: 1974 (3.2m), 1998 (2.8m), 2019 (2.6m). At 2.4m: Riverside Street floods. At 2.6m: Miller Bridge closes, power outages begin. At 2.8m: Main Street shops affected. At 3.0m: Hospital goes to emergency power only.",
    "tags": ["history", "flood-levels", "reference"],
    "location": "Town gauge at Willow Creek",
    "hazard_type": "flood",
    "source": "Historical records"
  },
  {
    "title": "Disability Support Network",
    "description": "Local disability support coordinator: Maria Santos (0467-XXX-XXX). Maintains register of residents needing evacuation assistance. Coordinates with SES for accessible transport. Priority notification list for power outages affecting medical equipment.",
    "tags": ["disability", "accessibility", "evacuation", "medical"],
    "location": "Town-wide",
    "hazard_type": "flood",
    "source": "Disability services"
  },
  {
    "title": "Food and Water Distribution",
    "description": "During extended emergencies, food distribution coordinated from Hilltop Community Hall. Red Cross volunteers activate after 24 hours. Bottled water supplies at council depot. Lions Club operates BBQ for hot meals. Dietary requirements should be communicated to shelter managers.",
    "tags": ["food", "water", "supplies", "volunteers"],
    "location": "Hilltop Community Hall",
    "hazard_type": "flood",
    "source": "Emergency planning committee"
  },
  {
    "title": "Road Closure Sequence",
    "description": "Typical road closure order during rising floods: 1) Riverside Street, 2) Creek Road, 3) Miller Bridge, 4) Low sections of Oak Avenue. Council updates road closure signs but local knowledge is faster - check Facebook group for real-time updates.",
    "tags": ["roads", "closures", "transport", "sequence"],
    "location": "Multiple roads",
    "hazard_type": "flood",
    "source": "Council roads department"
  },
  {
    "title": "Post-Flood Cleanup Coordination",
    "description": "After floods recede, cleanup coordinated from council depot. Green waste collection prioritized. Council provides free skip bins for flood-damaged materials. Volunteers register through SES. Mud army typically mobilizes within 48 hours.",
    "tags": ["cleanup", "recovery", "waste", "volunteers"],
    "location": "Council depot, 8 Works Road",
    "hazard_type": "flood",
    "source": "Recovery plan"
  },
  {
    "title": "Insurance and Financial Assistance",
    "description": "Financial counselor available through community center post-disaster. Emergency relief payments through Centrelink - claim online or at recovery center. Council coordinates with insurance assessors. Document damage with photos before cleanup.",
    "tags": ["insurance", "financial", "recovery", "assistance"],
    "location": "Community center",
    "hazard_type": "flood",
    "source": "Recovery services"
  },
  {
    "title": "Mental Health Support",
    "description": "Post-flood counseling available through community health center. Peer support group 'Flood Recovery Circle' meets Thursdays at St. Mary's. Children's trauma support through school counselors. 24/7 crisis line: 13 11 14.",
    "tags": ["mental-health", "counseling", "support", "recovery"],
    "location": "Community health center",
    "hazard_type": "flood",
    "source": "Health services"
  }
]
```

---

### Task 2.2: Seed Data Loader Script

#### `backend/scripts/load_seed_data.py`

```python
"""Load seed data into the database."""
import json
from pathlib import Path

from db import get_db_session
from models.models import CommunityKnowledge
from services.embeddings import embed_text


def load_seed_data():
    seed_file = Path(__file__).parent.parent / "seed_data" / "knowledge.json"

    with open(seed_file) as f:
        entries = json.load(f)

    with get_db_session() as db:
        existing_count = db.query(CommunityKnowledge).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} entries. Skipping seed.")
            return

        for entry in entries:
            embedding = embed_text(entry["description"])

            knowledge = CommunityKnowledge(
                title=entry["title"],
                description=entry["description"],
                tags=entry.get("tags", []),
                location=entry.get("location"),
                hazard_type=entry.get("hazard_type"),
                source=entry.get("source"),
                embedding=embedding
            )
            db.add(knowledge)

        db.commit()
        print(f"Loaded {len(entries)} knowledge entries.")


if __name__ == "__main__":
    load_seed_data()
```

---

### Task 2.3: README

#### `README.md`

```markdown
# Community Resilience Reasoning Model MVP

An AI-powered system to help community coordinators prioritize disaster response actions using local community knowledge.

## Features

- **Knowledge Base**: Store community-specific disaster knowledge (flood patterns, vulnerable populations, resources)
- **Semantic Search**: Find relevant knowledge using vector similarity
- **AI Reasoning**: Generate prioritized action recommendations using LLM
- **Feedback Loop**: Collect user feedback to improve the system

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Ollama installed locally for LLM

### 1. Clone and Setup

```bash
git clone <repo-url>
cd community-resilience-mvp
cp .env.example .env
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Pull LLM Model (if using Ollama)

```bash
docker exec community_resilience_ollama ollama pull llama3.2
```

### 4. Run Migrations

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
- **Admin UI**: <http://localhost:5173/admin>

## Usage

1. Open the web interface at <http://localhost:5173>
2. Describe a disaster situation (e.g., "Heavy rain, Riverside Street flooding, power out")
3. Review the prioritized recommendations
4. Provide feedback to help improve the system

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

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

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | /query | Submit situation, get recommendations |
| POST | /ingest | Add new knowledge entry |
| GET | /knowledge | List all knowledge entries |
| POST | /feedback | Submit feedback on recommendations |

## Configuration

See `.env.example` for all configuration options.

## License

MIT

---

## Phase 3: Make It Better (Medium)

### Task 3.1: Error Handling Improvements

Add to `backend/services/reasoning.py`:

```python
import asyncio
from typing import Dict, List, Optional
import json
import logging

from models.models import CommunityKnowledge
from llm_client import llm

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 8000  # Approximate token limit safety margin
MAX_RETRIES = 2
TIMEOUT_SECONDS = 60


async def run_reasoning_model(
    user_input: str,
    context_entries: List[CommunityKnowledge]
) -> Dict:
    """
    Main reasoning function with error handling and retries.
    """
    context_text = format_context(context_entries)

    # Truncate context if too long
    if len(context_text) > MAX_CONTEXT_CHARS:
        context_text = truncate_context(context_text, MAX_CONTEXT_CHARS)
        logger.warning("Context truncated due to length")

    prompt = build_prompt(user_input, context_text)

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await asyncio.wait_for(
                llm.generate(prompt),
                timeout=TIMEOUT_SECONDS
            )
            return parse_response(response)

        except asyncio.TimeoutError:
            logger.error(f"LLM timeout on attempt {attempt + 1}")
            if attempt == MAX_RETRIES:
                return error_response("The system is taking too long to respond. Please try again.")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            if attempt == MAX_RETRIES:
                return error_response("Unable to parse the response. Please try rephrasing your query.")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            if attempt == MAX_RETRIES:
                return error_response("An unexpected error occurred. Please try again later.")

    return error_response("Unable to generate recommendations.")


def truncate_context(context: str, max_chars: int) -> str:
    """Truncate context to fit within limits, preserving complete entries."""
    if len(context) <= max_chars:
        return context

    entries = context.split("\n\n")
    truncated = []
    current_length = 0

    for entry in entries:
        if current_length + len(entry) + 2 > max_chars:
            break
        truncated.append(entry)
        current_length += len(entry) + 2

    return "\n\n".join(truncated)


def error_response(message: str) -> Dict:
    """Return a structured error response."""
    return {
        "summary": message,
        "actions": [],
        "error": True
    }


def parse_response(response: str) -> Dict:
    """Parse LLM response with fallback handling."""
    try:
        data = json.loads(response)
        # Validate expected structure
        if "summary" not in data:
            data["summary"] = "Response received but format was unexpected."
        if "actions" not in data:
            data["actions"] = []
        return data
    except json.JSONDecodeError:
        # Attempt to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
        raise
```

---

## Implementation Checklist

### Phase 1: Make It Run

- [ ] Create `.env.example`
- [ ] Create `backend/config.py`
- [ ] Create `backend/db.py`
- [ ] Update `backend/models/models.py` (384-dim embeddings)
- [ ] Create `backend/llm_client.py`
- [ ] Create `docker-compose.yml`
- [ ] Create `backend/alembic/` structure
- [ ] Create initial migration
- [ ] Create `backend/requirements.txt`
- [ ] Create `backend/Dockerfile`
- [ ] Create `frontend/Dockerfile`

### Phase 2: Make It Usable

- [ ] Create `backend/seed_data/knowledge.json`
- [ ] Create `backend/scripts/load_seed_data.py`
- [ ] Create `README.md`
- [ ] Test end-to-end flow
- [ ] Add basic API key authentication (optional for MVP)

### Phase 3: Make It Better

- [ ] Improve error handling in reasoning service
- [ ] Add context truncation
- [ ] Add retry logic
- [ ] Add logging throughout
- [ ] Add input validation with Pydantic

---

## Decision Log

### Embedding Model: all-MiniLM-L6-v2 (384 dimensions)

**Chosen over OpenAI embeddings (1536 dimensions) because:**

- Free and runs locally
- Fast inference
- No API costs
- Works offline
- Sufficient quality for MVP semantic search

**Trade-off:** Slightly lower embedding quality than OpenAI, but acceptable for MVP.

### LLM: Ollama (default) with OpenAI fallback

**Rationale:**

- Ollama allows fully local deployment (privacy, offline capability)
- OpenAI option available for higher quality when needed
- Easy to switch via environment variable

### Database: PostgreSQL + pgvector

**Rationale:**

- Single database for both structured data and vector search
- pgvector is mature and performant
- Avoids complexity of separate vector DB
- Easy local development with Docker

---

## Next Steps After Implementation

1. **User Testing**: Get feedback from actual community coordinators
2. **Prompt Iteration**: Refine prompts based on output quality
3. **Knowledge Expansion**: Add more community-specific entries
4. **Authentication**: Add proper user authentication for production
5. **Monitoring**: Add observability (logging, metrics, error tracking)
