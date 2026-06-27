import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from app.models.document import Document, DocumentVersion, DocumentChunk
from app.repositories.base import BaseRepository

class DocumentRepository(BaseRepository[Document]):
    """Repository wrapping data access operations for Document metadata."""
    def __init__(self, db: AsyncSession):
        super().__init__(Document, db)

    async def get_with_relations(self, id: uuid.UUID) -> Optional[Document]:
        """Fetch document details, including its versions and department scope."""
        query = (
            select(Document)
            .where(Document.id == id)
            .options(
                joinedload(Document.department),
                selectinload(Document.versions)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_version_by_hash(self, file_hash: str, department_id: uuid.UUID) -> Optional[DocumentVersion]:
        """Find if a version with the same content hash exists in the department."""
        query = (
            select(DocumentVersion)
            .join(Document)
            .where(
                DocumentVersion.file_hash == file_hash,
                Document.department_id == department_id
            )
            .options(joinedload(DocumentVersion.document))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_filters(
        self,
        department_id: uuid.UUID,
        tag: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Document]:
        """Fetch documents matching department, status, and tag constraints."""
        query = select(Document).where(Document.department_id == department_id)
        
        if status:
            query = query.where(Document.status == status)
            
        if tag:
            # PostgreSQL syntax: tags.contains([tag])
            # For SQLite compatibility with Mapped lists: tags can be loaded as JSON,
            # so we check if JSON contains tag, or check matching tags list length/presence.
            # Using tags.like(f'%"{tag}"%') is SQLite compatible for JSON lists.
            # Let's write a dialect agnostic check:
            query = query.where(Document.tags.like(f'%"{tag}"%'))
            
        query = query.offset(skip).limit(limit).order_by(Document.updated_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_version(self, version_obj: DocumentVersion) -> DocumentVersion:
        """Create a new version record for a document."""
        self.db.add(version_obj)
        await self.db.flush()
        return version_obj

    async def create_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Bulk save document chunks."""
        self.db.add_all(chunks)
        await self.db.flush()
        return chunks

    async def get_version(self, document_id: uuid.UUID, version_number: int) -> Optional[DocumentVersion]:
        """Fetch a specific version metadata of a document."""
        query = (
            select(DocumentVersion)
            .where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.version == version_number
            )
            .options(selectinload(DocumentVersion.chunks))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_chunks_by_version(self, version_id: uuid.UUID) -> List[str]:
        """Delete all chunks for a specific version, returning their vector index IDs."""
        # 1. Fetch chunks to get vector_index_ids
        query = select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        result = await self.db.execute(query)
        chunks = list(result.scalars().all())
        
        vector_index_ids = [chunk.vector_index_id for chunk in chunks]
        
        # 2. Delete chunks (cascade or manual delete)
        for chunk in chunks:
            await self.db.delete(chunk)
            
        await self.db.flush()
        return vector_index_ids
