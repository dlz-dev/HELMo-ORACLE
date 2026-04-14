import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

import state
from core.utils.logger import logger

router = APIRouter(prefix="/ingest")


def _require_api_key(x_api_key: str = Header(...)):
    if not state.ADMIN_API_KEY or x_api_key != state.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


def _run_ingestion(file_paths: list):
    from core.agent.guardian import is_valid_lore_file
    from core.utils.utils import ARCHIVE_DIR, QUARANTINE_DIR, load_api_key
    from converters import convert_csv, convert_markdown, convert_text, convert_json, convert_pdf
    from converters.convert_unstructured import process_with_unstructured
    from core.pipeline.ingestion import generate_document_context
    from providers import get_llm
    import shutil

    cfg = state.config
    guardian_cfg = cfg.get("guardian", {})
    ctx_provider = guardian_cfg.get("provider", "groq")
    ctx_model = guardian_cfg.get("model", "llama-3.1-8b-instant")
    api_key = load_api_key()
    total = len(file_paths)

    try:
        context_llm = get_llm(provider_key=ctx_provider, model=ctx_model, config=cfg)
    except Exception as e:
        context_llm = None
        logger.warning("INGEST | Context LLM unavailable: %s", e)

    new_chunks = 0
    duplicate_chunks = 0
    rejected_files = 0

    file_statuses: dict = {Path(fp).name: "pending" for fp in file_paths}
    state.ingest_status["files"] = file_statuses

    def _process_file(fp):
        fp = Path(fp)
        name = fp.name

        if state.ingest_cancel.is_set():
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
        ext = fp.suffix.lower()
        if ext == ".csv":
            chunks = convert_csv.load_csv_data(str(fp))
        elif ext == ".md":
            chunks = convert_markdown.parse_markdown(str(fp))
        elif ext == ".txt":
            chunks = convert_text.process_text_file(str(fp))
        elif ext == ".json":
            chunks = convert_json.parse_json(str(fp))
        elif ext == ".pdf":
            chunks = convert_pdf.process_pdf_file(str(fp))
        else:
            chunks = process_with_unstructured(str(fp))

        file_statuses[name] = "contextualizing"
        doc_context = ""
        if context_llm is not None:
            doc_context = generate_document_context(fp, context_llm, chunks)

        base_metadata = {"source": name}
        if doc_context:
            base_metadata["global_context"] = doc_context

        file_statuses[name] = "vectorizing"
        return fp, chunks, base_metadata

    try:
        if state.ingest_cancel.is_set():
            state.ingest_status = {
                "running": False, "last_status": "warning",
                "last_message": "Ingestion annulée par l'administrateur.", "files": file_statuses,
            }
            return

        max_workers = min(4, total)
        state.ingest_status["last_message"] = f"Traitement parallèle de {total} fichier(s)…"

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_fp = {executor.submit(_process_file, fp): fp for fp in file_paths}

            for future in as_completed(future_to_fp):
                try:
                    fp, chunks, base_or_reason = future.result()
                except RuntimeError as e:
                    state.ingest_status = {
                        "running": False, "last_status": "error",
                        "last_message": str(e), "files": file_statuses,
                    }
                    return

                fp = Path(fp)

                if chunks is None:
                    reason = base_or_reason
                    if reason != "annulé":
                        shutil.move(str(fp), str(QUARANTINE_DIR / fp.name))
                        logger.warning("INGEST | Rejeté : %s — %s", fp.name, reason)
                        state.push_event("ingest_guardian", filename=fp.name, status="rejected",
                                         reason=reason[:100])
                    rejected_files += 1
                    continue

                base_metadata = base_or_reason
                state.push_event("ingest_guardian", filename=fp.name, status="accepted")

                batch = [(text, {**meta, **base_metadata}) for text, meta in chunks]
                inserted = state.vm.add_documents_batch(batch, use_late_chunking=True)
                file_dup = len(batch) - inserted
                new_chunks += inserted
                duplicate_chunks += file_dup

                file_statuses[fp.name] = "done"
                shutil.move(str(fp), str(ARCHIVE_DIR / fp.name))
                logger.info("INGEST | OK — %s (%d nouveaux, %d doublons)", fp.name, inserted, file_dup)
                state.push_event("ingest_complete", filename=fp.name, new_chunks=inserted,
                                 duplicate_chunks=file_dup)

        accepted = total - rejected_files
        if rejected_files == total:
            state.ingest_status = {
                "running": False, "last_status": "warning",
                "last_message": "Fichier refusé — déplacé en quarantaine.", "files": file_statuses,
            }
        elif rejected_files > 0:
            state.ingest_status = {
                "running": False, "last_status": "warning",
                "last_message": (
                    f"{accepted} fichier(s) ajouté(s) — {new_chunks} chunks ajoutés, "
                    f"{duplicate_chunks} doublons. {rejected_files} refusé(s) et déplacé(s) en quarantaine."
                ),
                "files": file_statuses,
            }
        else:
            state.ingest_status = {
                "running": False, "last_status": "success",
                "last_message": f"Fichier ajouté ! {new_chunks} chunks ajoutés, {duplicate_chunks} doublons ignorés.",
                "files": file_statuses,
            }

    except Exception as e:
        state.ingest_status = {
            "running": False, "last_status": "error", "last_message": str(e), "files": file_statuses,
        }
        logger.error("INGEST | Erreur : %s", e, exc_info=True)
        state.push_event("ingest_error", error=str(e)[:120])


@router.post("", dependencies=[Depends(_require_api_key)])
async def trigger_ingest(files: list[UploadFile] = File(...)):
    if state.ingest_status.get("running"):
        return {"started": False, "detail": "Une ingestion est déjà en cours."}

    from core.utils.utils import NEW_FILES_DIR, ARCHIVE_DIR, QUARANTINE_DIR
    NEW_FILES_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    _MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB par fichier
    saved_paths = []
    for file in files:
        safe_name = Path(file.filename).name
        contents = await file.read()
        if len(contents) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"Fichier '{safe_name}' dépasse la limite de 100 MB.")
        dest = NEW_FILES_DIR / safe_name
        with open(dest, "wb") as f:
            f.write(contents)
        saved_paths.append(dest)
        logger.info("INGEST | Fichier reçu : %s", safe_name)

    state.ingest_cancel.clear()
    state.ingest_status.update({"running": True, "last_status": "idle", "last_message": "Démarrage…"})
    t = threading.Thread(target=_run_ingestion, args=[saved_paths], daemon=True)
    t.start()
    return {"started": True, "files": [f.filename for f in files]}


@router.get("/status")
def ingest_status():
    return state.ingest_status


@router.post("/cancel", dependencies=[Depends(_require_api_key)])
def cancel_ingest():
    if not state.ingest_status.get("running"):
        return {"cancelled": False, "detail": "Aucune ingestion en cours."}
    state.ingest_cancel.set()
    return {"cancelled": True}