"""
LLM Providers factory.

Usage:
    from providers import get_llm, PROVIDER_LABELS

    llm = get_llm(provider_key="groq", model="llama-3.3-70b-versatile", config=config)
"""

from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider

# Maps config key → (display label, provider class)
PROVIDERS = {
    "groq":      ("⚡ Groq (Cloud)",       GroqProvider),
    "openai":    ("🤖 OpenAI / ChatGPT",   OpenAIProvider),
    "anthropic": ("🧠 Anthropic / Claude", AnthropicProvider),
    "gemini":    ("✨ Google Gemini",       GeminiProvider),
    "ollama":    ("🏠 Ollama (Local)",      OllamaProvider),
}

# For Streamlit selectbox display
PROVIDER_LABELS = {k: v[0] for k, v in PROVIDERS.items()}


def get_available_models(provider_key: str, config: dict) -> list[str]:
    """
    Returns the model list for a given provider.
    If the config defines a custom list (e.g. ollama.models), it takes priority.
    """
    _, provider_cls = PROVIDERS[provider_key]

    # Allow custom model list override in config.yaml
    provider_cfg = config.get("llm", {}).get(provider_key, {})
    custom_models = provider_cfg.get("models")

    return custom_models if custom_models else provider_cls.available_models()


def get_llm(provider_key: str, model: str, config: dict):
    """
    Instantiates and returns a LangChain-compatible LLM from the given provider.

    Args:
        provider_key: One of "groq", "openai", "anthropic", "gemini", "ollama"
        model:        Model name string
        config:       Parsed config.yaml dict (or st.secrets equivalent)

    Returns:
        A LangChain BaseChatModel instance ready for use with LangGraph.
    """
    if provider_key not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{provider_key}'. "
            f"Available: {list(PROVIDERS.keys())}"
        )

    _, provider_cls = PROVIDERS[provider_key]
    provider_cfg = config.get("llm", {}).get(provider_key, {})
    temperature = config.get("llm", {}).get("temperature", 0)

    if provider_key == "ollama":
        base_url = provider_cfg.get("base_url", "http://localhost:11434")
        return provider_cls(model=model, temperature=temperature, base_url=base_url).get_llm()

    else:
        import os
        # API key: config.yaml > environment variable
        env_map = {
            "groq":      "GROQ_API_KEY",
            "openai":    "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini":    "GOOGLE_API_KEY",
        }
        api_key = provider_cfg.get("api_key") or os.environ.get(env_map[provider_key], "")
        return provider_cls(model=model, temperature=temperature, api_key=api_key).get_llm()