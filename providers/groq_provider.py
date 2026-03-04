"""
Groq provider — fast cloud inference (LLaMA, Mixtral, Gemma via Groq API).
Dependency: langchain-groq
"""

from .base import BaseLLMProvider
from langchain_core.language_models.chat_models import BaseChatModel


class GroqProvider(BaseLLMProvider):

    @classmethod
    def available_models(cls) -> list[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]

    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("Install langchain-groq: pip install langchain-groq")

        if not self.api_key:
            raise ValueError("Groq API key is missing. Set it in config.yaml or GROQ_API_KEY env var.")

        return ChatGroq(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
        )

    def __init__(self, model: str, temperature: float, api_key: str):
        super().__init__(model, temperature)
        self.api_key = api_key