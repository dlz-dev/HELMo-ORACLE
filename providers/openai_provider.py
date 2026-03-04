"""
OpenAI provider — ChatGPT cloud models.
Dependency: langchain-openai
"""

from .base import BaseLLMProvider
from langchain_core.language_models.chat_models import BaseChatModel


class OpenAIProvider(BaseLLMProvider):

    @classmethod
    def available_models(cls) -> list[str]:
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]

    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Install langchain-openai: pip install langchain-openai")

        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Set it in config.yaml or OPENAI_API_KEY env var.")

        return ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
        )

    def __init__(self, model: str, temperature: float, api_key: str):
        super().__init__(model, temperature)
        self.api_key = api_key