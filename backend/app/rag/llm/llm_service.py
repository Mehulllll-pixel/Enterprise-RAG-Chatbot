from typing import AsyncGenerator, List, Dict
from app.core.config import settings
from app.rag.llm.base import BaseLLMProvider
from app.rag.llm.ollama_provider import OllamaProvider
from app.rag.llm.gemini_provider import GeminiProvider

class LLMService(BaseLLMProvider):
    """Facade service acting as factory router for interchangeable LLM providers."""

    def __init__(self):
        provider_name = settings.LLM_PROVIDER.lower()
        if provider_name == "gemini":
            self.provider: BaseLLMProvider = GeminiProvider()
        else:
            self.provider: BaseLLMProvider = OllamaProvider()

    async def check_health(self) -> bool:
        """Forward health check to the active provider."""
        return await self.provider.check_health()

    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0
    ) -> AsyncGenerator[str, None]:
        """Forward streaming request to the active provider."""
        async for chunk in self.provider.generate_chat_stream(messages, temperature):
            yield chunk
