import os
from typing import Callable, Any

import pypdf

from core.utils.logger import get_logger
from core.utils.utils import load_config, _GUARDIAN_PROMPT

logger = get_logger(__name__)


def get_llm_for_guardian() -> Callable[..., Any]:
    """
    Import différé pour éviter les dépendances circulaires
    lors du chargement du module.
    """
    from providers import get_llm
    return get_llm


def is_valid_lore_file(file_path: str) -> tuple[bool, str]:
    """
    Valide le contenu d'un fichier via le LLM configuré dans la section [guardian].
    Extrait un échantillon (max 1500 caractères) pour limiter le coût et la taille du prompt.

    Args:
        file_path: Chemin absolu ou relatif du fichier.

    Returns:
        Un tuple (Verdicte booléen, Explication du modèle ou message d'erreur).
    """
    fname: str = os.path.basename(file_path)
    extension: str = os.path.splitext(fname)[1].lower()
    sample_text: str = ""

    try:
        if extension == ".pdf":
            reader = pypdf.PdfReader(file_path)

            for page in reader.pages:
                extracted: str | None = page.extract_text()
                if extracted:
                    sample_text += extracted + "\n"

                if len(sample_text) >= 1500:
                    break

            sample_text = sample_text[:1500]

            # Rejet de sécurité pour les PDF scannés ou images (non océrisés)
            if not sample_text.strip():
                logger.warning(f"[{fname}] PDF vide ou composé uniquement d'images → REJECTED")
                return False, "PDF illisible (aucun texte extrait)."

        else:
            # Fallback sur latin-1 si l'utf-8 échoue pour les fichiers texte/code anciens
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    sample_text = f.read(1500)
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    sample_text = f.read(1500)

    except Exception as e:
        logger.error(f"[{fname}] Erreur de lecture physique du fichier → REJECTED", exc_info=True)
        return False, f"Fichier illisible: {e}"

    try:
        config: dict[str, Any] = load_config()
        guardian_cfg: dict[str, Any] = config.get("guardian", {})
        provider_key: str = guardian_cfg.get("provider", "groq")
        model: str = guardian_cfg.get("model", "llama-3.1-8b-instant")

        get_llm: Callable[..., Any] = get_llm_for_guardian()
        llm: Any = get_llm(provider_key=provider_key, model=model, config=config)
    except Exception as e:
        raise RuntimeError(
            f"🚫 Guardian unavailable ({provider_key}/{model}): {e}\n"
            f"   Ingestion halted — no files will be added without validation."
        ) from e

    prompt: str = _GUARDIAN_PROMPT.format(sample_text=sample_text)

    try:
        response: Any = llm.invoke(prompt)
        answer: str = response.content.strip()
        lines: list[str] = answer.splitlines()

        verdict_str: str = lines[0].strip().upper()
        verdict: bool = verdict_str.startswith("OUI")

        explication: str = lines[1].strip() if len(lines) > 1 else "Aucune explication fournie."

        status: str = "ACCEPTED" if verdict else "REJECTED"
        logger.info(f"Guardian [{fname}] via {provider_key}/{model} → {status}")

        return verdict, explication
    except Exception:
        logger.error(f"[{fname}] Erreur API lors de la validation → REJECTED", exc_info=True)
        return False, "Erreur API"
