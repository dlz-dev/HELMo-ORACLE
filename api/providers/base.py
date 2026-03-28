"""
Base class for all LLM providers.

Each provider must implement the `get_llm` method to return a LangChain-compatible
chat model, and `available_models` to list supported models.
"""

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class BaseLLMProvider(ABC):
    """
    Abstract base class ensuring a consistent interface across all LLM providers.
    """

    def __init__(self, model: str, temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """
        Returns a LangChain-compatible chat model instance.
        """
        pass

    @classmethod
    @abstractmethod
    def available_models(cls) -> list[str]:
        """
        Returns the list of models available for this provider.
        """
        pass
