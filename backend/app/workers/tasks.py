import asyncio
import os
import uuid
from typing import List
from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.repositories.document_repository import DocumentRepository
from app.services.parser_service import ParserService
from app.services.chunking_service import ChunkingService
from app.rag.vectorstore.vector_service import VectorService
from app.models.document import DocumentChunk
from app.utils.logger import logger

async def process_document_async(document_id_str: str, version_id_str: str, file_path: str) -> None:
    """Core asynchronous ingestion pipeline processing, chunking, embedding, and indexing."""
    doc_id = uuid.UUID(document_id_str)
    version_id = uuid.UUID(version_id_str)
    
    logger.info(f"Background worker starting text processing for Document {doc_id} (Version: {version_id})")

    async with AsyncSessionLocal() as db:
        doc_repo = DocumentRepository(db)
        
        # 1. Fetch document and version details
        doc = await doc_repo.get(doc_id)
        version = await doc_repo.get_version(doc_id, doc.current_version) if doc else None
        
        if not doc or not version:
            logger.error(f"Ingestion aborted: Document metadata missing for {doc_id} or Version {version_id}")
            return

        # Update status to PROCESSING
        doc.status = "PROCESSING"
        await doc_repo.update(doc, {})
        await db.commit()

        try:
            # 2. Parse file
            _, ext = os.path.splitext(file_path)
            parser = ParserService()
            parsed_pages = parser.parse_file(file_path, ext)
            page_count = len(parsed_pages)

            if page_count == 0:
                raise ValueError("Parsed document yielded zero text contents.")

            # 3. Split content into chunks
            chunking = ChunkingService()
            chunks_dto = chunking.split_pages(parsed_pages)
            chunk_count = len(chunks_dto)

            if chunk_count == 0:
                raise ValueError("Chunking document yielded zero text fragments.")

            # 4. Generate embeddings and add to FAISS index
            vector_service = VectorService()
            texts = [chunk.text for chunk in chunks_dto]
            
            # Map metadata for vector search mapping
            metadatas = [
                {
                    "document_id": str(doc_id),
                    "version_id": str(version_id),
                    "filename": doc.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index
                }
                for chunk in chunks_dto
            ]
            
            # Index in FAISS
            vector_index_ids = vector_service.add_chunks(doc.department_id, texts, metadatas)

            # 5. Persist Document chunks in relational database
            db_chunks = [
                DocumentChunk(
                    document_version_id=version_id,
                    chunk_index=chunk.chunk_index,
                    text_content=chunk.text,
                    page_number=chunk.page_number,
                    vector_index_id=vector_index_ids[chunk.chunk_index]
                )
                for chunk in chunks_dto
            ]
            await doc_repo.create_chunks(db_chunks)

            # 6. Update version and document completion details
            version.page_count = page_count
            version.chunk_count = chunk_count
            version.error_message = None
            
            doc.status = "COMPLETED"
            
            await db.commit()
            logger.info(f"Ingestion completed successfully for Document {doc_id}. Indexed {chunk_count} chunks.")

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {str(e)}", exc_info=True)
            # Re-fetch in a clean session state if needed and mark as FAILED
            await db.rollback()
            
            version.error_message = str(e)
            doc.status = "FAILED"
            await db.commit()
            raise e

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, document_id: str, version_id: str, file_path: str) -> None:
    """Celery synchronous wrapper scheduling async parsing pipeline."""
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            logger.info("Running event loop detected. Scheduling async ingestion as background task.")
            loop.create_task(process_document_async(document_id, version_id, file_path))
        else:
            asyncio.run(process_document_async(document_id, version_id, file_path))
    except Exception as exc:
        logger.warning(f"Retrying ingestion job due to execution error: {str(exc)}")
        try:
            self.retry(exc=exc)
        except Exception:
            logger.error("Reached maximum retry limit for document ingestion task.")
            # Set to FAILED database-side is already handled in process_document_async
