import os
import json
import uuid
from typing import Optional, Dict, Any, Tuple
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LC_Document
import redis.asyncio as aioredis

from app.core.config import settings
from app.rag.embeddings.embedding_service import EmbeddingService
from app.utils.logger import logger

class SemanticCacheService:
    """Service providing semantic query-response caching using local FAISS indices and Redis storage."""
    
    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.embeddings = EmbeddingService.get_embeddings_model()
        self.cache_dir = os.path.join(settings.VECTOR_STORE_DIR, "semantic_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.distance_threshold = 0.08 # Strict similarity required to hit cache

    def _get_faiss_path(self, department_id: uuid.UUID) -> str:
        """Calculate path to department-scoped cache index."""
        return os.path.join(self.cache_dir, f"cache_{str(department_id)}")

    def _load_or_create_cache_index(self, department_id: uuid.UUID) -> FAISS:
        path = self._get_faiss_path(department_id)
        index_file = os.path.join(path, "index.faiss")

        if os.path.exists(index_file):
            return FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            dummy_doc = LC_Document(page_content="initialize_cache", metadata={"type": "sys"})
            db = FAISS.from_documents([dummy_doc], self.embeddings)
            db.save_local(path)
            return db

    async def lookup(self, department_id: uuid.UUID, query: str) -> Optional[Dict[str, Any]]:
        """Look up if a semantically equivalent query has a cached response."""
        path = self._get_faiss_path(department_id)
        index_file = os.path.join(path, "index.faiss")

        if not os.path.exists(index_file):
            return None

        try:
            db = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
            # Search with score (returns doc and L2 distance)
            results = db.similarity_search_with_score(query, k=1)
            
            if not results:
                return None
                
            doc, distance = results[0]
            # Ignore dummy initialization document
            if doc.metadata.get("type") == "sys":
                return None

            if distance <= self.distance_threshold:
                cache_key_id = doc.metadata.get("cache_key_id")
                if not cache_key_id:
                    return None
                    
                # Fetch payload from Redis/Fallback
                payload_str = await self.redis.get(f"semcache:{cache_key_id}")
                if payload_str:
                    logger.info(f"Semantic Cache Hit for query '{query}' (Distance: {distance:.4f})")
                    return json.loads(payload_str)
        except Exception as e:
            logger.error(f"Semantic cache lookup failure: {str(e)}")
            
        return None

    async def save(
        self,
        department_id: uuid.UUID,
        query: str,
        response_content: str,
        citations: Optional[list] = None,
        confidence_score: Optional[float] = None
    ) -> None:
        """Store query, response, and citations in the semantic cache."""
        try:
            db = self._load_or_create_cache_index(department_id)
            
            cache_key_id = str(uuid.uuid4())
            
            # 1. Store vector mapping in local FAISS
            cache_doc = LC_Document(
                page_content=query,
                metadata={"cache_key_id": cache_key_id}
            )
            db.add_documents(documents=[cache_doc])
            db.save_local(self._get_faiss_path(department_id))
            
            # 2. Store payload in Redis/Fallback
            payload = {
                "content": response_content,
                "citations": citations or [],
                "confidence_score": confidence_score
            }
            # Cache duration: 24 hours (86400 seconds)
            await self.redis.setex(f"semcache:{cache_key_id}", 86400, json.dumps(payload))
            logger.info(f"Saved query response to semantic cache under ID {cache_key_id}")
        except Exception as e:
            logger.error(f"Failed to write to semantic cache: {str(e)}")
