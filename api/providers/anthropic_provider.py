"""
Anthropic provider mapping for Claude models.
"""

from langchain_core.language_models.chat_models import BaseChatModel

from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """
    Implementation of the BaseLLMProvider for Anthropic's API.
    """

    def __init__(self, model: str, temperature: float, api_key: str) -> None:
        super().__init__(model, temperature)
        self.api_key = api_key

    def get_llm(self) -> BaseChatModel:
        """
        Returns an instance of ChatAnthropic.
        """
        # Lazy import to prevent hard dependency crashes if the package is missing.
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Install langchain-anthropic: pip install langchain-anthropic")

        if not self.api_key:
            raise ValueError("Anthropic API key is missing. Set it in config or environment.")

        return ChatAnthropic(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
        )

    @classmethod
    def available_models(cls) -> list[str]:
        """
        Returns a list of default Anthropic models available.
        """
        return [
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
        ]
