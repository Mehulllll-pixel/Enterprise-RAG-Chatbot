import hashlib
import os
import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ConflictException, EntityNotFoundException, ValidationException
from app.models.document import Document, DocumentVersion
from app.repositories.document_repository import DocumentRepository
from app.utils.logger import logger
from app.utils.file_validator import validate_uploaded_file

class DocumentService:
    """Business service layer for document lifecycle and ingestion."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        # Create uploads folder if missing
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    @staticmethod
    def calculate_file_hash(content: bytes) -> str:
        """Generate SHA-256 hash representation of file content for duplicate check."""
        hash_sha256 = hashlib.sha256()
        hash_sha256.update(content)
        return hash_sha256.hexdigest()

    async def _save_physical_file(self, content: bytes, original_name: str) -> str:
        """Write file contents safely to configured uploads path, returning absolute path."""
        _, ext = os.path.splitext(original_name)
        unique_filename = f"{uuid.uuid4()}{ext.lower()}"
        file_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, unique_filename))
        
        # Write to disk
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    async def upload_document(
        self,
        file: UploadFile,
        department_id: uuid.UUID,
        owner_id: uuid.UUID,
        tags: Optional[List[str]] = None
    ) -> Document:
        """Process file upload request, validate, check hash collision, write to disk, and register PENDING state."""
        # 1. Validate file (Size, magic bytes, extensions)
        validate_uploaded_file(file)
        
        # Read content
        content = await file.read()
        file_size = len(content)
        
        # 2. Check duplicate hash detection
        file_hash = self.calculate_file_hash(content)
        existing_version = await self.doc_repo.get_version_by_hash(file_hash, department_id)
        if existing_version:
            raise ConflictException(
                f"File '{file.filename}' already indexed in this department. "
                f"Duplicate of Document '{existing_version.document.filename}' (v{existing_version.version})."
            )

        # 3. Write physical file to storage
        file_path = await self._save_physical_file(content, file.filename)

        # 4. Insert Document metadata
        doc = Document(
            filename=file.filename,
            department_id=department_id,
            owner_id=owner_id,
            current_version=1,
            status="PENDING",
            tags=tags or []
        )
        created_doc = await self.doc_repo.create(doc)
        
        # Insert Version metadata
        version = DocumentVersion(
            document_id=created_doc.id,
            version=1,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            created_by=owner_id
        )
        await self.doc_repo.create_version(version)
        await self.db.commit()

        # 5. Trigger Asynchronous Celery background processing task
        # We import here to avoid circular dependencies
        from app.workers.tasks import process_document_task
        process_document_task.delay(
            str(created_doc.id),
            str(version.id),
            file_path
        )

        logger.info(f"Ingestion started for document {created_doc.id} (Version 1, status: PENDING)")
        return await self.doc_repo.get_with_relations(created_doc.id)

    async def update_document_version(
        self,
        document_id: uuid.UUID,
        file: UploadFile,
        owner_id: uuid.UUID
    ) -> Document:
        """Upload a new version of an existing document."""
        doc = await self.doc_repo.get_with_relations(document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found.")

        # Validate file
        validate_uploaded_file(file)
        content = await file.read()
        file_size = len(content)

        # Check duplicate hash detection
        file_hash = self.calculate_file_hash(content)
        existing_version = await self.doc_repo.get_version_by_hash(file_hash, doc.department_id)
        if existing_version:
            raise ConflictException(
                f"File content is duplicate of an already indexed version (Document ID: {existing_version.document_id})."
            )

        # Save physical file
        file_path = await self._save_physical_file(content, file.filename)

        # Increment version
        new_version_num = doc.current_version + 1
        
        # Update Document state to PENDING during processing
        doc.current_version = new_version_num
        doc.status = "PENDING"
        await self.doc_repo.update(doc, {})

        # Create new version metadata
        version = DocumentVersion(
            document_id=doc.id,
            version=new_version_num,
            file_path=file_path,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            created_by=owner_id
        )
        await self.doc_repo.create_version(version)
        await self.db.commit()

        # Trigger background processing task
        from app.workers.tasks import process_document_task
        process_document_task.delay(
            str(doc.id),
            str(version.id),
            file_path
        )

        logger.info(f"Updating document {doc.id} to new version {new_version_num} (status: PENDING)")
        return await self.doc_repo.get_with_relations(doc.id)

    async def get_document(self, document_id: uuid.UUID) -> Document:
        """Get document details with versions or raise 404."""
        doc = await self.doc_repo.get_with_relations(document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found.")
        return doc

    async def list_documents(
        self,
        department_id: uuid.UUID,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Document]:
        """Fetch documents by department filters."""
        return await self.doc_repo.list_by_filters(department_id, tag, status, skip, limit)

    async def delete_document(self, document_id: uuid.UUID) -> None:
        """Purge document record, erase local vector index chunks, and delete files from disk."""
        doc = await self.doc_repo.get_with_relations(document_id)
        if not doc:
            raise EntityNotFoundException(f"Document with ID {document_id} not found.")

        department_id = doc.department_id
        logger.info(f"Initiating purge for Document {document_id} in Department {department_id}")

        # 1. Collect all vector_index_ids across all document versions and delete from FAISS
        vector_index_ids: List[str] = []
        files_to_delete: List[str] = []

        for version in doc.versions:
            # Delete chunks from DB and capture their vector index IDs
            v_ids = await self.doc_repo.delete_chunks_by_version(version.id)
            vector_index_ids.extend(v_ids)
            files_to_delete.append(version.file_path)

        # Delete from FAISS vector store
        if vector_index_ids:
            from app.rag.vectorstore.vector_service import VectorService
            vector_service = VectorService()
            # Clean up vector index ids
            # Filter out initialized dummy vectors (if any) or check valid ids
            vector_service.delete_chunks(department_id, vector_index_ids)

        # 2. Delete physical files from disk
        for path in files_to_delete:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Purged physical file: {path}")
            except Exception as e:
                logger.error(f"Failed to delete file {path} from disk: {str(e)}")

        # 3. Delete document from database (cascade deletes versions/chunks)
        await self.doc_repo.delete(doc.id)
        await self.db.commit()
        logger.info(f"Purged Document metadata {document_id} from database.")
