import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user, has_permissions
from app.schemas.document import DocumentResponse, DocumentResponseWithRelations
from app.services.document_service import DocumentService
from app.models.user import User
from app.core.exceptions import AuthorizationException, ValidationException

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post(
    "/upload",
    response_model=DocumentResponseWithRelations,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permissions(["doc:upload"]))]
)
async def upload_document(
    file: UploadFile = File(...),
    department_id: uuid.UUID = Form(...),
    tags_json: Optional[str] = Form(None, description="JSON array of tags, e.g. ['finance', 'report']"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new corporate document for parsing and embedding (Manager/Engineer permissions)."""
    # Verify user belongs to department or is Admin
    if current_user.role_id != "ADMIN" and current_user.department_id != department_id:
        raise AuthorizationException("Access denied. You can only upload documents for your own department.")

    # Parse tags
    tags: List[str] = []
    if tags_json:
        try:
            tags = json.loads(tags_json)
            if not isinstance(tags, list):
                raise ValueError()
        except Exception:
            raise ValidationException("tags_json parameter must be a valid JSON array of strings.")

    doc_service = DocumentService(db)
    return await doc_service.upload_document(
        file=file,
        department_id=department_id,
        owner_id=current_user.id,
        tags=tags
    )

@router.post(
    "/{id}/new-version",
    response_model=DocumentResponseWithRelations,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permissions(["doc:upload"]))]
)
async def upload_new_version(
    id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload an updated version of a document."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_document(id)
    
    # Check permissions
    if current_user.role_id != "ADMIN" and current_user.department_id != doc.department_id:
        raise AuthorizationException("Access denied. You can only update documents within your department.")

    return await doc_service.update_document_version(
        document_id=id,
        file=file,
        owner_id=current_user.id
    )

@router.get(
    "",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["doc:read"]))]
)
async def list_documents(
    department_id: uuid.UUID = Query(...),
    tag: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List documents scoped to a department with tag and status filtering."""
    if current_user.role_id != "ADMIN" and current_user.department_id != department_id:
        raise AuthorizationException("Access denied. You can only view documents in your own department.")

    doc_service = DocumentService(db)
    return await doc_service.list_documents(
        department_id=department_id,
        tag=tag,
        status=status_filter,
        skip=skip,
        limit=limit
    )

@router.get(
    "/{id}",
    response_model=DocumentResponseWithRelations,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["doc:read"]))]
)
async def get_document_details(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get metadata details and version counts of a document."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_document(id)

    if current_user.role_id != "ADMIN" and current_user.department_id != doc.department_id:
        raise AuthorizationException("Access denied. Document belongs to another department.")

    return doc

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["doc:write"]))]
)
async def delete_document(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Purge document, its indexed embeddings in FAISS, and filesystem paths (Admin/Manager)."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_document(id)

    if current_user.role_id != "ADMIN" and current_user.department_id != doc.department_id:
        raise AuthorizationException("Access denied. Document belongs to another department.")

    await doc_service.delete_document(id)
    return {"message": "Document and all its indexed chunks deleted successfully."}

@router.post(
    "/{id}/reindex",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(has_permissions(["doc:write"]))]
)
async def reindex_document(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enqueue document for complete re-indexing (Admin/Manager)."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_document(id)

    if current_user.role_id != "ADMIN" and current_user.department_id != doc.department_id:
        raise AuthorizationException("Access denied. Document belongs to another department.")

    # Reset status to PENDING
    doc.status = "PENDING"
    await doc_service.doc_repo.update(doc, {})
    await db.commit()

    # Trigger background task for the latest version
    latest_version = sorted(doc.versions, key=lambda v: v.version)[-1]
    
    # Clean old chunks first
    vector_index_ids = await doc_service.doc_repo.delete_chunks_by_version(latest_version.id)
    if vector_index_ids:
        from app.rag.vectorstore.vector_service import VectorService
        vector_service = VectorService()
        vector_service.delete_chunks(doc.department_id, vector_index_ids)
    await db.commit()

    from app.workers.tasks import process_document_task
    process_document_task.delay(
        str(doc.id),
        str(latest_version.id),
        latest_version.file_path
    )

    return {"message": "Re-indexing task started.", "status": "PENDING"}

@router.get(
    "/{id}/chunks",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permissions(["doc:read"]))]
)
async def get_document_chunks(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve indexed text chunks for document previewing."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_document(id)
    if current_user.role_id != "ADMIN" and current_user.department_id != doc.department_id:
        raise AuthorizationException("Access denied. Document belongs to another department.")
    
    if not doc.versions:
        return []
    
    # Get latest version
    latest_version = sorted(doc.versions, key=lambda v: v.version)[-1]
    
    from sqlalchemy.future import select
    from app.models.document import DocumentChunk
    query = select(DocumentChunk).where(DocumentChunk.document_version_id == latest_version.id).order_by(DocumentChunk.chunk_index)
    res = await db.execute(query)
    chunks = res.scalars().all()
    
    return [{"index": c.chunk_index, "page_number": c.page_number, "text": c.text_content} for c in chunks]
