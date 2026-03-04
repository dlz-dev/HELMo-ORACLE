"""
Base class for all LLM providers.
Each provider must implement the `get_llm` method.
"""

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class BaseLLMProvider(ABC):
    """
    Abstract base class that every LLM provider must inherit.
    Ensures a consistent interface across all providers.
    """

    def __init__(self, model: str, temperature: float = 0):
        self.model = model
        self.temperature = temperature

    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """
        Returns a LangChain-compatible chat model instance.
        Must be implemented by each provider subclass.
        """
        pass

    @classmethod
    @abstractmethod
    def available_models(cls) -> list[str]:
        """
        Returns the list of models available for this provider.
        Used to populate the Streamlit sidebar selector.
        """
        pass
