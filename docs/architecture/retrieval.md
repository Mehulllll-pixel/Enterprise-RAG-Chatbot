# RAG Retrieval & Similarity Inference Pipeline

This document details how the Retrieval-Augmented Generation (RAG) loop queries vector stores and grounds model responses.

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Application
    participant API as FastAPI Router
    participant Cache as Semantic Cache (FAISS + Redis)
    participant FAISS as FAISS Index (Department-Scoped)
    participant LLM as local Ollama Chat Engine
    
    User->>API: POST /chats/{id}/messages (with Prompt)
    API->>Cache: Query Cache Index for similar prompts
    alt Prompt Cache Hit (L2 Distance <= 0.15)
        Cache-->>API: Return Cached Message String
        API-->>User: Stream Cached Response (Sub-10ms)
    else Cache Miss
        API->>FAISS: Search top 4 chunks (L2 Distance <= 1.60)
        FAISS-->>API: Return document snippets & citation page numbers
        API->>API: Format System Grounding Prompt (inject Context)
        API->>LLM: Stream chat payload (POST /api/chat)
        LLM-->>API: Stream token chunks
        API-->>User: SSE Stream chunk tokens
        API->>Cache: Save generated response in Prompt cache
    end
```

---

## Technical Details

### 1. Department Isolation
*   FAISS indices are stored in isolated sub-directories based on the department UUID: `./data/vector_store/dept_<uuid>/`.
*   Users can **only** search within the department they are assigned to, guaranteeing data boundary isolation.

### 2. Matching Threshold
*   **Distance metric:** Euclidean L2 distance squared ($L_2^2$).
*   **Threshold:** `score <= 1.60` (ensures matching snippets have a cosine similarity of at least `0.20`, filtering out unrelated text while preserving weak matches).

### 3. LLM Grounding
*   The system uses the central `SYSTEM_RAG_PROMPT` configuring the LLM as a secure assistant.
*   **Grounding Rule:** If the snippets do not contain enough facts to resolve the query, the model is strictly bound to output a default "Information not found" sentence, preventing hallucination.
