# Document Ingestion and Vectorization Pipeline

This document details the step-by-step architecture of the asynchronous document ingestion and vectorization pipeline.

```mermaid
graph TD
    User([Manager / Engineer]) -->|Upload File| API[FastAPI endpoint: /upload]
    API -->|Save Raw File| Storage[Local Filesystem / Cloud Storage]
    API -->|Create Pending Record| MetaDB[(PostgreSQL / SQLite)]
    API -->|Enqueue Task| RedisBroker{Redis Task Broker}
    RedisBroker -->|Consume Task| CeleryWorker[Celery Worker Process]
    
    subgraph Celery Text Processing Pipeline
        CeleryWorker -->|Load File| Parser[Parser Service: PDF, DOCX, TXT, MD]
        Parser -->|Extract Raw Pages| Chunking[Chunking Service: RecursiveTextSplitter]
        Chunking -->|Generate Text Segments| Embedding[Embedding Service: sentence-transformers]
        Embedding -->|Produce Vector Embeddings| Indexing[FAISS Index Writer]
    end
    
    Indexing -->|Add to Scoped Index| FAISS[(FAISS Vector Store)]
    Indexing -->|Insert Chunks Meta| MetaDB
    CeleryWorker -->|Mark Status COMPLETED| MetaDB
```

---

## Technical Details

### 1. Ingestion Endpoint
*   **FastAPI route:** `POST /api/v1/documents/upload`
*   **Access Scope:** Protected by JWT Authentication and requires `doc:upload` scope (default roles: `ADMIN`, `MANAGER`, `ENGINEER`).

### 2. Task Asynchrony
*   File data ingestion can take significant time for large manuals. The system delegates vector computations to background Celery workers.
*   While active processing takes place, the status in the database remains `PENDING` or `PROCESSING`.

### 3. Chunking Configuration
*   **Chunk size:** 1000 characters.
*   **Overlap size:** 200 characters (to maintain context across split points).
*   **Algorithm:** Recursive Character Text Splitter (splits on paragraph, sentence, and word boundaries).

### 4. Embedding Generation
*   **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors).
*   **Execution:** Runs locally via HuggingFace `sentence-transformers` library, requiring no third-party API keys or external network transit.
