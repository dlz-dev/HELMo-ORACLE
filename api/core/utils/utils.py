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

# Ensure the base directory is in the system path for module imports
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

_CONTEXT_PROMPT = """
Tu analyses un document provenant des archives du jeu Dofus (MMORPG).
Écris en 2-3 phrases maximum une description du CONTENU GLOBAL de ce document.
Cette description sera utilisée comme contexte pour chaque fragment du document.

Sois précis : mentionne le type de données (armes, monstres, quêtes, lore historique...),
les entités principales couvertes, et l'utilité pour un joueur Dofus.

Document (extrait des 3000 premiers caractères) :
---
{sample}
---

Réponds avec UNIQUEMENT la description, sans introduction ni ponctuation finale.
"""

_GUARDIAN_PROMPT = """
Tu es le Gardien des Archives du jeu Dofus (MMORPG fantasy d'Ankama).
Ta mission : déterminer si le contenu ci-dessous fait partie de l'univers Dofus ou d'un MMORPG fantasy.

RÈGLE IMPORTANTE : Le contenu peut se présenter sous n'importe quel format :
- Texte narratif (description de lore, histoire du monde)
- JSON ou CSV avec des noms d'armes, monstres, sorts, équipements, classes, objets
- Statistiques de jeu (dommages, PA, PM, pods, résistances, niveaux)
- URLs vers dofus.com ou ankama.com (= preuve formelle que c'est du lore Dofus)
- Noms propres Dofus : Amakna, Bonta, Brakmar, Pandala, Iop, Osamodas, Sacrieur...

EXEMPLES ACCEPTÉS → répondre OUI :
- {{"nom": "Hache Ériphe", "Type": "Hache", "url": "https://www.dofus.com/..."}}
- "Mazic est le Méryde de la naissance..."
- "Chaque personnage dans Dofus possède un alignement..."
- Données CSV sur les classes, donjons ou monstres du jeu

EXEMPLES REJETÉS → répondre NON :
- Une recette de cuisine réelle
- Du code source informatique sans rapport avec un jeu
- Une facture ou document administratif
- Un texte sur de l'informatique, des sciences ou qui n'a pas de lien avec un MMORPG ou de la fantasy

Contenu à analyser :
---
{sample_text}
---

Tu dois répondre STRICTEMENT sous ce format, sur deux lignes :
Ligne 1 : OUI ou NON
Ligne 2 : Un résumé court (max 20 mots) du pourquoi.
"""

_SUMMARY_PROMPT = """
You are summarizing a conversation between a user and an AI Oracle specialized in the Dofus game.

Your task: write a CONCISE summary (5-10 sentences max) of the conversation below.
Focus on:
- The user's main topics and questions
- Key information the Oracle provided
- Any preferences or context the user mentioned (character class, level, goals...)

This summary will be injected into future conversations so the Oracle remembers the context.
Write in the same language as the conversation. Be factual, not narrative.

Existing summary (if any):
{existing_summary}

New messages to integrate:
{new_messages}

Write the updated summary now:
"""


@lru_cache(maxsize=1)
def load_config() -> Dict[str, Any]:
    """Builds the configuration dictionary from environment variables.

    Replaces the former config.yaml approach. All values have the same
    defaults as the example YAML so existing code is unaffected.

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
                "server_url": os.environ.get("UNSTRUCTURED_SERVER_URL",
                                             "https://api.unstructuredapp.io/general/v0/general"),
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

    Priority:
      1. prompt.txt file (if it exists — kept for convenience)
      2. SYSTEM_PROMPT environment variable

    Returns:
        str: The raw string content of the system prompt.
    """
    if PROMPT_PATH.exists():
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    prompt = os.environ.get("SYSTEM_PROMPT", "")
    if not prompt:
        raise RuntimeError(
            "No system prompt found. Create config/prompt.txt or set SYSTEM_PROMPT env var."
        )
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
    text = re.sub(r"^(Analyse|Analysis|Context)\s*:?", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# Search constants — read once at import time
_cfg = load_config()
_SEARCH_CFG = _cfg.get("search", {})
K_SEMANTIC = _SEARCH_CFG.get("k_semantic", 10)
K_BM25 = _SEARCH_CFG.get("k_bm25", 10)
K_FINAL = _SEARCH_CFG.get("k_final", 5)
RRF_K = _SEARCH_CFG.get("rrf_k", 60)
FTS_LANG = _SEARCH_CFG.get("fts_language", "french")
