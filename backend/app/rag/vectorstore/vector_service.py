import os
import uuid
from typing import List, Dict, Any, Tuple, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LC_Document
from app.core.config import settings
from app.rag.embeddings.embedding_service import EmbeddingService
from app.utils.logger import logger

class VectorService:
    """Service managing department-isolated local FAISS vector indices."""
    
    def __init__(self):
        self.embeddings = EmbeddingService.get_embeddings_model()
        self.base_dir = settings.VECTOR_STORE_DIR
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_index_path(self, department_id: uuid.UUID) -> str:
        """Calculate the localized index storage folder for a specific department."""
        return os.path.join(self.base_dir, f"dept_{str(department_id)}")

    def _load_or_create_index(self, department_id: uuid.UUID) -> FAISS:
        """Load department index from disk, or initialize an empty one if missing."""
        path = self._get_index_path(department_id)
        index_file = os.path.join(path, "index.faiss")

        if os.path.exists(index_file):
            logger.info(f"Loading existing FAISS index for department: {department_id} from {path}")
            return FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            logger.info(f"Creating new empty FAISS index for department: {department_id}")
            # Initialize with a dummy document to generate the schema structure
            dummy_doc = LC_Document(page_content="initialize", metadata={"type": "sys"})
            db = FAISS.from_documents([dummy_doc], self.embeddings)
            # Save initialized index
            db.save_local(path)
            return db

    def add_chunks(
        self,
        department_id: uuid.UUID,
        texts: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> List[str]:
        """Index text fragments into a department-scoped FAISS database, returning internal IDs."""
        if not texts:
            return []

        path = self._get_index_path(department_id)
        db = self._load_or_create_index(department_id)
        
        # Build Document objects
        docs = [
            LC_Document(page_content=text, metadata=meta)
            for text, meta in zip(texts, metadatas)
        ]
        
        # Generate random unique IDs for the added documents in the index
        doc_ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        
        # Add to index
        db.add_documents(documents=docs, ids=doc_ids)
        
        # Persist index back to disk
        db.save_local(path)
        logger.info(f"Successfully added and saved {len(texts)} chunks to FAISS for department {department_id}")
        return doc_ids

    def similarity_search(
        self,
        department_id: uuid.UUID,
        query: str,
        k: int = 5,
        score_threshold: float = 0.8
    ) -> List[Tuple[LC_Document, float]]:
        """Query similarity match scoped to department, returning document structures and confidence margins."""
        path = self._get_index_path(department_id)
        index_file = os.path.join(path, "index.faiss")

        if not os.path.exists(index_file):
            logger.warning(f"No FAISS index exists yet for department {department_id}. Returning empty search.")
            return []

        db = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
        
        # FAISS search returns tuples of (Document, L2 distance/score)
        # Note: all-MiniLM-L6-v2 embeddings represent cosine distance.
        # Cosine distance = 1 - cosine_similarity. Smaller distance means higher similarity.
        results = db.similarity_search_with_score(query, k=k)
        
        # Filter results by score threshold if needed, or return all
        logger.info(f"Executed similarity search on department {department_id} for '{query}'. Hits: {len(results)}")
        return results

    def delete_chunks(self, department_id: uuid.UUID, vector_index_ids: List[str]) -> None:
        """Remove specific indexed chunks by their unique internal vector store identifiers."""
        if not vector_index_ids:
            return

        path = self._get_index_path(department_id)
        index_file = os.path.join(path, "index.faiss")

        if not os.path.exists(index_file):
            logger.warning(f"Attempted to delete chunks from non-existent index for department: {department_id}")
            return

        db = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
        
        # Purge chunks
        try:
            # We filter out vector ids that might not exist in the index to prevent errors
            valid_ids = [vid for vid in vector_index_ids if vid in db.index_to_docstore_id.values()]
            if valid_ids:
                db.delete(ids=valid_ids)
                db.save_local(path)
                logger.info(f"Successfully deleted {len(valid_ids)} chunks from FAISS index for department {department_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks from FAISS: {str(e)}")
            raise
