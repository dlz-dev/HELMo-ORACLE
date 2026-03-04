import os
import yaml
from langchain_groq import ChatGroq


def load_api_key() -> str:
    """Charge la clé API depuis le config.yaml."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "..", "config", "config.yaml")

    with open(config_path, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config["api"]["api_key"]


def is_valid_lore_file(file_path: str, api_key: str) -> bool:
    """
    Le Gardien IA : Lit un extrait du fichier et détermine s'il est dans le thème.
    """
    try:
        # On lit seulement les 1500 premiers caractères
        with open(file_path, 'r', encoding='utf-8') as f:
            sample_text = f.read(1500)
    except Exception as e:
        print(f"⚠️ Erreur de lecture pour la validation : {e}")
        return False

    # Initialisation du modèle
    llm = ChatGroq(
        model="gemma2-9b-it",
        temperature=0,
        api_key=api_key
    )

    prompt = f"""Tu es le Gardien des Archives d'un jeu vidéo.
Ta mission est de déterminer si le texte ci-dessous appartient à l'univers d'un jeu de rôle/MMORPG (fantaisie, quêtes, monstres, objets magiques, statistiques, Dofus, Wakfu, Amakna, etc.).
Si le texte parle de cuisine réelle, de code informatique hors contexte jeu, de factures, ou de tout autre sujet hors-jeu, tu dois le rejeter.

Texte à analyser :
---
{sample_text}
---

Réponds STRICTEMENT par le mot OUI ou par le mot NON, sans aucune autre ponctuation ni explication."""

    try:
        response = llm.invoke(prompt)
        # On nettoie la réponse et on cherche le mot OUI
        return "OUI" in response.content.strip().upper()
    except Exception as e:
        print(f"⚠️ Erreur API du Gardien : {e}")
        return False