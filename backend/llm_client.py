"""Unified LLM client supporting Ollama and OpenAI."""

import httpx
import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client supporting multiple providers.

    Supports:
    - Ollama (local, free)
    - OpenAI (API, paid)
    - Groq (API, free tier available)

    The provider is selected via the LLM_PROVIDER environment variable.
    """

    def __init__(self):
        self.provider = settings.llm_provider
        if self.provider == "ollama":
            self.model = settings.llm_model
        elif self.provider == "openai":
            self.model = settings.openai_model
        elif self.provider == "groq":
            self.model = settings.groq_model
        else:
            self.model = settings.llm_model
        logger.info(f"LLM Client initialized: provider={self.provider}, model={self.model}")

    async def generate(self, prompt: str, timeout: float = 120.0) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the model
            timeout: Request timeout in seconds

        Returns:
            The model's response as a string

        Raises:
            ValueError: If the provider is unknown
            httpx.HTTPError: If the API request fails
        """
        if self.provider == "ollama":
            return await self._generate_ollama(prompt, timeout)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, timeout)
        elif self.provider == "groq":
            return await self._generate_groq(prompt, timeout)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _generate_ollama(self, prompt: str, timeout: float) -> str:
        """Generate using Ollama API."""
        url = f"{settings.ollama_base_url}/api/generate"

        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug(f"Calling Ollama at {url}")
            response = await client.post(
                url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2048,
                    }
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def _generate_openai(self, prompt: str, timeout: float) -> str:
        """Generate using OpenAI API."""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        url = "https://api.openai.com/v1/chat/completions"

        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug("Calling OpenAI API")
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,
                    "max_tokens": 2048,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _generate_groq(self, prompt: str, timeout: float) -> str:
        """Generate using Groq API (OpenAI-compatible)."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        url = "https://api.groq.com/openai/v1/chat/completions"

        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.debug("Calling Groq API")
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,
                    "max_tokens": 2048,
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def health_check(self) -> bool:
        """Check if the LLM service is available."""
        try:
            if self.provider == "ollama":
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{settings.ollama_base_url}/api/tags")
                    return response.status_code == 200
            elif self.provider == "openai":
                # Just check if API key is configured
                return bool(settings.openai_api_key)
            elif self.provider == "groq":
                # Just check if API key is configured
                return bool(settings.groq_api_key)
            return False
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False


# Singleton instance
llm = LLMClient()
