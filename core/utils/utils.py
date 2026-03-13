"""
Utility module for the RAG pipeline.

Handles path resolutions, configuration loading, and stores core prompts 
used for data extraction and LLM context generation.
"""

import sys
from pathlib import Path
from typing import Any, Dict

import yaml

_CURRENT_DIR = Path(__file__).resolve().parent
_CORE_DIR = _CURRENT_DIR.parent
_BASE_DIR = _CORE_DIR.parent

_STORAGE_DIR = _BASE_DIR / "storage" / "sessions"
_CONFIG_PATH = _BASE_DIR / "config" / "config.yaml"
_PIPELINE_DIR = _CURRENT_DIR
_PROMPT_PATH = _BASE_DIR / "config" / "prompt.txt"

# Ensure the base directory is in the system path for module imports
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

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


def _load_config() -> Dict[str, Any]:
    """Loads the YAML configuration file.

    Returns:
        Dict[str, Any]: The parsed configuration dictionary.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_api_key() -> str:
    """Retrieves the API key based on the configured LLM provider.

    Provides backward compatibility for scripts calling this directly. 
    It defaults to the Guardian's provider (falling back to Groq) and 
    supports legacy configuration structures.

    Returns:
        str: The extracted API key, or an empty string if not found.
    """
    config = _load_config()

    # New multi-provider structure
    if "llm" in config:
        provider = config.get("guardian", {}).get("provider", "groq")
        return config.get("llm", {}).get(provider, {}).get("api_key", "")

    return config["api"]["api_key"]
