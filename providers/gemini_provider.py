"""
Google Gemini provider — cloud models via Google AI Studio.
Dependency: langchain-google-genai
"""

from .base import BaseLLMProvider
from langchain_core.language_models.chat_models import BaseChatModel


class GeminiProvider(BaseLLMProvider):

    @classmethod
    def available_models(cls) -> list[str]:
        return [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "Install langchain-google-genai: pip install langchain-google-genai"
            )

        if not self.api_key:
            raise ValueError("Gemini API key is missing. Set it in config.yaml or GOOGLE_API_KEY env var.")

        return ChatGoogleGenerativeAI(
            model=self.model,
            temperature=self.temperature,
            google_api_key=self.api_key,
        )

    def __init__(self, model: str, temperature: float, api_key: str):
        super().__init__(model, temperature)
        self.api_key = api_key