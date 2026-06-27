import pytest
import os
import uuid
import tempfile
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from tests.conftest import TestingSessionLocal
from app.services.parser_service import ParserService
from app.services.chunking_service import ChunkingService
from app.workers.tasks import process_document_async
from app.models.document import Document, DocumentVersion, DocumentChunk
from app.models.department import Department

def test_chunking_service():
    """Verify recursive character splitting splits long texts with configured size and overlap."""
    from app.services.parser_service import ParsedPage
    text = "This is paragraph one.\n\nThis is paragraph two. It contains more letters to trigger a split."
    page = ParsedPage(text=text, page_number=1)
    
    # Tiny chunk size to force a split
    chunking = ChunkingService(chunk_size=30, chunk_overlap=5)
    chunks = chunking.split_pages([page])
    
    assert len(chunks) > 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert len(chunks[0].text) > 0

@pytest.mark.asyncio
async def test_parser_txt():
    """Verify parser extracts content from plaintext files."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("Hello Text Parsing!")
        tmp_name = tmp.name

    try:
        parser = ParserService()
        pages = parser.parse_file(tmp_name, ".txt")
        assert len(pages) == 1
        assert pages[0].text == "Hello Text Parsing!"
        assert pages[0].page_number == 1
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

@pytest.mark.asyncio
@patch("app.workers.tasks.VectorService.add_chunks")
@patch("app.workers.tasks.AsyncSessionLocal", new=TestingSessionLocal)
async def test_async_ingestion_pipeline(mock_add_chunks: MagicMock, db: AsyncSession):
    """Verify background async task processes, chunks, embeds, and indexes successfully."""
    # Setup mock returns
    mock_add_chunks.return_value = ["mock-vector-id-0"]

    # 1. Fetch seeded department
    result = await db.execute(select(Department).where(Department.code == "ENG"))
    dept = result.scalar_one()

    # 2. Setup mock document in PENDING state
    doc = Document(
        filename="test.txt",
        department_id=dept.id,
        current_version=1,
        status="PENDING",
        tags=["engineering"]
    )
    db.add(doc)
    await db.flush()

    # Create dummy temp file on disk
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as tmp:
        tmp.write("This is a simple text file contents for document indexing checks.")
        tmp_path = tmp.name

    version = DocumentVersion(
        document_id=doc.id,
        version=1,
        file_path=tmp_path,
        file_hash="dummyhash123",
        file_size=100,
        mime_type="text/plain"
    )
    db.add(version)
    await db.commit()

    try:
        # Run background ingestion
        await process_document_async(str(doc.id), str(version.id), tmp_path)

        # Assert database updates
        async with TestingSessionLocal() as session:
            # Re-query
            res_doc = await session.get(Document, doc.id)
            assert res_doc.status == "COMPLETED"
            
            # Check version
            query = select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
            res_ver = (await session.execute(query)).scalar_one()
            assert res_ver.chunk_count == 1
            assert res_ver.page_count == 1

            # Check chunk
            query_chunk = select(DocumentChunk).where(DocumentChunk.document_version_id == res_ver.id)
            res_chunk = (await session.execute(query_chunk)).scalar_one()
            assert res_chunk.vector_index_id == "mock-vector-id-0"
            assert res_chunk.text_content == "This is a simple text file contents for document indexing checks."
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@pytest.mark.asyncio
async def test_document_upload_api_unauthorized(client: AsyncClient):
    """Verify upload route is restricted by permissions."""
    # Attempt upload without authorization headers
    response = await client.post(
        "/api/v1/documents/upload",
        data={"department_id": str(uuid.uuid4())},
        files={"file": ("test.txt", b"content", "text/plain")}
    )
    assert response.status_code == 401
