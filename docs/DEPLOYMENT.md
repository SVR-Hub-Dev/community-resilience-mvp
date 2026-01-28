# Deployment Guide

This guide covers deploying the Community Resilience MVP to cloud providers using the free tier.

## Architecture Overview

| Component | Local Development | Cloud Deployment |
| --------- | ----------------- | ---------------- |
| Frontend | Vite dev server (port 5173) | Vercel |
| Backend | Docker/uvicorn (port 8000) | Render |
| Database | Docker PostgreSQL | Neon |
| LLM | Ollama (local) | Groq API |
| Document Processing | Full Docling | Basic text extraction |

### Document Processing Strategy

Due to Render free tier memory constraints (512MB), document processing uses a hybrid approach:

| Feature | Cloud (Free Tier) | Local Instance |
| -------- | ----------------- | -------------- |
| PDF text extraction | ✅ PyMuPDF | ✅ Docling |
| Office documents (.docx, .pptx) | ❌ Queued for local | ✅ Docling |
| OCR (scanned PDFs) | ❌ Queued for local | ✅ Tesseract |
| Structured section extraction | ❌ Basic only | ✅ Full |
| Table extraction | ❌ Not available | ✅ Docling |
| Metadata extraction | Basic (filename, size) | Full (author, sections, pages) |

**Cloud mode** uses `SimpleTextExtractor` (PyMuPDF for PDFs, direct read for TXT/MD). Documents that need OCR or Office conversion are marked `needs_full_processing=True` with status `NEEDS_LOCAL`. These queue up for sync.

**Local mode** uses `DoclingProcessor` which wraps the [Docling](https://github.com/DS4SD/docling) library for full document conversion including OCR (Tesseract), Office document conversion (LibreOffice), structured section extraction, and table/image detection.

**Sync cycle**: A local instance with sync enabled periodically pulls unprocessed documents from cloud, processes them with Docling, and pushes the results back. This is handled by the sync worker service.

---

## Prerequisites

- GitHub account (for deployment integrations)
- [Neon](https://neon.tech) account (free)
- [Groq](https://console.groq.com) account (free)
- [Render](https://render.com) account (free)
- [Vercel](https://vercel.com) account (free)

---

## Step 1: Set Up Neon Database

Neon provides serverless PostgreSQL with pgvector support on the free tier.

### 1.1 Create a Neon Project

1. Go to [Neon Console](https://console.neon.tech)
2. Click **Create Project**
3. Name it `community-resilience`
4. Select a region close to your users (e.g., `us-east-2`)
5. Click **Create Project**

### 1.2 Enable pgvector Extension

1. In your Neon project, go to **SQL Editor**
2. Run the following SQL:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 1.3 Get Connection String

1. Go to **Dashboard** > **Connection Details**
2. Copy the connection string (it looks like):

   ```text
   postgresql://user:password@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

3. Replace `neondb` with `community_resilience` in the connection string

### 1.4 Run Migrations

You'll need to run Alembic migrations against Neon. From your local machine:

```bash
cd backend

# Set the DATABASE_URL to your Neon connection string
export DATABASE_URL="postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/community_resilience?sslmode=require"

# Run migrations
alembic upgrade head

# Load seed data
python scripts/load_seed_data.py
```

---

## Step 2: Get Groq API Key

Groq provides fast, free LLM inference.

1. Go to [Groq Console](https://console.groq.com)
2. Sign up or log in
3. Go to **API Keys**
4. Click **Create API Key**
5. Copy and save the key (starts with `gsk_`)

---

## Step 3: Deploy Backend to Render

### 3.1 Connect Repository

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** > **Blueprint**
3. Connect your GitHub repository
4. Render will detect the `render.yaml` file

### 3.2 Configure Environment Variables

In the Render dashboard, set these environment variables:

| Variable | Value |
| -------- | ----- |
| `DATABASE_URL` | Your Neon connection string |
| `GROQ_API_KEY` | Your Groq API key |
| `LLM_PROVIDER` | `groq` |
| `DEPLOYMENT_MODE` | `cloud` |
| `SYNC_API_KEY` | Generate a secure key for sync authentication |

### 3.3 Deploy

1. Click **Apply** to deploy
2. Wait for the build to complete
3. Note your Render URL (e.g., `https://community-resilience-api.onrender.com`)

### 3.4 Verify Deployment

```bash
curl https://community-resilience-api.onrender.com/health
```

Should return:

```json
{"status": "healthy", "database": true, "llm": true, "deployment_mode": "cloud"}
```

---

## Step 4: Deploy Frontend to Vercel

### 4.1 Connect Repository

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Add New** > **Project**
3. Import your GitHub repository
4. Configure the project:
   - **Framework Preset**: SvelteKit
   - **Root Directory**: `frontend`

### 4.2 Configure Environment Variables

Add this environment variable in Vercel:

| Variable | Value |
| -------- | ----- |
| `VITE_API_URL` | Your Render backend URL (e.g., `https://community-resilience-api.onrender.com`) |

### 4.3 Deploy

1. Click **Deploy**
2. Wait for the build to complete
3. Your frontend is now live at the Vercel URL

---

## Step 5: Test the Deployment

1. Open your Vercel frontend URL
2. Navigate to the **Query** page
3. Enter a test query like:

   ```text
   Heavy rain expected, Riverside Street flooding, power out
   ```

4. Verify you get AI-generated recommendations

---

## Step 6: Deploy Local Instance (Optional)

For full offline capability and complete document processing, deploy a local instance.

### 6.1 Prerequisites

- Docker and Docker Compose installed
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

### 6.2 Configure Environment

Create a `.env.local` file:

```bash
# .env.local
DEPLOYMENT_MODE=local
DATABASE_URL=postgresql://postgres:postgres@database:5432/community_resilience
OLLAMA_URL=http://ollama:11434
LLM_PROVIDER=ollama

# Sync configuration (optional - for cloud sync)
SYNC_ENABLED=true
SYNC_SERVER_URL=https://your-render-url.onrender.com
SYNC_API_KEY=your-sync-api-key
SYNC_INTERVAL_MINUTES=15
```

### 6.3 Start Local Instance

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# Wait for services to initialize (first run downloads Ollama models)
sleep 60

# Run migrations
docker exec community-resilience-backend alembic upgrade head

# Verify
curl http://localhost:8000/health
```

### 6.4 Access Local Instance

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- Ollama: <http://localhost:11434>

---

## Troubleshooting

### Backend Cold Starts

Render's free tier spins down after 15 minutes of inactivity. The first request after inactivity may take 30-50 seconds. This is normal for the free tier.

**Solutions:**

- Upgrade to Render's paid tier ($7/month) for always-on
- Use a cron job to ping the health endpoint every 10 minutes
- Accept the cold start delay for demo/development use

### Database Connection Issues

If you see database connection errors:

1. Verify your `DATABASE_URL` includes `?sslmode=require`
2. Check that pgvector extension is enabled
3. Ensure migrations have been run against Neon

### CORS Errors

If you see CORS errors in the browser console:

1. Verify `VITE_API_URL` is set correctly in Vercel
2. Check that the backend CORS configuration includes your Vercel domain

Add your Vercel domain to `backend/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://your-app.vercel.app",  # Add your Vercel URL
    ],
    ...
)
```

### Groq Rate Limits

Groq's free tier has generous rate limits, but if you hit them:

1. Wait a few minutes and retry
2. Consider switching to a smaller model (`llama-3.1-8b-instant`)
3. Upgrade to Groq's paid tier if needed

### Document Processing Issues

**Office documents not processing in cloud:**
This is expected. Office documents (.docx, .pptx, .xlsx) require LibreOffice which exceeds free tier memory limits. These documents are marked with `processing_status=needs_local` and queued for processing by local instances.

**Solutions:**

- Deploy a local instance to process queued documents
- Convert documents to PDF before uploading
- Upgrade to Render Starter tier ($7/month) for 2GB RAM

**OCR not working in cloud:**
Scanned PDFs require Tesseract OCR which is only available on local instances. The cloud extractor detects low-text PDFs (less than 10% of pages have text, or fewer than 100 characters total) and marks them as `needs_full_processing`.

**Document stuck in "processing" status:**
If a document remains in `processing` status, the sync worker may have crashed during processing.

**Solutions:**

1. Check sync worker logs: `docker logs community-resilience-sync-worker`
2. Restart the sync worker: `docker-compose -f docker-compose.local.yml --profile sync restart sync-worker`
3. Manually mark the document as failed via the API and re-upload

**Sync not pulling documents:**
If the local instance is not pulling unprocessed documents from cloud:

1. Verify `SYNC_ENABLED=true` in your `.env.local`
2. Verify `SYNC_SERVER_URL` points to your Render backend URL
3. Verify `SYNC_API_KEY` matches the key configured on the cloud instance
4. Check sync status: `curl -H "X-Sync-API-Key: YOUR_KEY" http://localhost:8000/api/sync/status`

**Upload rejected with "File type not supported":**
Supported file types depend on deployment mode. In cloud mode only `.pdf`, `.txt`, and `.md` are directly processed. Other formats are accepted but queued for local processing. Check `GET /api/documents/processing/stats` for current capabilities.

---

## Environment Variables Reference

### Backend (Render - Cloud)

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string |
| `LLM_PROVIDER` | Yes | Set to `groq` |
| `GROQ_API_KEY` | Yes | Groq API key |
| `GROQ_MODEL` | No | Model name (default: `llama-3.1-8b-instant`) |
| `DEPLOYMENT_MODE` | Yes | Set to `cloud` |
| `SYNC_API_KEY` | Yes | API key for local instance sync |
| `EMBEDDING_MODEL` | No | Sentence transformer model (default: `all-MiniLM-L6-v2`) |
| `EMBEDDING_DIMENSION` | No | Vector dimension (default: `384`) |

### Backend (Local)

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `DATABASE_URL` | Yes | Local PostgreSQL connection string |
| `LLM_PROVIDER` | Yes | Set to `ollama` |
| `OLLAMA_URL` | Yes | Ollama server URL |
| `DEPLOYMENT_MODE` | Yes | Set to `local` |
| `SYNC_ENABLED` | No | Enable cloud sync (default: `false`) |
| `SYNC_SERVER_URL` | If sync enabled | Cloud backend URL |
| `SYNC_API_KEY` | If sync enabled | API key for sync authentication |
| `SYNC_INTERVAL_MINUTES` | No | Sync interval (default: `15`) |

### Frontend (Vercel)

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `VITE_API_URL` | Yes | Backend API URL (Render URL) |

---

## Cost Summary

All services used have free tiers:

| Service | Free Tier Limits |
| ------- | ---------------- |
| **Neon** | 512 MB storage, auto-suspend after 5 min inactivity |
| **Groq** | Generous rate limits, fast inference |
| **Render** | 750 hours/month, spins down after 15 min inactivity |
| **Vercel** | 100 GB bandwidth, unlimited deployments |

For a demo or low-traffic application, this stack costs **$0/month**.

---

## Upgrading for Production

For production use, consider:

1. **Render**: Upgrade to Starter ($7/month) for always-on backend and full Docling support
2. **Neon**: Upgrade for more storage and compute
3. **Vercel**: Pro plan for team features and analytics
4. **Custom Domain**: Add your own domain to both Vercel and Render
5. **Authentication**: Add API key or OAuth protection

### Enabling Full Cloud Document Processing

To enable full Docling processing in cloud (requires paid tier):

1. Upgrade Render to Starter plan (2GB RAM)
2. Change Dockerfile to use `Dockerfile.local`
3. Set `DEPLOYMENT_MODE=local` (enables full processing)
4. Redeploy
