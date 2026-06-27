# Enterprise RAG REST API Documentation

The backend service automatically generates a standardized Swagger specification available in development at:
`http://127.0.0.1:8000/docs`

---

## 1. Authentication Router (`/api/v1/auth`)

### `POST /auth/register`
*   **Description:** Register a new corporate employee profile.
*   **Payload:**
    ```json
    {
      "email": "employee@company.com",
      "password": "SecurePassword123",
      "full_name": "Jane Doe",
      "department_id": "b73ee999-bb4a-4719-a409-9a65909b3699"
    }
    ```
*   **Response (201):** User details.

### `POST /auth/login`
*   **Description:** Obtain Access and Refresh token pair.
*   **Payload:**
    ```json
    {
      "email": "employee@company.com",
      "password": "SecurePassword123"
    }
    ```
*   **Response (200):**
    ```json
    {
      "access_token": "eyJhbG...",
      "refresh_token": "eyJhbG...",
      "token_type": "bearer"
    }
    ```

---

## 2. Document Router (`/api/v1/documents`)

### `POST /documents/upload`
*   **Description:** Upload a new text, PDF, MD, or DOCX document to be vectorized.
*   **Form Parameters:**
    *   `file`: Binary file upload.
    *   `department_id`: Scoping UUID.
    *   `tags_json`: optional JSON array, e.g. `["HR", "Handbook"]`.
*   **Response (201):** Document metadata.

### `GET /documents`
*   **Description:** List all department-scoped documents.
*   **Query Parameters:**
    *   `department_id`: Scoping UUID.
    *   `status`: optional (PENDING, PROCESSING, COMPLETED, FAILED).
*   **Response (200):** List of document metadata items.

### `GET /documents/{id}/chunks`
*   **Description:** Retrieve all chunked text blocks for a document (used in UI preview).
*   **Response (200):** Chunks text array.

---

## 3. Chat Router (`/api/v1/chats`)

### `POST /chats`
*   **Description:** Create a new conversation session.
*   **Payload:**
    ```json
    {
      "title": "Topic title",
      "department_id": "b73ee999-bb4a-4719-a409-9a65909b3699"
    }
    ```

### `POST /chats/{id}/messages`
*   **Description:** Stream RAG grounding inference answer using Server-Sent Events (SSE).
*   **Payload:**
    ```json
    {
      "content": "What are the core hybrid days?"
    }
    ```
*   **Response (200):** Event Stream chunk tokens (`data: {"type": "token", "content": "..."}`) ending in a metadata event payload containing citations, confidence, and latency records.
