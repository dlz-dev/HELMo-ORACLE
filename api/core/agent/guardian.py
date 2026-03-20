import os
from typing import Optional

from ..utils.utils import load_config, _GUARDIAN_PROMPT


# Import delayed to avoid circular dependency
def get_llm_for_guardian():
    from ...providers import get_llm
    return get_llm


def is_valid_lore_file(file_path: str, api_key: Optional[str] = None) -> bool:
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

    # Bypass text reading for PDFs (auto-accept for Unstructured conversion)
    if extension == '.pdf':
        print(f"  📄 [{fname}] Binary format (PDF) → Auto-Accepted for Unstructured conversion")
        return True

    # Attempt to read a sample of the file to evaluate its content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample_text = f.read(1500)
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                sample_text = f.read(1500)
        except Exception as e:
            print(f"  🚫 [{fname}] Read error: {e} → REJECTED (Unreadable file)")
            return False
    except Exception as e:
        print(f"  🚫 [{fname}] Unexpected read error: {e} → REJECTED")
        return False

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
        answer = response.content.strip().upper()

        # Note: We keep "OUI" since _GUARDIAN_PROMPT instructs the LLM in French
        verdict = "OUI" in answer

        status = "✅ ACCEPTED" if verdict else "❌ REJECTED"
        print(f"  🛡️  Guardian [{fname}] via {provider_key}/{model} → '{response.content.strip()}' → {status}")

        return verdict
    except Exception as e:
        print(f"  🚫 [{fname}] API error during validation: {e} → REJECTED (Not validated)")
        return False