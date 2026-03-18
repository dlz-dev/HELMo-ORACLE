"""
Groq provider mapping for fast cloud inference (LLaMA, Mixtral, Gemma).
"""

from langchain_core.language_models.chat_models import BaseChatModel

from .base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    """
    Implementation of the BaseLLMProvider for the Groq API.
    """

    def __init__(self, model: str, temperature: float, api_key: str) -> None:
        super().__init__(model, temperature)
        self.api_key = api_key

    def get_llm(self) -> BaseChatModel:
        """
        Returns an instance of ChatGroq.
        """
        # Lazy import to prevent hard dependency crashes if the package is missing.
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("Install langchain-groq: pip install langchain-groq")

        if not self.api_key:
            raise ValueError("Groq API key is missing. Set it in config or environment.")

        return ChatGroq(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
        )

    @classmethod
    def available_models(cls) -> list[str]:
        """
        Returns a list of default Groq models available.
        """
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]