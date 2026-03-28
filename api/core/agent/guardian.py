import os
from typing import Optional

import pypdf
from core.utils.utils import load_config, _GUARDIAN_PROMPT


# Import delayed to avoid circular dependency
def get_llm_for_guardian():
    from providers import get_llm
    return get_llm


def is_valid_lore_file(file_path: str, api_key: Optional[str] = None) -> tuple[bool, str]:
    """
    Validates a file using the LLM configured in config.yaml under [guardian].

    The `api_key` parameter is maintained for backward compatibility with
    legacy ingestion scripts but is no longer used directly; the key is
    read from the configuration via `get_llm()`.

    Args:
        file_path (str): The absolute or relative path to the file.
        api_key (Optional[str]): Legacy parameter, currently unused.

    Returns:
        bool: True if the file is accepted by the Guardian or is a known
              binary format, False otherwise.

    Raises:
        RuntimeError: If the Guardian LLM configuration is invalid or unreachable.
    """
    fname = os.path.basename(file_path)
    extension = os.path.splitext(fname)[1].lower()

    sample_text = ""

    # Text reading for PDFs
    try:
        if extension == ".pdf":
            reader = pypdf.PdfReader(file_path)

            # We read page by page until we reach 1,500 characters
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    sample_text += extracted + "\n"

                if len(sample_text) >= 1500:
                    break

            sample_text = sample_text[:1500]

            # Security: scanning images without text
            if not sample_text.strip():
                print(f"  🚫 [{fname}] PDF vide ou composé uniquement d'images → REJECTED")
                return False, "PDF illisible (aucun texte extrait)."

        else:
            # Attempt to read a sample of the file to evaluate its content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    sample_text = f.read(1500)
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    sample_text = f.read(1500)

    except Exception as e:
        print(f"  🚫 [{fname}] Erreur de lecture physique du fichier: {e} → REJECTED")
        return False, f"Fichier illisible: {e}"

    # Load configuration and initialize the LLM
    try:
        config = load_config()
        guardian_cfg = config.get("guardian", {})
        provider_key = guardian_cfg.get("provider", "groq")
        model = guardian_cfg.get("model", "llama-3.1-8b-instant")
        get_llm = get_llm_for_guardian()
        llm = get_llm(provider_key=provider_key, model=model, config=config)
    except Exception as e:
        raise RuntimeError(
            f"🚫 Guardian unavailable ({provider_key}/{model}): {e}\n"
            f"   Ingestion halted — no files will be added without validation."
        ) from e

    # Query the LLM for validation
    prompt = _GUARDIAN_PROMPT.format(sample_text=sample_text)

    try:
        response = llm.invoke(prompt)
        answer = response.content.strip()
        lines = answer.splitlines()

        # Note: We keep "OUI" since _GUARDIAN_PROMPT instructs the LLM in French
        verdict_str = lines[0].strip().upper()
        verdict = verdict_str.startswith("OUI")

        explication = lines[1].strip() if len(lines) > 1 else "Aucune explication fournie."

        status = "✅ ACCEPTED" if verdict else "❌ REJECTED"
        print(f"  🛡️  Guardian [{fname}] via {provider_key}/{model} → '{response.content.strip()}' → {status}")

        return verdict, explication
    except Exception as e:
        print(f"  🚫 [{fname}] API error during validation: {e} → REJECTED (Not validated)")
        return False, "Erreur API"
