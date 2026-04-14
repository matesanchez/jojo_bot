# Jojo Bot — Deployment Guide

## Before You Deploy

Make sure you've run the ingestion pipeline locally to build the ChromaDB vector database:

```bash
cd src/backend
source venv/bin/activate
python -m rag.ingest --input ../../data/manuals/
```

The `chroma_db/` folder must exist at the project root before building the Docker image.

---

## Backend — Railway

1. Go to https://railway.app and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub Repo**
3. Select your `jojobot` repository
4. In **Settings → Variables**, add:
   - `ANTHROPIC_API_KEY` = your key from https://console.anthropic.com/settings/keys
   - `CHROMA_DB_PATH` = `/app/chroma_db`
   - `DATABASE_URL` = `sqlite:///./jojobot.db`
   - `CORS_ORIGINS` = `https://your-vercel-url.vercel.app`
   - `LOG_LEVEL` = `info`
5. Railway auto-deploys from the `main` branch on every push

> **Note:** The first deploy uploads your `chroma_db/` directory inside the Docker image. If you re-ingest with new documents, you'll need to rebuild and redeploy.

---

## Frontend — Vercel

1. Go to https://vercel.com and sign in with GitHub
2. Click **Import Project** → select your `jojobot` repository
3. Set **Root Directory** to: `src/frontend`
4. In **Environment Variables**, add:
   - `NEXT_PUBLIC_API_URL` = `https://your-railway-url.railway.app`
5. Click **Deploy**

---

## After Both Are Deployed

1. Copy your Vercel URL (e.g. `https://jojobot.vercel.app`)
2. Go back to Railway → Settings → Variables
3. Update `CORS_ORIGINS` to include your Vercel URL
4. Railway will automatically redeploy

5. Visit your Vercel URL and test by asking: "How do I prime the pumps on the ÄKTA pure?"

---

## Local Development

```bash
# One command to start both servers:
chmod +x start.sh
./start.sh
```

Then open http://localhost:3000
