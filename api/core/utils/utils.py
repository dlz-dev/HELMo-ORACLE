"""
Utility module for the RAG pipeline.

Handles path resolutions, configuration loading, and stores core prompts 
used for data extraction and LLM context generation.
"""

import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

# Centralized Path Management
CURRENT_DIR = Path(__file__).resolve().parent
CORE_DIR = CURRENT_DIR.parent
BASE_DIR = CORE_DIR.parent

# RAG Data Directories
DATA_DIR = BASE_DIR / "data"
NEW_FILES_DIR = DATA_DIR / "new_files"
ARCHIVE_DIR = DATA_DIR / "files"
QUARANTINE_DIR = DATA_DIR / "quarantine"

STORAGE_DIR = BASE_DIR / "storage" / "sessions"
PIPELINE_DIR = CURRENT_DIR

PROMPT_PATH = BASE_DIR / "config" / "prompt.txt"
PROMPT_CONTEXT_PATH = BASE_DIR / "config" / "prompt_context.txt"
PROMPT_GUARDIAN_PATH = BASE_DIR / "config" / "prompt_guardian.txt"
PROMPT_SUMMARY_PATH = BASE_DIR / "config" / "prompt_summary.txt"
PROMPT_JUDGE_PATH = BASE_DIR / "config" / "prompt_judge.txt"

# Inject BASE_DIR into sys.path to allow absolute imports from the project root
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Pre-compile regex patterns for performance in text formatting
_FORMAT_PREFIX_PATTERN = re.compile(r"^(Analyse|Analysis|Context)\s*:?", flags=re.IGNORECASE | re.MULTILINE)
_FORMAT_NEWLINE_PATTERN = re.compile(r"\n{3,}")


def _load_prompt_file(path: Path, env_var: str) -> str:
    """Loads prompt text from a file, falling back to an environment variable."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    prompt = os.environ.get(env_var, "")
    if not prompt:
        raise RuntimeError(f"Prompt not found: create {path.name} or set {env_var}.")

    return prompt


@lru_cache(maxsize=1)
def load_context_prompt() -> str:
    return _load_prompt_file(PROMPT_CONTEXT_PATH, "CONTEXT_PROMPT")


@lru_cache(maxsize=1)
def load_guardian_prompt() -> str:
    return _load_prompt_file(PROMPT_GUARDIAN_PATH, "GUARDIAN_PROMPT")


@lru_cache(maxsize=1)
def load_summary_prompt() -> str:
    return _load_prompt_file(PROMPT_SUMMARY_PATH, "SUMMARY_PROMPT")


@lru_cache(maxsize=1)
def load_judge_prompt() -> str:
    return _load_prompt_file(PROMPT_JUDGE_PATH, "JUDGE_PROMPT")


# Cache the loaded prompts at module level to avoid redundant I/O
_CONTEXT_PROMPT = load_context_prompt()
_GUARDIAN_PROMPT = load_guardian_prompt()
_SUMMARY_PROMPT = load_summary_prompt()
_JUDGE_PROMPT = load_judge_prompt()


@lru_cache(maxsize=1)
def load_config() -> Dict[str, Any]:
    """Builds the configuration dictionary from environment variables.

    Returns:
        Dict[str, Any]: The configuration dictionary.
    """
    return {
        "database": {
            "connection_string": os.environ.get("DATABASE_URL", ""),
        },
        "llm": {
            "default_provider": os.environ.get("LLM_DEFAULT_PROVIDER", "groq"),
            "default_model": os.environ.get("LLM_DEFAULT_MODEL", "llama-3.3-70b-versatile"),
            "temperature": float(os.environ.get("LLM_TEMPERATURE", "0")),
            "groq": {"api_key": os.environ.get("GROQ_API_KEY", "")},
            "openai": {"api_key": os.environ.get("OPENAI_API_KEY", "")},
            "anthropic": {"api_key": os.environ.get("ANTHROPIC_API_KEY", "")},
            "gemini": {"api_key": os.environ.get("GOOGLE_API_KEY", "")},
            "unstructured": {
                "api_key": os.environ.get("UNSTRUCTURED_API_KEY", ""),
                "server_url": os.environ.get(
                    "UNSTRUCTURED_SERVER_URL",
                    "https://api.unstructuredapp.io/general/v0/general"
                ),
            },
        },
        "guardian": {
            "provider": os.environ.get("GUARDIAN_PROVIDER", "groq"),
            "model": os.environ.get("GUARDIAN_MODEL", "llama-3.1-8b-instant"),
        },
        "memory": {
            "max_recent_tokens": int(os.environ.get("MAX_RECENT_TOKENS", "1200")),
            "min_recent_messages": int(os.environ.get("MIN_RECENT_MESSAGES", "4")),
        },
        "search": {
            "k_semantic": int(os.environ.get("K_SEMANTIC", "10")),
            "k_bm25": int(os.environ.get("K_BM25", "10")),
            "k_final": int(os.environ.get("K_FINAL", "5")),
            "rrf_k": int(os.environ.get("RRF_K", "60")),
            "fts_language": os.environ.get("FTS_LANG", "french"),
        },
        "cache": {
            "similarity_threshold": float(os.environ.get("CACHE_SIMILARITY_THRESHOLD", "0.92")),
            "ttl_days": int(os.environ.get("CACHE_TTL_DAYS", "30")),
            "max_entries": int(os.environ.get("CACHE_MAX_ENTRIES", "500")),
        },
    }


@lru_cache(maxsize=1)
def load_base_prompt() -> str:
    """Loads the base system prompt.
    Returns:
        str: The raw string content of the system prompt.
    """
    if PROMPT_PATH.exists():
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()

    prompt = os.environ.get("SYSTEM_PROMPT", "")
    if not prompt:
        raise RuntimeError("No system prompt found. Create config/prompt.txt or set SYSTEM_PROMPT env var.")

    return prompt


def load_api_key() -> str:
    """Retrieves the API key for the configured Guardian provider.

    Returns:
        str: The extracted API key, or an empty string if not found.
    """
    config = load_config()
    provider = config.get("guardian", {}).get("provider", "groq")
    return config.get("llm", {}).get(provider, {}).get("api_key", "")


def format_response(text: str) -> str:
    """Cleans up the LLM response formatting.

    Args:
        text (str): The raw text output from the LLM.

    Returns:
        str: The cleaned and formatted text.
    """
    text = _FORMAT_PREFIX_PATTERN.sub("", text).strip()
    return _FORMAT_NEWLINE_PATTERN.sub("\n\n", text)


# Pre-extract search configuration constants at import time
_cfg = load_config()
_SEARCH_CFG = _cfg.get("search", {})

K_SEMANTIC = _SEARCH_CFG.get("k_semantic", 10)
K_BM25 = _SEARCH_CFG.get("k_bm25", 10)
K_FINAL = _SEARCH_CFG.get("k_final", 5)
RRF_K = _SEARCH_CFG.get("rrf_k", 60)
FTS_LANG = _SEARCH_CFG.get("fts_language", "french")
