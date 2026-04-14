"""
Worker d'ingestion de fichiers pour le pipeline RAG.
Gère la validation (Guardian), conversion, contextualisation et vectorisation.
"""

import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from converters import convert_csv, convert_json, convert_markdown, convert_text
from converters.convert_unstructured import process_with_unstructured
from core.agent.guardian import is_valid_lore_file
from core.pipeline.ingestion import generate_document_context
from core.utils.logger import logger
from core.utils.utils import ARCHIVE_DIR, QUARANTINE_DIR, load_api_key, load_config
from providers import get_llm

# ── État global d'ingestion ────────────────────────────────────────────────────

status: dict = {"running": False, "last_status": "idle", "last_message": "", "files": {}}
cancel_event = threading.Event()

# Injectés depuis api.py au démarrage
_vm = None
_push_event = None


def setup(vm, push_event_fn):
    global _vm, _push_event
    _vm = vm
    _push_event = push_event_fn


# ── Conversion par extension ───────────────────────────────────────────────────

_CONVERTERS = {
    ".csv": lambda fp: convert_csv.load_csv_data(str(fp)),
    ".md": lambda fp: convert_markdown.parse_markdown(str(fp)),
    ".txt": lambda fp: convert_text.process_text_file(str(fp)),
    ".json": lambda fp: convert_json.parse_json(str(fp)),
}


def _convert(fp: Path) -> list:
    converter = _CONVERTERS.get(fp.suffix.lower(), lambda p: process_with_unstructured(str(p)))
    return converter(fp)


# ── Traitement d'un fichier (dans un thread worker) ────────────────────────────

def _process_file(fp: Path, file_statuses: dict, api_key: str, context_llm) -> tuple:
    """Retourne (fp, chunks, base_metadata) ou (fp, None, reason_str) si rejeté."""
    name = fp.name

    if cancel_event.is_set():
        return fp, None, "annulé"

    file_statuses[name] = "validating"
    try:
        valid, reason = is_valid_lore_file(str(fp), api_key)
    except RuntimeError as e:
        raise RuntimeError(f"Guardian indisponible: {e}")

    if not valid:
        file_statuses[name] = "rejected"
        return fp, None, reason

    file_statuses[name] = "converting"
    chunks = _convert(fp)

    file_statuses[name] = "contextualizing"
    doc_context = ""
    if context_llm is not None:
        doc_context = generate_document_context(fp, context_llm, chunks)

    base_metadata = {"source": name}
    if doc_context:
        base_metadata["global_context"] = doc_context

    file_statuses[name] = "vectorizing"
    return fp, chunks, base_metadata


# ── Worker principal ───────────────────────────────────────────────────────────

def run(file_paths: list):
    global status
    config = load_config()
    api_key = load_api_key()
    total = len(file_paths)

    guardian_cfg = config.get("guardian", {})
    try:
        context_llm = get_llm(
            provider_key=guardian_cfg.get("provider", "groq"),
            model=guardian_cfg.get("model", "llama-3.1-8b-instant"),
            config=config,
        )
    except Exception as e:
        context_llm = None
        logger.warning("INGEST | Context LLM unavailable: %s", e)

    file_statuses = {Path(fp).name: "pending" for fp in file_paths}
    status["files"] = file_statuses

    new_chunks = 0
    duplicate_chunks = 0
    rejected_files = 0

    try:
        if cancel_event.is_set():
            status.update({"running": False, "last_status": "warning",
                           "last_message": "Ingestion annulée par l'administrateur.", "files": file_statuses})
            return

        status["last_message"] = f"Traitement parallèle de {total} fichier(s)…"

        with ThreadPoolExecutor(max_workers=min(4, total)) as executor:
            futures = {executor.submit(_process_file, Path(fp), file_statuses, api_key, context_llm): fp
                       for fp in file_paths}

            for future in as_completed(futures):
                try:
                    fp, chunks, result = future.result()
                except RuntimeError as e:
                    status.update({"running": False, "last_status": "error",
                                   "last_message": str(e), "files": file_statuses})
                    return

                fp = Path(fp)

                if chunks is None:
                    if result != "annulé":
                        shutil.move(str(fp), str(QUARANTINE_DIR / fp.name))
                        logger.warning("INGEST | Rejeté : %s — %s", fp.name, result)
                        _push_event("ingest_guardian", filename=fp.name, status="rejected", reason=result[:100])
                    rejected_files += 1
                    continue

                _push_event("ingest_guardian", filename=fp.name, status="accepted")

                batch = [(text, {**meta, **result}) for text, meta in chunks]
                inserted = _vm.add_documents_batch(batch, use_late_chunking=True)
                file_dup = len(batch) - inserted
                new_chunks += inserted
                duplicate_chunks += file_dup

                file_statuses[fp.name] = "done"
                shutil.move(str(fp), str(ARCHIVE_DIR / fp.name))
                logger.info("INGEST | OK — %s (%d nouveaux, %d doublons)", fp.name, inserted, file_dup)
                _push_event("ingest_complete", filename=fp.name, new_chunks=inserted, duplicate_chunks=file_dup)

        accepted = total - rejected_files
        if rejected_files == total:
            msg = "Fichier refusé — déplacé en quarantaine."
            last_status = "warning"
        elif rejected_files > 0:
            msg = (f"{accepted} fichier(s) ajouté(s) — {new_chunks} chunks ajoutés, "
                   f"{duplicate_chunks} doublons. {rejected_files} refusé(s) et déplacé(s) en quarantaine.")
            last_status = "warning"
        else:
            msg = f"Fichier ajouté ! {new_chunks} chunks ajoutés, {duplicate_chunks} doublons ignorés."
            last_status = "success"

        status.update({"running": False, "last_status": last_status, "last_message": msg, "files": file_statuses})

    except Exception as e:
        status.update({"running": False, "last_status": "error", "last_message": str(e), "files": file_statuses})
        logger.error("INGEST | Erreur : %s", e, exc_info=True)
        _push_event("ingest_error", error=str(e)[:120])
