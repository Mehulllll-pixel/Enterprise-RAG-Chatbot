from typing import List, Optional
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.core.config import settings
from app.utils.logger import logger

class EmbeddingService:
    """Service utilizing sentence-transformers to generate semantic embeddings locally."""
    _instance: Optional[HuggingFaceEmbeddings] = None

    @classmethod
    def get_embeddings_model(cls) -> HuggingFaceEmbeddings:
        """Get or initialize the HuggingFaceEmbeddings model singleton."""
        if cls._instance is None:
            model_name = f"sentence-transformers/{settings.EMBEDDING_MODEL}"
            logger.info(f"Loading local SentenceTransformer model: {model_name}...")
            try:
                # Load the model locally using HuggingFace cache directory (fully offline once cached)
                cls._instance = HuggingFaceEmbeddings(
                    model_name=model_name,
                    model_kwargs={"device": "cpu"}, # Force cpu for CPU-only local environments
                    encode_kwargs={"normalize_embeddings": True} # Cosine similarity
                )
                logger.info("SentenceTransformer model successfully loaded.")
            except Exception as e:
                logger.error(f"Failed to load sentence-transformer model: {str(e)}")
                raise RuntimeError(f"Embedding initialization error: {str(e)}")
        return cls._instance

    def __init__(self):
        self.model = self.get_embeddings_model()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate numerical embedding vectors for a list of string contents."""
        if not texts:
            return []
        try:
            return self.model.embed_documents(texts)
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate a single embedding vector for a natural language user query."""
        try:
            return self.model.embed_query(query)
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise
