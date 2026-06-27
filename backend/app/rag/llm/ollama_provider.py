import json
import httpx
from typing import AsyncGenerator, List, Dict
from app.core.config import settings
from app.utils.logger import logger
from app.rag.llm.base import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    """LLM Provider implementation wrapping connection to local Ollama engine."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.LLM_MODEL
        self.timeout = httpx.Timeout(60.0, connect=5.0)

    async def check_health(self) -> bool:
        """Ping local Ollama engine to verify health connection."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama provider health check failed: {str(e)}")
            return False

    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0
    ) -> AsyncGenerator[str, None]:
        """Call Ollama /api/chat and stream response tokens."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096  # Context window size
            }
        }
        
        url = f"{self.base_url}/api/chat"
        logger.info(f"Submitting chat request to Ollama: {url} (Model: {self.model}, Temp: {temperature})")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Ollama server returned error status {response.status_code}: {error_text.decode('utf-8')}")
                        yield f"Error: Ollama service returned status {response.status_code}."
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError as jde:
                            logger.error(f"Failed to parse Ollama stream JSON line: {line} | Error: {str(jde)}")
                            continue
        except httpx.ConnectError as ce:
            logger.error(f"Could not connect to Ollama service: {str(ce)}")
            yield "Error: Local Ollama service is unreachable. Please ensure Ollama is running."
        except Exception as e:
            logger.error(f"Unexpected error in Ollama stream generation: {str(e)}", exc_info=True)
            yield f"Error: Inference pipeline exception occurred: {str(e)}"
