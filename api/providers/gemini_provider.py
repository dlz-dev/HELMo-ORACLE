"""
Google Gemini provider mapping for cloud models via Google AI Studio.
"""

from langchain_core.language_models.chat_models import BaseChatModel

from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    """
    Implementation of the BaseLLMProvider for Google's Gemini API.
    """

    def __init__(self, model: str, temperature: float, api_key: str) -> None:
        super().__init__(model, temperature)
        self.api_key = api_key

    def get_llm(self) -> BaseChatModel:
        """
        Returns an instance of ChatGoogleGenerativeAI.
        """
        # Lazy import to prevent hard dependency crashes if the package is missing.
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Install langchain-google-genai: pip install langchain-google-genai")

        if not self.api_key:
            raise ValueError("Gemini API key is missing. Set it in config or environment.")

        return ChatGoogleGenerativeAI(
            model=self.model,
            temperature=self.temperature,
            google_api_key=self.api_key,
        )

    @classmethod
    def available_models(cls) -> list[str]:
        """
        Returns a list of default Gemini models available.
        """
        return [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]