"""
Ollama provider mapping for local models.
No API key required. Ollama must be running locally.
"""

from langchain_core.language_models.chat_models import BaseChatModel

from .base import BaseLLMProvider

# Default models — user can override via config (ollama.models)
DEFAULT_MODELS: list[str] = [
    "llama3.1",
    "llama3.2",
    "mistral",
    "mistral-nemo",
    "gemma3:12b",
    "qwen2.5:72b",
    "deepseek-r1:70b",
    "gpt-oss:120b",
]


class OllamaProvider(BaseLLMProvider):
    """
    Implementation of the BaseLLMProvider for local Ollama instances.
    """

    def __init__(self, model: str, temperature: float, base_url: str = "http://localhost:11434") -> None:
        super().__init__(model, temperature)
        self.base_url = base_url

    def get_llm(self) -> BaseChatModel:
        """
        Returns an instance of ChatOllama.
        """
        # Lazy import to prevent hard dependency crashes if the package is missing.
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError("Install langchain-ollama: pip install langchain-ollama")

        return ChatOllama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
        )

    @classmethod
    def available_models(cls) -> list[str]:
        """
        Returns a list of default local Ollama models available.
        """
        return DEFAULT_MODELS