# Enterprise On-Premise RAG Chatbot Platform

A production-grade, secure, local Retrieval-Augmented Generation (RAG) platform. The application runs entirely on-premise, ensuring that company documents and user chat transcripts never leave the internal corporate network.

---

## 1. System Architecture

The platform follows Clean Architecture and SOLID design principles, split into a React client and a FastAPI API gateway:

*   **Frontend (React 19 + TypeScript + Vite + Tailwind CSS):** A responsive, glassmorphic dark-themed dashboard. Integrates real-time Server-Sent Events (SSE) token stream readers, citations panels, confidence metrics meters, user registers, and admin directory panels.
*   **Backend (FastAPI + Python 3.12 + SQLAlchemy 2.0 + Celery):** Asynchronous API gateway with structured error handlers, SQLAlchemy models with Alembic migrations, repository-service pattern, and role-based access controls (RBAC) token dependency guards.
*   **Vector Engine & LLM Pipeline (FAISS + sentence-transformers + Ollama):** Department-scoped isolated FAISS indexes, sentence embeddings generated locally using `all-MiniLM-L6-v2`, and text generation processed locally via a Mistral-7B model inside Ollama.
*   **Semantic Cache Layer (FAISS + Redis):** Stores previously answered queries and vectors locally. Similarity query matches bypass LLM inference, retrieving cached answers in sub-10ms.
*   **Task Queue (Celery + Redis):** Document parsing (.pdf, .docx, .txt, .md), signature checking, text recursive chunking, and embedding generation are processed asynchronously in the background.

---

## 2. Directory Tree Structure

```
├── backend/                  # FastAPI Application gateway
│   ├── app/
│   │   ├── api/v1/           # REST & SSE stream controllers
│   │   ├── core/             # DB pooling, security, JWT and Redis fallbacks
│   │   ├── models/           # Declarative base tables (User, Chat, Chunks, etc.)
│   │   ├── rag/              # Ollama LLM, FAISS managers, prompts and cache
│   │   ├── repositories/     # Async database queries managers
│   │   ├── services/         # Parsing, ingestion, and RAG orchestrators
│   │   └── workers/          # Celery background workers tasks
│   ├── alembic/              # Database migration revisions
│   └── tests/                # Pytest automated test suites
├── frontend/                 # React SPA Client
│   ├── src/
│   │   ├── components/       # Route guards
│   │   ├── context/          # Profile Auth state global providers
│   │   ├── pages/            # Chat, Library, Register, Admin dashboards
│   │   └── services/         # api.ts client with transparent token refreshing
│   └── nginx.conf            # Reverse proxy config for containerized routing
└── docker-compose.yml        # Multi-container production orchestration
```

---

## 3. Quickstart Guide (Local Development)

### 3.1. Prerequisite Systems
Ensure the following are installed and running locally:
1.  **Python 3.12**
2.  **Node.js 20+**
3.  **Ollama** (with Mistral-7B downloaded: `ollama run mistral`)

### 3.2. Setup Backend
1.  Navigate to `backend` directory:
    ```bash
    cd backend
    ```
2.  Create virtual environment and install packages:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
    ```
3.  Apply Alembic database migrations:
    ```bash
    .\venv\Scripts\alembic upgrade head
    ```
4.  Run FastAPI Dev Server:
    ```bash
    .\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
    ```

### 3.3. Setup Frontend
1.  Navigate to `frontend` directory:
    ```bash
    cd ../frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run Dev Server (proxies API queries automatically to `http://localhost:8000`):
    ```bash
    npm run dev
    ```

---

## 4. Production Deployment (Docker Compose)

The entire multi-container service stack (PostgreSQL, Redis, Ollama, Backend, Celery Worker, and Nginx Frontend) can be initialized with a single command:

```bash
docker-compose up --build -d
```

### 4.1. Network Proxying
Nginx serves the frontend client on port **3000** and reverse-proxies `/api` traffic directly to the backend service container, disabling buffering for smooth SSE streams.

---

## 5. Seeded Accounts & Roles

On startup, the seeder automatically registers standard roles, the `VAL` validation department, and an admin user:
*   **Admin Email:** `admin@test.com` (or `admin@company.com`)
*   **Password:** `AdminPass123!`
