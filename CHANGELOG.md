# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-06-27

### Added
*   **Vector Semantic Cache Layer:** Local FAISS cache index coupled with Redis key-value storage. duplicate or highly similar queries bypass LLM inferences entirely to yield sub-10ms response times.
*   **Conversational SSE Streams:** Asynchronous Server-Sent Events (SSE) token chunks streaming using FastAPI's `StreamingResponse`.
*   **Scoped FAISS Vector Store:** Isolated, department-scoped document indexing directories using local HuggingFace `all-MiniLM-L6-v2` embeddings.
*   **Asynchronous Processing:** Celery tasks and Redis background brokers managing document parsing, text chunking, and index insertions.
*   **Clean Schema Migrations:** SQLAlchemy 2.0 async database models orchestrated by Alembic batch database revisions.
*   **Modern React Frontend:** Single-page dashboard built using React 19, TypeScript, Vite 6, and Tailwind CSS.
*   **Premium Security:** JWT authentication flows, transparent token refresh interceptors, and Role-Based Access Controls (RBAC) route guards.
*   **Recruiter Demo Mode:** A fast login button automatically loading a pre-seeded corporate sandbox.

### Fixed
*   Content Security Policy headers to allow fetching Swagger UI assets correctly.
*   Celery eager-mode background execution conflicts with active FastAPI asyncio event loops.
*   User update API integration routes and department list retrieval 404s.
