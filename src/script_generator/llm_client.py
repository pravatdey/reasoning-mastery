"""
LLM Client - Interface for Groq and Ollama language models
"""

import os
from abc import ABC, abstractmethod
from typing import List

from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 4000, temperature: float = 0.7) -> str:
        pass


class GroqClient(BaseLLMClient):
    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY env var. "
                "Get free key at: https://console.groq.com/"
            )
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Initialized Groq client: {model}")
        except ImportError:
            raise ImportError("Please install groq: pip install groq")

    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 4000, temperature: float = 0.7) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=messages,
                max_tokens=max_tokens, temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise


class OllamaClient(BaseLLMClient):
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama2"):
        self.host = host
        self.model = model
        try:
            import ollama
            self.client = ollama.Client(host=host)
            self.client.list()
            logger.info(f"Initialized Ollama client: {model}")
        except ImportError:
            raise ImportError("Please install ollama: pip install ollama")
        except Exception as e:
            logger.warning(f"Ollama connection failed: {e}")

    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 4000, temperature: float = 0.7) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        try:
            response = self.client.generate(
                model=self.model, prompt=full_prompt,
                options={"num_predict": max_tokens, "temperature": temperature}
            )
            return response.get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise


class LLMClient:
    """Unified LLM client with fallback between providers."""

    def __init__(self, provider: str = "groq", **kwargs):
        self.provider = provider
        self.client = None

        if provider == "groq":
            try:
                self.client = GroqClient(**kwargs)
            except Exception as e:
                logger.warning(f"Groq init failed: {e}")

        elif provider == "ollama":
            try:
                self.client = OllamaClient(**kwargs)
            except Exception as e:
                logger.warning(f"Ollama init failed: {e}")

        if self.client is None:
            fallback = "ollama" if provider == "groq" else "groq"
            try:
                self.client = (OllamaClient if fallback == "ollama" else GroqClient)()
                self.provider = fallback
                logger.info(f"Falling back to {fallback}")
            except Exception:
                pass

        if self.client is None:
            raise RuntimeError(
                "No LLM provider available. Set GROQ_API_KEY or run Ollama locally."
            )

        logger.info(f"LLM Client ready: {self.provider}")

    def generate(self, prompt: str, system_prompt: str = None,
                 max_tokens: int = 4000, temperature: float = 0.7) -> str:
        return self.client.generate(
            prompt=prompt, system_prompt=system_prompt,
            max_tokens=max_tokens, temperature=temperature
        )
