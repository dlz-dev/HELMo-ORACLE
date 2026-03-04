"""
Ollama provider — local models running via Ollama.
No API key required. Ollama must be running locally (default: http://localhost:11434).
Dependency: langchain-ollama
"""

from .base import BaseLLMProvider
from langchain_core.language_models.chat_models import BaseChatModel

# Default models — user can override via config.yaml (ollama.models)
DEFAULT_MODELS = [
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

    @classmethod
    def available_models(cls) -> list[str]:
        return DEFAULT_MODELS

    def get_llm(self) -> BaseChatModel:
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError("Install langchain-ollama: pip install langchain-ollama")

        return ChatOllama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
        )

    def __init__(self, model: str, temperature: float, base_url: str = "http://localhost:11434"):
        super().__init__(model, temperature)
        self.base_url = base_url