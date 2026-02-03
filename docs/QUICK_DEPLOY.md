# Quick Deployment Guide: Render + Netlify

This guide walks you through deploying the Community Resilience MVP to production using Render (backend) and Netlify (frontend).

## 📋 Prerequisites

- GitHub account with this repository
- [Neon](https://neon.tech) account (free PostgreSQL)
- [Groq](https://console.groq.com) account (free LLM API)
- [Render](https://render.com) account (free backend hosting)
- [Netlify](https://netlify.com) account (free frontend hosting)

## 🔐 Production Keys (SAVE THESE!)

**Generated secure keys for your production deployment:**

```bash
JWT_SECRET_KEY=G0Dkzu6DPwJxbuksOj7UF9y3hPwTT_LFKZAtRB0iTHY
INTERNAL_AUTH_SECRET=67u9-H2sUxliDfcN2h3nDmJCGRk8bgQUtuvB-MAtpt8
SYNC_API_KEY=cr_KJol7nZ_gt3GNLEbjPRO-p6ZKbEFY3PGlOHPIWLdl7s
```

⚠️ **IMPORTANT**: Save these keys securely! You'll need them for both Render and Netlify configuration.

---

## Part 1: Deploy Backend to Render

### Step 1: Prepare Database (Neon)

1. Go to [Neon Console](https://console.neon.tech)
2. Click **New Project**
   - Name: `community-resilience`
   - Region: Choose closest to your users (e.g., `us-east-2`)
3. Click **Create Project**

4. Enable pgvector:
   - Go to **SQL Editor**
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

5. Get connection string:
   - Go to **Dashboard** → **Connection Details**
   - Copy the connection string (looks like):

     ```text
     postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```

   - Replace `neondb` with `community_resilience`

6. Run migrations from your local machine:

   ```bash
   cd backend
   export DATABASE_URL="postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/community_resilience?sslmode=require"
   alembic upgrade head
   python scripts/load_seed_data.py
   ```

### Step 2: Get Groq API Key

1. Go to [Groq Console](https://console.groq.com)
2. Sign up/log in
3. Go to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_`)

### Step 3: Deploy to Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Blueprint**
3. Connect your GitHub repository
4. Render will detect `render.yaml` - click **Apply**

### Step 4: Configure Render Environment Variables

In the Render dashboard for your service, go to **Environment** and add:

#### Required Variables

| Variable | Value | Notes |
| -------- | ----- | ----- |
| `DATABASE_URL` | Your Neon connection string | From Step 1 |
| `GROQ_API_KEY` | Your Groq API key | From Step 2 |
| `JWT_SECRET_KEY` | `G0Dkzu6DPwJxbuksOj7UF9y3hPwTT_LFKZAtRB0iTHY` | From production keys above |
| `INTERNAL_AUTH_SECRET` | `67u9-H2sUxliDfcN2h3nDmJCGRk8bgQUtuvB-MAtpt8` | From production keys above |
| `SYNC_API_KEY` | `cr_KJol7nZ_gt3GNLEbjPRO-p6ZKbEFY3PGlOHPIWLdl7s` | For sync authentication |
| `FRONTEND_URL` | `https://YOUR_NETLIFY_SITE.netlify.app` | Will add after deploying frontend |

#### Email Configuration (Optional but Recommended)

If you want email functionality (password resets, notifications):

1. Sign up for [Resend](https://resend.com) (free tier: 100 emails/day)
2. Get your API key
3. Add these variables:

| Variable | Value |
| -------- | ----- |
| `RESEND_API_KEY` | Your Resend API key |
| `EMAIL_FROM_ADDRESS` | `noreply@yourdomain.com` |
| `EMAIL_FROM_NAME` | `Community Resilience` |
| `ADMIN_EMAIL` | Your admin email |
| `EMAIL_ENABLED` | `true` |

#### OAuth Configuration (Optional)

If you want social login:

**Google OAuth:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 credentials
3. Add variables: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`

**GitHub OAuth:**

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create OAuth App
3. Add variables: `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`

### Step 5: Verify Backend Deployment

Once deployed, test your backend:

```bash
curl https://YOUR_RENDER_URL.onrender.com/health
```

Expected response:

```json
{
  "status": "healthy",
  "database": true,
  "llm": true,
  "deployment_mode": "cloud"
}
```

⚠️ **Save your Render URL!** You'll need it for Netlify configuration.

---

## Part 2: Deploy Frontend to Netlify

### Step 1: Deploy to Netlify

1. Go to [Netlify Dashboard](https://app.netlify.com)
2. Click **Add new site** → **Import an existing project**
3. Choose **GitHub** and select your repository
4. Configure build settings:
   - **Base directory**: `frontend`
   - **Build command**: `pnpm run build`
   - **Publish directory**: `frontend/build`
   - **Production branch**: `main` (or your default branch)
5. Click **Deploy site**

### Step 2: Configure Netlify Environment Variables

1. Go to **Site settings** → **Environment variables**
2. Click **Add a variable**
3. Add the following:

| Variable | Value | Notes |
| -------- | ----- | ----- |
| `VITE_API_URL` | `https://YOUR_RENDER_URL.onrender.com` | Your Render backend URL (no trailing slash) |

### Step 3: Update Backend with Frontend URL

1. Go back to your Render dashboard
2. Update the `FRONTEND_URL` environment variable with your Netlify URL:

   ```text
   https://YOUR_NETLIFY_SITE.netlify.app
   ```

3. Render will automatically redeploy with the new variable

### Step 4: Custom Domain (Optional)

To use your own domain:

1. In Netlify: **Domain settings** → **Add custom domain**
2. Follow DNS configuration instructions
3. Update `FRONTEND_URL` in Render with your custom domain

---

## 🧪 Testing Your Deployment

### 1. Test Backend Health

```bash
curl https://YOUR_RENDER_URL.onrender.com/health
```

### 2. Test Frontend

1. Open your Netlify URL in a browser
2. Go to the **Query** page
3. Enter a test query:

   ```text
   Heavy rain expected, Riverside Street flooding, power out
   ```

4. Verify you get AI-generated recommendations

### 3. Test Authentication

1. Create a new account
2. Log in
3. Try uploading a document (PDF or text file)
4. Verify it appears in your documents list

---

## 🔧 Troubleshooting

### Backend Issues

**Database connection fails:**

- Verify DATABASE_URL is correct
- Check Neon database is running
- Ensure pgvector extension is enabled

**LLM requests fail:**

- Verify GROQ_API_KEY is correct
- Check Groq API status at [status.groq.com](https://status.groq.com)

**CORS errors:**

- Ensure FRONTEND_URL is set correctly in Render
- Verify it matches your Netlify URL exactly (no trailing slash)

### Frontend Issues

**API calls fail:**

- Check VITE_API_URL in Netlify environment variables
- Verify backend is deployed and healthy
- Check browser console for CORS errors

**Build fails:**

- Ensure Node version is 22 (configured in netlify.toml)
- Check build logs in Netlify dashboard
- Verify pnpm dependencies are correct

---

## 📊 Monitoring

### Render Logs

View backend logs in Render:

1. Dashboard → Your service → **Logs**
2. Monitor for errors and performance issues

### Netlify Analytics (Optional)

Enable Netlify Analytics for traffic insights:

1. Site settings → **Analytics**
2. Follow setup instructions

---

## 💰 Cost Breakdown (Free Tiers)

| Service | Free Tier | Notes |
| ------- | --------- | ----- |
| Neon | 512 MB storage | 1 project, 10 branches |
| Groq | 14,400 requests/day | Rate limited |
| Render | 750 hours/month | Spins down after 15 min inactivity |
| Netlify | 100 GB bandwidth/month | Unlimited sites |

**Total Cost: $0/month** (within free tier limits)

---

## 🚀 Next Steps

1. **Set up monitoring**: Configure uptime monitoring (e.g., UptimeRobot)
2. **Enable analytics**: Add Google Analytics or Plausible
3. **Configure backups**: Set up automated Neon database backups
4. **Add custom domain**: Configure your own domain for professional branding
5. **Enable email**: Set up Resend for password resets and notifications
6. **Scale as needed**: Upgrade to paid tiers when you exceed free limits

---

## 📝 Environment Variables Summary

### Render (Backend)

```bash
# Database
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/community_resilience?sslmode=require

# LLM
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama-3.1-8b-instant

# Authentication
JWT_SECRET_KEY=G0Dkzu6DPwJxbuksOj7UF9y3hPwTT_LFKZAtRB0iTHY
INTERNAL_AUTH_SECRET=67u9-H2sUxliDfcN2h3nDmJCGRk8bgQUtuvB-MAtpt8
SYNC_API_KEY=cr_KJol7nZ_gt3GNLEbjPRO-p6ZKbEFY3PGlOHPIWLdl7s

# URLs
FRONTEND_URL=https://YOUR_NETLIFY_SITE.netlify.app

# Deployment
DEPLOYMENT_MODE=cloud

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Email (optional)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxx
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Community Resilience
ADMIN_EMAIL=admin@yourdomain.com
EMAIL_ENABLED=true
```

### Netlify (Frontend)

```bash
VITE_API_URL=https://YOUR_RENDER_URL.onrender.com
```

---

## 🆘 Support

- **Documentation**: See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed information
- **Issues**: Open an issue on GitHub
- **Render Support**: [render.com/docs](https://render.com/docs)
- **Netlify Support**: [docs.netlify.com](https://docs.netlify.com)

---

**Deployment Status:**

- [ ] Neon database created and migrated
- [ ] Groq API key obtained
- [ ] Backend deployed to Render
- [ ] Frontend deployed to Netlify
- [ ] Environment variables configured
- [ ] Health check passes
- [ ] End-to-end test successful

Once all checkboxes are complete, your application is live! 🎉
