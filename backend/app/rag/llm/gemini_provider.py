import json
import httpx
from typing import AsyncGenerator, List, Dict
from app.core.config import settings
from app.utils.logger import logger
from app.rag.llm.base import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    """LLM Provider implementation wrapping Google's Gemini REST API."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.timeout = httpx.Timeout(60.0, connect=10.0)

    async def check_health(self) -> bool:
        """Verify API key and connectivity with Google Gemini."""
        if not self.api_key:
            logger.error("Gemini API key (GEMINI_API_KEY) is not set.")
            return False
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Gemini health check returned status {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Gemini API health check failed: {str(e)}")
            return False

    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0
    ) -> AsyncGenerator[str, None]:
        """Call Gemini streamGenerateContent API and yield chunks."""
        if not self.api_key:
            yield "Error: Gemini API key is missing. Please set GEMINI_API_KEY in your configuration."
            return

        # 1. Translate message roles to Gemini REST structure
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_instruction = {
                    "parts": [{"text": content}]
                }
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role in ["assistant", "model"]:
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature
            }
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?key={self.api_key}"
        logger.info(f"Submitting chat request to Gemini: Model={self.model}, Temp={temperature}")

        try:
            # Build robust buffer accumulator parser to parse streamed JSON arrays
            buffer = ""
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Gemini API returned error status {response.status_code}: {error_text.decode('utf-8')}")
                        yield f"Error: Gemini API returned status {response.status_code}."
                        return

                    async for line in response.aiter_lines():
                        if isinstance(line, bytes):
                            line = line.decode('utf-8')
                        line = line.strip()
                        if not line or line in ["[", "]", ","]:
                            continue
                        if line.startswith(","):
                            line = line[1:].strip()

                        # Accumulate line and try to parse
                        buffer += line
                        try:
                            data = json.loads(buffer)
                            buffer = ""  # Reset buffer on success
                            
                            # Navigate structure to yield text segment
                            candidates = data.get("candidates", [])
                            if candidates:
                                content = candidates[0].get("content", {})
                                parts = content.get("parts", [])
                                if parts:
                                    text = parts[0].get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            # Incomplete JSON segment; continue accumulating
                            continue
        except Exception as e:
            logger.error(f"Unexpected error in Gemini stream generation: {str(e)}", exc_info=True)
            yield f"Error: Gemini inference failed. ({str(e)})"
