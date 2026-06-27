import pytest
import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.rag.llm.llm_service import LLMService
from app.rag.semantic_cache.cache_service import SemanticCacheService
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.models.chat import Chat, Message
from app.models.department import Department
from sqlalchemy.orm import selectinload
from tests.conftest import MockRedis, TestingSessionLocal

@pytest.mark.asyncio
async def test_llm_health_check():
    """Verify health checker yields True on HTTP 200."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        llm = LLMService()
        assert await llm.check_health() is True

        mock_get.return_value = MagicMock(status_code=500)
        assert await llm.check_health() is False

@pytest.mark.asyncio
async def test_llm_chat_stream_generation():
    """Verify LLM client parses streaming JSON lines from Ollama endpoint."""
    llm = LLMService()
    
    mock_response = MagicMock(status_code=200)
    # Define an async generator to simulate line streaming
    async def mock_iter_lines():
        lines = [
            b'{"message": {"content": "Hello "}}',
            b'{"message": {"content": "world!"}}'
        ]
        for line in lines:
            yield line

    mock_response.iter_lines = mock_iter_lines
    
    # Mock httpx client stream
    mock_context_mgr = MagicMock()
    mock_context_mgr.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context_mgr.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient.stream", return_value=mock_context_mgr):
        tokens = []
        async for token in llm.generate_chat_stream([{"role": "user", "content": "hi"}], temperature=0.0):
            tokens.append(token)
            
        assert len(tokens) == 2
        assert "".join(tokens) == "Hello world!"

@pytest.mark.asyncio
async def test_semantic_cache_workflow():
    """Verify saving to and looking up from semantic cache yields identical payloads."""
    mock_redis = MockRedis()
    cache_service = SemanticCacheService(mock_redis)
    dept_id = uuid.uuid4()
    query = "What is the remote work policy?"
    
    captured_key_id = None
    
    # Mock add_documents to capture the generated cache key ID
    def mock_add_documents(documents, **kwargs):
        nonlocal captured_key_id
        captured_key_id = documents[0].metadata["cache_key_id"]
        return [str(uuid.uuid4())]

    # Define dynamic search match function returning captured ID
    def mock_similarity_search_with_score(query_str, k=1, **kwargs):
        doc = MagicMock()
        doc.metadata = {"cache_key_id": captured_key_id}
        return [(doc, 0.02)]
    
    # Mock load and search functions
    with patch("app.rag.semantic_cache.cache_service.os.path.exists", return_value=True):
        with patch("app.rag.semantic_cache.cache_service.FAISS.load_local") as mock_load:
            mock_db = MagicMock()
            mock_db.add_documents = mock_add_documents
            mock_db.similarity_search_with_score = mock_similarity_search_with_score
            mock_load.return_value = mock_db
            
            # Mock load index in save method as well
            with patch("app.rag.semantic_cache.cache_service.SemanticCacheService._load_or_create_cache_index") as mock_create:
                mock_create.return_value = mock_db
                
                # Save payload to cache
                await cache_service.save(
                    department_id=dept_id,
                    query=query,
                    response_content="Cached Remote Answer",
                    citations=[{"id": "REF-1", "filename": "policy.txt"}],
                    confidence_score=0.98
                )
                
                # Lookup
                res = await cache_service.lookup(dept_id, query)
                assert res is not None
                assert res["content"] == "Cached Remote Answer"
                assert res["confidence_score"] == 0.98
                assert len(res["citations"]) == 1

@pytest.mark.asyncio
async def test_rag_pipeline_grounding(db: AsyncSession):
    """Verify RAGService outputs correct formatted SSE streaming payload."""
    mock_redis = MockRedis()
    rag_service = RAGService(db, mock_redis)
    
    # Fetch seeded department
    result = await db.execute(select(Department).where(Department.code == "ENG"))
    dept = result.scalar_one()
    
    # Mock vector search to return empty matches to test grounding fallback
    with patch("app.rag.vectorstore.vector_service.VectorService.similarity_search", return_value=[]):
        # Mock LLM stream generator
        async def mock_llm_stream(*args, **kwargs):
            yield "I do "
            yield "not know."
            
        with patch("app.rag.llm.llm_service.LLMService.generate_chat_stream", side_effect=mock_llm_stream):
            # Run stream
            generator = rag_service.generate_response_stream(dept.id, "unrelated question", [])
            events = []
            async for event_str in generator:
                events.append(json.loads(event_str))
                
            assert len(events) == 3 # 2 tokens, 1 metadata
            assert events[0]["content"] == "I do "
            assert events[1]["content"] == "not know."
            assert events[2]["type"] == "metadata"
            assert len(events[2]["citations"]) == 0
            assert events[2]["confidence_score"] == 0.0

@pytest.mark.asyncio
async def test_chats_rest_apis(client: AsyncClient, db: AsyncSession):
    """Verify chat session REST controllers handle creations, lists, and SSE queries."""
    # 1. Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get department
    result = await db.execute(select(Department).where(Department.code == "ENG"))
    dept = result.scalar_one()

    # 3. Create chat
    chat_response = await client.post(
        "/api/v1/chats",
        json={"title": "RAG Chat", "department_id": str(dept.id)},
        headers=headers
    )
    assert chat_response.status_code == 201
    chat_id = chat_response.json()["id"]

    # 4. List chats
    list_response = await client.get("/api/v1/chats", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    # 5. Submit query message (mock RAG stream)
    # Mock generate_response_stream
    async def mock_rag_stream(*args, **kwargs):
        yield json.dumps({"type": "token", "content": "Mistral answer"})
        yield json.dumps({
            "type": "metadata",
            "citations": [],
            "confidence_score": 0.5,
            "related_questions": ["What?"]
        })

    with patch("app.api.v1.chats.RAGService.generate_response_stream", side_effect=mock_rag_stream):
        response = await client.post(
            f"/api/v1/chats/{chat_id}/messages",
            json={"content": "What is security?"},
            headers=headers
        )
        assert response.status_code == 200
        
        # Read stream
        body = await response.aread()
        body_text = body.decode("utf-8")
        assert "Mistral answer" in body_text
        assert "metadata" in body_text

        # Verify chat transcripts save
        async with TestingSessionLocal() as session:
            # Query chat with messages
            query = select(Chat).where(Chat.id == uuid.UUID(chat_id)).options(selectinload(Chat.messages))
            res = await session.execute(query)
            c = res.scalar_one()
            assert len(c.messages) == 2 # user and assistant message
            assert c.messages[0].role == "user"
            assert c.messages[1].role == "assistant"
            assert c.messages[1].content == "Mistral answer"
            assert c.messages[1].confidence_score == 0.5
