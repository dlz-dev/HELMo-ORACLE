"""
LLM Providers factory for initializing LangChain-compatible models.
"""

import os
from typing import Any

from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider


PROVIDERS = {
    "groq": ("⚡ Groq (Cloud)", GroqProvider),
    "openai": ("🤖 OpenAI / ChatGPT", OpenAIProvider),
    "anthropic": ("🧠 Anthropic / Claude", AnthropicProvider),
    "gemini": ("✨ Google Gemini", GeminiProvider),
    "ollama": ("🏠 Ollama (Local)", OllamaProvider),
}

PROVIDER_LABELS: dict[str, str] = {k: v[0] for k, v in PROVIDERS.items()}


def get_available_models(provider_key: str, config: dict[str, Any]) -> list[str]:
    """
    Returns the model list for a given provider, prioritizing config overrides.
    """
    _, provider_cls = PROVIDERS[provider_key]

    provider_cfg = config.get("llm", {}).get(provider_key, {})
    custom_models = provider_cfg.get("models")

    if custom_models:
        return custom_models
        
    return provider_cls.available_models()


def get_llm(provider_key: str, model: str, config: dict[str, Any]) -> Any:
    """
    Instantiates and returns a LangChain-compatible LLM.
    """
    if provider_key not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider_key}'. Available: {list(PROVIDERS.keys())}")

    _, provider_cls = PROVIDERS[provider_key]
    provider_cfg = config.get("llm", {}).get(provider_key, {})
    temperature = config.get("llm", {}).get("temperature", 0.0)

    if provider_key == "ollama":
        base_url = provider_cfg.get("base_url", "http://localhost:11434")
        return provider_cls(model=model, temperature=temperature, base_url=base_url).get_llm()

    env_map = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }
    
    api_key = provider_cfg.get("api_key") or os.environ.get(env_map[provider_key], "")
    return provider_cls(model=model, temperature=temperature, api_key=api_key).get_llm()