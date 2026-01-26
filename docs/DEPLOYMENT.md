# Deployment Guide

This guide covers deploying the Community Resilience MVP to cloud providers using the free tier.

## Architecture Overview

| Component | Local Development | Cloud Deployment |
| --------- | ----------------- | ---------------- |
| Frontend | Vite dev server (port 5173) | Vercel |
| Backend | Docker/uvicorn (port 8000) | Render |
| Database | Docker PostgreSQL | Neon |
| LLM | Ollama (local) | Groq API |

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
   ```
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
{"status": "healthy", "database": true, "llm": true}
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
   ```
   Heavy rain expected, Riverside Street flooding, power out
   ```
4. Verify you get AI-generated recommendations

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

---

## Environment Variables Reference

### Backend (Render)

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string |
| `LLM_PROVIDER` | Yes | Set to `groq` |
| `GROQ_API_KEY` | Yes | Groq API key |
| `GROQ_MODEL` | No | Model name (default: `llama-3.1-8b-instant`) |
| `EMBEDDING_MODEL` | No | Sentence transformer model (default: `all-MiniLM-L6-v2`) |
| `EMBEDDING_DIMENSION` | No | Vector dimension (default: `384`) |

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

1. **Render**: Upgrade to Starter ($7/month) for always-on backend
2. **Neon**: Upgrade for more storage and compute
3. **Vercel**: Pro plan for team features and analytics
4. **Custom Domain**: Add your own domain to both Vercel and Render
5. **Authentication**: Add API key or OAuth protection
