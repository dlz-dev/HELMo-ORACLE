"""
Ingestion pipeline for lore files into the vector database.

Pipeline steps per file:
  1. GUARD    — Validates that the file is Dofus/MMORPG lore.
  2. PARSE    — Converts the file based on its extension via LlamaIndex.
  3. CONTEXT  — An LLM generates a global description from the extracted text.
  4. VECTORIZE— Each contextualized chunk is vectorized and saved to the DB.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("oracle")


# Import converters - moved to function-level to avoid circular imports
def _import_converters():
    from converters import convert_csv, convert_markdown, convert_text, convert_json, convert_pdf, convert_unstructured
    return convert_csv, convert_markdown, convert_text, convert_json, convert_pdf, convert_unstructured


from core.agent.guardian import is_valid_lore_file
from core.database.vector_manager import VectorManager
from core.utils.utils import _CONTEXT_PROMPT, ARCHIVE_DIR, QUARANTINE_DIR, load_config, load_api_key


# Import providers - moved to function-level to avoid circular imports
def _import_providers():
    from providers import get_llm
    return get_llm


def generate_document_context(
        file_path: Path,
        llm: Any,
        extracted_chunks: List[Tuple[str, Dict]] = None
) -> str:
    """
    Generates a contextual description of the entire document using an LLM.

    Uses already-extracted chunks as the text sample when available (covers
    binary formats like .docx, .pptx handled by Unstructured). Falls back to
    a raw text read for simple formats (.txt, .md, .json, .csv).

    Args:
        file_path (Path): The path to the file (used for fallback read).
        llm (Any): The language model instance used for generation.
        extracted_chunks: Already-extracted (text, metadata) pairs, if available.

    Returns:
        str: The generated context, or an empty string if it fails.
    """
    try:
        if extracted_chunks:
            # Build sample from extracted text — works for ALL formats including binary
            sample = " ".join(text for text, _ in extracted_chunks)[:3000]
        else:
            # Fallback: raw read for simple text formats
            with open(file_path, "r", encoding="utf-8") as f:
                sample = f.read(3000)
    except Exception:
        logger.warning("INGEST | Could not read file sample for context generation", exc_info=True)
        return ""

    try:
        response = llm.invoke(_CONTEXT_PROMPT.format(sample=sample))
        context = response.content.strip()
        logger.info("INGEST | Context generated: %s...", context[:80])
        return context
    except Exception as e:
        logger.warning("INGEST | Context generation failed: %s", e)
        return ""


def seed_database() -> None:
    """
    Main pipeline to read files, validate them, generate context, chunk, and insert
    them into the vector database.
    """
    input_folder = ARCHIVE_DIR
    quarantine_folder = QUARANTINE_DIR

    quarantine_folder.mkdir(parents=True, exist_ok=True)

    config = load_config()

    guardian_cfg = config.get("guardian", {})
    ctx_provider = guardian_cfg.get("provider", "groq")
    ctx_model = guardian_cfg.get("model", "gemma2-9b-it")

    try:
        get_llm = _import_providers()
        context_llm = get_llm(provider_key=ctx_provider, model=ctx_model, config=config)
        logger.info("INGEST | Contextualization via %s/%s", ctx_provider, ctx_model)
    except Exception as e:
        context_llm = None
        logger.warning("INGEST | Context LLM unavailable: %s", e)

    logger.info("INGEST | Connecting to vector database...")
    db_manager = VectorManager()

    logger.info("INGEST | Reading files from: %s", input_folder)

    files = sorted(input_folder.iterdir())
    total_accepted = total_rejected = total_chunks = 0

    for file_path in files:
        if not file_path.is_file() or not file_path.name.startswith("lore_"):
            continue

        logger.info("INGEST | Processing: %s", file_path.name)

        try:
            valid = is_valid_lore_file(str(file_path))
        except RuntimeError as e:
            logger.error("INGEST | Guardian unavailable: %s", e)
            return

        if not valid:
            total_rejected += 1
            logger.warning("INGEST | REJECTED → quarantine: %s", file_path.name)
            shutil.move(str(file_path), str(quarantine_folder / file_path.name))
            continue

        total_accepted += 1

        # ─ Étape 1 :Conversion ─────────────────────────────────────────────
        extension = file_path.suffix.lower()
        extracted_chunks: List[Tuple[str, Dict[str, Any]]] = []
        convert_csv, convert_markdown, convert_text, convert_json, convert_pdf, convert_unstructured = _import_converters()

        _unst_cfg = config.get("llm", {}).get("unstructured", {})

        if extension == ".csv":
            extracted_chunks = convert_csv.load_csv_data(str(file_path))
        elif extension == ".txt":
            extracted_chunks = convert_text.process_text_file(str(file_path))
        elif extension == ".json":
            extracted_chunks = convert_json.parse_json(str(file_path))
        elif extension == ".md":
            extracted_chunks = convert_markdown.parse_markdown(str(file_path))
        else:
            logger.info("INGEST | Complex format detected, calling Unstructured.io for %s", file_path.name)
            extracted_chunks = convert_unstructured.process_with_unstructured(str(file_path))

        # ── Étape 2 : Contexte global ─────────────────────────────────────────
        # Utilise les chunks extraits comme base — fonctionne pour tous les formats.
        doc_context = ""
        if context_llm is not None:
            doc_context = generate_document_context(file_path, context_llm, extracted_chunks)

        base_metadata: Dict[str, Any] = {"source": file_path.name}
        if doc_context:
            base_metadata["global_context"] = doc_context

        # ── Étape 3 : Vectorisation (late chunking) ───────────────────────────
        if extracted_chunks:
            batch = [
                (text_chunk, {**base_metadata, **specific_metadata})
                for text_chunk, specific_metadata in extracted_chunks
            ]
            inserted = db_manager.add_documents_batch(batch, use_late_chunking=True)
            total_chunks += len(extracted_chunks)
            logger.info(
                "INGEST | OK — %d/%d chunks inserted from %s (late chunking)",
                inserted, len(extracted_chunks), file_path.name,
            )
        else:
            logger.warning("INGEST | No text extracted from %s", file_path.name)

    logger.info("INGEST | ✓ Complete")
    logger.info("INGEST | Accepted=%d Rejected=%d Chunks=%d", total_accepted, total_rejected, total_chunks)


if __name__ == "__main__":
    seed_database()
