from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict

class BaseLLMProvider(ABC):
    """Abstract base class defining interface for interchangeable LLM providers."""

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if the LLM provider service is healthy and reachable."""
        pass

    @abstractmethod
    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0
    ) -> AsyncGenerator[str, None]:
        """Generate response tokens as a stream from the LLM provider."""
        pass
