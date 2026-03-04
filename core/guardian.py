import os
import sys

import yaml

# ── Résolution du chemin pour imports depuis core/ ou racine ─────
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_DIR = os.path.dirname(_CORE_DIR)
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from providers import get_llm


# ─────────────────────────────────────────────────────────────────
# Config loader
# ─────────────────────────────────────────────────────────────────

def _load_config() -> dict:
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


# ─────────────────────────────────────────────────────────────────
# Prompt du Gardien
# ─────────────────────────────────────────────────────────────────

_GUARDIAN_PROMPT = """Tu es le Gardien des Archives du jeu Dofus (MMORPG fantasy d'Ankama).
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

Réponds STRICTEMENT par OUI (contenu Dofus/MMORPG) ou NON (hors-sujet), sans aucune explication."""


# ─────────────────────────────────────────────────────────────────
# Gardien principal
# ─────────────────────────────────────────────────────────────────

def is_valid_lore_file(file_path: str, api_key: str = None) -> bool:
    """
    Valide un fichier via le LLM configuré dans config.yaml [guardian].

    Le paramètre api_key est conservé pour rétro-compatibilité avec
    ingestion.py mais n'est plus utilisé directement — la clé est
    lue depuis le config via get_llm().

    Config yaml utilisée :
        guardian:
          provider: "groq"            # provider du Gardien (indépendant de l'Oracle)
          model: "gemma2-9b-it"       # modèle léger suffisant pour classification
    """
    fname = os.path.basename(file_path)

    # ── Lecture du fichier ────────────────────────────────────────
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample_text = f.read(1500)
    except Exception as e:
        print(f"  🚫 [{fname}] Erreur de lecture : {e} → REFUSÉ (impossible à lire)")
        return False  # fail-strict : on ne peut pas valider ce qu'on ne lit pas

    # ── Chargement config & LLM ───────────────────────────────────
    try:
        config = _load_config()
        guardian_cfg = config.get("guardian", {})
        provider_key = guardian_cfg.get("provider", "groq")
        model = guardian_cfg.get("model", "gemma2-9b-it")
        llm = get_llm(provider_key=provider_key, model=model, config=config)

    except Exception as e:
        # L'API du Gardien est indisponible → on bloque TOUTE l'ingestion
        # pour éviter d'ingérer des fichiers non validés
        raise RuntimeError(
            f"🚫 Gardien indisponible ({provider_key}/{model}) : {e}\n"
            f"   Ingestion interrompue — aucun fichier ne sera ajouté sans validation."
        )

    # ── Appel LLM ────────────────────────────────────────────────
    prompt = _GUARDIAN_PROMPT.format(sample_text=sample_text)

    try:
        response = llm.invoke(prompt)
        answer = response.content.strip().upper()
        verdict = "OUI" in answer

        status = "✅ ACCEPTÉ" if verdict else "❌ REJETÉ"
        print(f"  🛡️  Gardien [{fname}] via {provider_key}/{model} → '{response.content.strip()}' → {status}")

        return verdict

    except Exception as e:
        # Erreur pendant la validation d'UN fichier → on refuse CE fichier
        # mais on laisse l'ingestion continuer pour les autres
        print(f"  🚫 [{fname}] Erreur API durant la validation : {e} → REFUSÉ (non validé)")
        return False  # fail-strict : pas de réponse = pas d'ingestion
