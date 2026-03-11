import os
import yaml
import sys

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
_CORE_DIR = os.path.dirname(_AGENT_DIR)
_BASE_DIR = os.path.dirname(_CORE_DIR)
_STORAGE_DIR = os.path.join(_BASE_DIR, "storage", "sessions")
_CONFIG_PATH = os.path.join(_BASE_DIR, "config", "config.yaml")
_PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROMPT_PATH = os.path.join(_BASE_DIR, "config", "prompt.txt")

if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

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


def _load_config() -> dict:
    if _BASE_DIR not in sys.path:
        sys.path.insert(0, _BASE_DIR)
    config_path = os.path.join(_BASE_DIR, "config", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_api_key() -> str:
    """
    Rétro-compatibilité pour ingestion.py qui appelle encore load_api_key().
    Retourne la clé du provider par défaut du Gardien (ou Groq en fallback).
    """
    config = _load_config()

    # Nouvelle structure multi-provider
    if "llm" in config:
        provider = config.get("guardian", {}).get("provider", "groq")
        return config["llm"].get(provider, {}).get("api_key", "")

    # Ancienne structure
    return config["api"]["api_key"]
