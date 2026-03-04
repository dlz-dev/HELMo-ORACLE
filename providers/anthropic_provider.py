"""
Anthropic provider — Claude models.
Dependency: langchain-anthropic
"""

from .base import BaseLLMProvider
from langchain_core.language_models.chat_models import BaseChatModel


class AnthropicProvider(BaseLLMProvider):

    @classmethod
    def available_models(cls) -> list[str]:
        return [
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
        ]

    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Install langchain-anthropic: pip install langchain-anthropic")

        if not self.api_key:
            raise ValueError("Anthropic API key is missing. Set it in config.yaml or ANTHROPIC_API_KEY env var.")

        return ChatAnthropic(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
        )

    def __init__(self, model: str, temperature: float, api_key: str):
        super().__init__(model, temperature)
        self.api_key = api_key