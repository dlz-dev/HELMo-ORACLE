import os
from typing import Callable, Any

import pypdf

from core.utils.logger import get_logger
from core.utils.utils import load_config, _GUARDIAN_PROMPT

logger = get_logger(__name__)


def get_llm_for_guardian() -> Callable[..., Any]:
    """
    Delayed import to avoid circular dependencies
    when loading the module.
    """
    from providers import get_llm
    return get_llm


def is_valid_lore_file(file_path: str) -> tuple[bool, str]:
    """
    Validates the content of a file via the LLM configured in the [guardian] section.
    Extracts a sample (max 1500 characters) to limit cost and prompt size.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        A tuple (Boolean verdict, Model explanation or error message).
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

            # Security rejection for scanned PDFs or images (no OCR)
            if not sample_text.strip():
                logger.warning(f"[{fname}] Empty PDF or composed only of images → REJECTED")
                return False, "Unreadable PDF (no text extracted)."

        else:
            # Fallback to latin-1 if utf-8 fails for legacy text/code files
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    sample_text = f.read(1500)
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    sample_text = f.read(1500)

    except Exception as e:
        logger.error(f"[{fname}] Physical file reading error → REJECTED", exc_info=True)
        return False, f"Unreadable file: {e}"

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
        # Request evaluation from the LLM
        response: Any = llm.invoke(prompt)
        answer: str = response.content.strip()
        lines: list[str] = answer.splitlines()

        verdict_str: str = lines[0].strip().upper()
        verdict: bool = verdict_str.startswith("OUI")  # Keeps 'OUI' logic as per prompt expectations

        explication: str = lines[1].strip() if len(lines) > 1 else "No explanation provided."

        status: str = "ACCEPTED" if verdict else "REJECTED"
        logger.info(f"Guardian [{fname}] via {provider_key}/{model} → {status}")

        return verdict, explication
    except Exception:
        logger.error(f"[{fname}] API error during validation → REJECTED", exc_info=True)
        return False, "API Error"
