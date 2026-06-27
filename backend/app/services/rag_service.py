import time
import uuid
from typing import AsyncGenerator, List, Dict, Any, Tuple
import json

from app.rag.llm.llm_service import LLMService
from app.rag.vectorstore.vector_service import VectorService
from app.rag.semantic_cache.cache_service import SemanticCacheService
from app.rag.prompts import SYSTEM_RAG_PROMPT, REFORMULATION_PROMPT_TEMPLATE, format_history_for_prompt
from app.utils.logger import logger

class RAGService:
    """Orchestrator coordinating semantic search retrievals, grounding prompt compilation, and LLM text generation."""
    
    def __init__(self, db_session: Any, redis_client: Any):
        self.db = db_session
        self.redis = redis_client
        self.vector_service = VectorService()
        self.llm_service = LLMService()
        self.cache_service = SemanticCacheService(redis_client)

    async def _reformulate_query(self, query: str, history: List[Dict[str, str]]) -> str:
        """Compress multi-turn chat history and follow up questions into a standalone query."""
        if not history:
            return query

        formatted_history = format_history_for_prompt(history)
        prompt = REFORMULATION_PROMPT_TEMPLATE.format(
            chat_history=formatted_history,
            question=query
        )
        
        logger.info(f"Reformulating follow-up query based on history of {len(history)} turns.")
        
        # We fetch the reformulated question from the LLM (temperature = 0 for consistency)
        # We can call Ollama synchronously or accumulate a tiny stream
        # Let's accumulate the stream tokens for rephrasing
        tokens = []
        messages = [{"role": "user", "content": prompt}]
        async for token in self.llm_service.generate_chat_stream(messages, temperature=0.0):
            tokens.append(token)
            
        reformulated = "".join(tokens).strip()
        # Fallback to raw query if reformulation is empty or error
        if not reformulated or "error" in reformulated.lower():
            logger.warning("Query reformulation yielded empty string or error. Falling back to raw query.")
            return query
            
        logger.info(f"Reformulated standalone query: '{reformulated}'")
        return reformulated

    async def generate_response_stream(
        self,
        department_id: uuid.UUID,
        query: str,
        history: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Orchestrate cache lookup, similarity search, prompt assembly, and SSE streaming output."""
        start_time = time.time()
        
        # 1. Reformulate search query if history exists
        search_query = await self._reformulate_query(query, history)
        
        # 2. Check Semantic Cache
        cached_result = await self.cache_service.lookup(department_id, search_query)
        if cached_result:
            # Yield cached content
            yield json.dumps({"type": "token", "content": cached_result["content"]})
            # Yield cached metadata
            yield json.dumps({
                "type": "metadata",
                "citations": cached_result["citations"],
                "confidence_score": cached_result["confidence_score"],
                "related_questions": self._generate_related_questions(search_query, cached_result["content"]),
                "cached": True,
                "latency_ms": int((time.time() - start_time) * 1000)
            })
            return

        # 3. Retrieve relevant chunks from FAISS
        db_faiss = self.vector_service._load_or_create_index(department_id)
        faiss_vector_count = db_faiss.index.ntotal
        logger.info(f"FAISS total vector count in index (including dummy): {faiss_vector_count}")

        raw_matches = self.vector_service.similarity_search(
            department_id=department_id,
            query=search_query,
            k=4
        )
        
        logger.info(f"Raw FAISS similarity matches retrieved for query '{search_query}':")
        for i, (doc, score) in enumerate(raw_matches):
            safe_text = doc.page_content[:80].encode('ascii', 'replace').decode('ascii')
            logger.info(f" - Hit {i+1}: Score={score:.4f} | Source={doc.metadata.get('filename')} (Page {doc.metadata.get('page_number')}) | Text={safe_text}...")

        # Filter matches (LangChain FAISS returns Euclidean L2 distance squared, range 0.0 to 4.0)
        # An L2 distance of 1.6 corresponds to a cosine similarity of 0.2 (2 - 2 * 0.2 = 1.6)
        valid_matches = []
        for doc, score in raw_matches:
            if doc.metadata.get("type") == "sys":
                continue # Skip initialization dummy vector
            if score <= 1.60:
                valid_matches.append((doc, score))
            else:
                logger.info(f" - Discarded Hit (distance {score:.4f} > 1.60): Source={doc.metadata.get('filename')}")

        logger.info(f"Valid grounding chunks retained: {len(valid_matches)}")

        # Calculate confidence score
        if valid_matches:
            # Average similarity score = Mean of (1 - normalized distance/2)
            avg_distance = sum(score for _, score in valid_matches) / len(valid_matches)
            confidence_score = max(0.0, min(1.0, 1.0 - (avg_distance / 2.0)))
        else:
            confidence_score = 0.0

        # Assemble citations
        citations = []
        context_blocks = []
        for i, (doc, score) in enumerate(valid_matches):
            citation_id = f"REF-{i+1}"
            citations.append({
                "id": citation_id,
                "document_id": doc.metadata.get("document_id"),
                "version_id": doc.metadata.get("version_id"),
                "filename": doc.metadata.get("filename"),
                "page_number": doc.metadata.get("page_number"),
                "chunk_index": doc.metadata.get("chunk_index"),
                "snippet": doc.page_content[:250],
                "score": float(score)
            })
            context_blocks.append(
                f"Source: {doc.metadata.get('filename')} (Page {doc.metadata.get('page_number')})\n"
                f"Content: {doc.page_content}"
            )

        context_str = "\n\n".join(context_blocks)
        
        # 4. Compile prompt
        system_prompt = SYSTEM_RAG_PROMPT.format(context=context_str if context_str else "No document snippets retrieved.")
        logger.info(f"Final System Prompt compiled for Ollama:\n{system_prompt.encode('ascii', 'replace').decode('ascii')}")
        
        # Build message transcript for Ollama
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history details (last 3 turns to fit context and keep focus)
        for msg in history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Add current reformulated query
        messages.append({"role": "user", "content": search_query})

        # 5. Run LLM stream and yield tokens
        generated_tokens = []
        
        async for token in self.llm_service.generate_chat_stream(messages, temperature=0.0):
            generated_tokens.append(token)
            yield json.dumps({"type": "token", "content": token})

        full_response = "".join(generated_tokens).strip()
        latency_ms = int((time.time() - start_time) * 1000)

        # 6. Save in Semantic Cache if valid response was generated (only cache if we retrieved valid context to avoid caching "not found")
        if valid_matches and full_response and not "sorry" in full_response.lower() and not "do not know" in full_response.lower():
            await self.cache_service.save(
                department_id=department_id,
                query=search_query,
                response_content=full_response,
                citations=citations,
                confidence_score=confidence_score
            )

        # Generate related follow-up questions
        related_questions = self._generate_related_questions(search_query, full_response)

        # 7. Yield final metadata payload
        yield json.dumps({
            "type": "metadata",
            "citations": citations,
            "confidence_score": confidence_score,
            "related_questions": related_questions,
            "cached": False,
            "latency_ms": latency_ms
        })

    def _generate_related_questions(self, query: str, response: str) -> List[str]:
        """Simple rules based heuristic engine to generate relevant follow up questions."""
        # Simple local logic based on queries and keywords (prevents extra slow LLM calls)
        keywords = {
            "work": ["What is the process to request remote work?", "Can I work fully remote?"],
            "security": ["Who manages quarterly security assessments?", "How are database credentials rotated?"],
            "password": ["How do I reset my password?", "What is the security policy on passwords?"],
            "data": ["Where are customer records encrypted?", "What happens during IT security audits?"],
            "policy": ["Where can I view general HR policies?", "Are there exceptions to core days?"]
        }
        
        related = []
        for word, questions in keywords.items():
            if word in query.lower() or word in response.lower():
                related.extend(questions)
                if len(related) >= 3:
                    break
        
        # Default questions fallback
        if not related:
            related = [
                "Can you summarize the key points of this document?",
                "Which parts of this policy apply to my department?",
                "What is the effective date of these guidelines?"
            ]
        return list(set(related))[:3]
