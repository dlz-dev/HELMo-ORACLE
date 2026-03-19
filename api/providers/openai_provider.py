"""
OpenAI provider mapping for ChatGPT cloud models.
"""

from langchain_core.language_models.chat_models import BaseChatModel

from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    Implementation of the BaseLLMProvider for OpenAI's API.
    """

    def __init__(self, model: str, temperature: float, api_key: str) -> None:
        super().__init__(model, temperature)
        self.api_key = api_key

    def get_llm(self) -> BaseChatModel:
        """
        Returns an instance of ChatOpenAI.
        """
        # Lazy import to prevent hard dependency crashes if the package is missing.
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Install langchain-openai: pip install langchain-openai")

        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Set it in config or environment.")

        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
        )

    @classmethod
    def available_models(cls) -> list[str]:
        """
        Returns a list of default OpenAI models available.
        """
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]