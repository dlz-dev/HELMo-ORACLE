"""
Utility module for the RAG pipeline.

Handles path resolutions, configuration loading, and stores core prompts 
used for data extraction and LLM context generation.
"""

import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import streamlit as st
import yaml

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
CONFIG_PATH = BASE_DIR / "config" / "config.yaml"
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
- Un texte sur de l'informatique ou des sciences sans lien avec un MMORPG

Contenu à analyser :
---
{sample_text}
---

Réponds STRICTEMENT par OUI (contenu Dofus/MMORPG) ou NON (hors-sujet), sans aucune explication.
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
    """Loads the YAML configuration file.

    Returns:
        Dict[str, Any]: The parsed configuration dictionary.
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@lru_cache(maxsize=1)
def load_base_prompt() -> str:
    """Loads the base system prompt from the prompt file or Streamlit secrets.
    
    Returns:
        str: The raw string content of the system prompt.
    """
    if PROMPT_PATH.exists():
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return st.secrets["prompts"]["system_prompt"]

def load_api_key() -> str:
    """Retrieves the API key based on the configured LLM provider.

    Provides backward compatibility for scripts calling this directly. 
    It defaults to the Guardian's provider (falling back to Groq) and 
    supports legacy configuration structures.

    Returns:
        str: The extracted API key, or an empty string if not found.
    """
    config = load_config()

    # New multi-provider structure
    if "llm" in config:
        provider = config.get("guardian", {}).get("provider", "groq")
        return config.get("llm", {}).get(provider, {}).get("api_key", "")

    return config["api"]["api_key"]

def format_response(text: str) -> str:
    """Cleans up the LLM response formatting.
    
    Removes leading thought-process tags, strips excessive whitespace, 
    and limits consecutive line breaks.

    Args:
        text (str): The raw text output from the LLM.

    Returns:
        str: The cleaned and formatted text.
    """
    text = re.sub(r"^(Analyse|Analysis|Context)\s*:?", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text

# Extract search variables once to avoid repeated dictionary lookups
_config = load_config()
_SEARCH_CFG = _config.get("search", {})
K_SEMANTIC = _SEARCH_CFG.get("k_semantic", 10)
K_BM25 = _SEARCH_CFG.get("k_bm25", 10)
K_FINAL = _SEARCH_CFG.get("k_final", 5)
RRF_K = _SEARCH_CFG.get("rrf_k", 60)
FTS_LANG = _SEARCH_CFG.get("fts_language", "french")