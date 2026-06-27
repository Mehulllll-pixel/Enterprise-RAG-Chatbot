# Production Deployment Guide

This document outlines the step-by-step setup to deploy this full-stack application in a production-ready environment.

---

## Architecture Overview

```
┌─────────────────┐       HTTPS       ┌─────────────────┐
│   Vercel SPA    │ ────────────────> │   Render Host   │
│   (React app)   │                   │ (FastAPI / Uvicorn)│
└─────────────────┘                   └─────────────────┘
                                               │
                       ┌───────────────────────┼───────────────────────┐
                       ▼                       ▼                       ▼
              ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
              │ Neon PostgreSQL │     │  Upstash Redis  │     │  Ollama Cloud   │
              │  (Relational)   │     │ (Caching/Broker)│     │(Secure Inference)│
              └─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 1. Database Setup: Neon PostgreSQL
1.  Sign in to [Neon Console](https://neon.tech/).
2.  Create a new project named `enterprise-rag`.
3.  Choose PostgreSQL version **16** or above.
4.  Copy the connection string (with pooled configuration if deploying workers).
    *   Example: `postgresql://username:password@ep-cool-snowflake-12345.us-east-2.aws.neon.tech/neondb?sslmode=require`

## 2. Cache & Broker Setup: Upstash Redis
1.  Sign in to [Upstash Console](https://upstash.com/).
2.  Create a new serverless Redis database.
3.  Copy the Redis connection URL.
    *   Example: `rediss://default:yourpassword@cool-marlin-12345.upstash.io:6379`

## 3. Backend Deployment: Render
1.  Sign in to [Render](https://render.com/).
2.  Select **New Web Service** and connect your GitHub repository.
3.  Configure variables:
    *   **Environment:** `Python`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4.  Add **Environment Variables**:
    *   `ENVIRONMENT`: `production`
    *   `DATABASE_URL`: `postgresql://...` (from Neon)
    *   `REDIS_URL`: `rediss://...` (from Upstash)
    *   `SECRET_KEY`: (Run `openssl rand -hex 32` to generate a strong key)
    *   `LLM_SERVICE`: `ollama`
    *   `OLLAMA_BASE_URL`: (Your dedicated cloud/on-premise Ollama instance endpoint)
    *   `EMBEDDING_MODEL`: `sentence-transformers/all-MiniLM-L6-v2`

## 4. Frontend Deployment: Vercel
1.  Sign in to [Vercel](https://vercel.com/).
2.  Select **New Project** and import the `frontend/` directory.
3.  Configure parameters:
    *   **Framework Preset:** `Vite`
    *   **Root Directory:** `frontend`
    *   **Build Command:** `npm run build`
    *   **Output Directory:** `dist`
4.  Add **Environment Variables**:
    *   `VITE_API_URL`: (URL of your deployed Render Web Service, e.g. `https://enterprise-rag-backend.onrender.com`)
