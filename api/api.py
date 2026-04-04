"""
FastAPI backend for HELMo Oracle.

Exposes the RAG pipeline as a REST API so a separate frontend
(e.g. deployed on Vercel) can call it over HTTP.
"""

import os
import threading as _threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, HTTPException, Header, Depends, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langgraph.prebuilt import create_react_agent
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from psycopg import sql
from pydantic import BaseModel

import mcp_server as _mcp_module
from core.agent.tools_oracle import get_search_tool
from core.context.memory_manager import MemoryManager
from core.context.session_manager import SessionManager
from core.database.vector_manager import VectorManager
from core.pipeline.pii_manager import PIIManager
from core.utils.logger import logger, set_shared_conn, log_to_db_sync, _LOG_FILE
from core.utils.utils import load_config, load_base_prompt, format_response
from providers import get_llm, get_available_models

# --- Configuration Loading ---
config = load_config()
BASE_SYSTEM_PROMPT = load_base_prompt()

logger.info("━" * 50)
logger.info("Oracle API démarrage...")

# --- Service Initialization ---
_embeddings = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-base")
logger.info("Modèle embeddings chargé : intfloat/multilingual-e5-base")

vm = VectorManager(embeddings_model=_embeddings)

if vm.is_db_available():
    logger.info("VectorManager connecté à Digital Ocean (pgvector).")
else:
    logger.error("VectorManager n'a PAS pu se connecter à Digital Ocean. La recherche sera indisponible.")

# --- Connexion séparée Supabase pour logs/profils ---
import psycopg as _psycopg

_log_conn = None
_LOG_DB_URL = os.getenv("LOG_DATABASE_URL", "")
if _LOG_DB_URL:
    try:
        _log_conn = _psycopg.connect(_LOG_DB_URL, autocommit=False, connect_timeout=10)
        logger.info("Connexion Supabase (logs) initialisée.")
    except Exception as _e:
        logger.error(f"Impossible de se connecter à Supabase pour les logs : {_e}")

set_shared_conn(_log_conn)


def _ensure_log_conn() -> bool:
    """Ensures _log_conn is alive, reconnecting if needed. Returns True if available."""
    global _log_conn
    if not _LOG_DB_URL:
        return False
    # Check if existing connection is still usable
    if _log_conn is not None and not _log_conn.closed:
        try:
            with _log_conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            logger.warning("_ensure_log_conn: Ping failed, will attempt reconnect", exc_info=True)
    try:
        if _log_conn is not None and not _log_conn.closed:
            try:
                _log_conn.close()
            except Exception:
                logger.warning("_ensure_log_conn: Failed to close stale connection", exc_info=True)
        _log_conn = _psycopg.connect(_LOG_DB_URL, autocommit=False, connect_timeout=10)
        set_shared_conn(_log_conn)
        logger.info("Connexion Supabase (logs) reconnectée.")
        return True
    except Exception as _e:
        logger.error(f"_ensure_log_conn: Reconnexion échouée : {_e}")
        _log_conn = None
        set_shared_conn(None)
        return False


# --- Client Supabase Python (pour feedback) ---
_supabase = None
_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
if _SUPABASE_URL and _SUPABASE_KEY:
    try:
        from supabase import create_client as _create_supabase_client
        _supabase = _create_supabase_client(_SUPABASE_URL, _SUPABASE_KEY)
        logger.info("Client Supabase initialisé.")
    except Exception as _e:
        logger.error(f"Impossible d'initialiser le client Supabase : {_e}")

_mcp_module.setup(vm)
_mcp_asgi = _mcp_module.mcp.streamable_http_app()
sm = SessionManager()
mm = MemoryManager(
    max_recent_tokens=config.get("memory", {}).get("max_recent_tokens", 1200),
    min_recent_messages=config.get("memory", {}).get("min_recent_messages", 4),
)
pii = PIIManager()

# --- Auth ---
_ADMIN_API_KEY = os.getenv("API_SECRET_KEY", "")


def _require_api_key(x_api_key: str = Header(...)):
    if not _ADMIN_API_KEY or x_api_key != _ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


# --- FastAPI App ---
@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with _mcp_asgi.router.lifespan_context(app):
        yield


app = FastAPI(title="HELMo Oracle API", version="1.0.0", lifespan=_lifespan)

ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)
app.mount("/mcp", _mcp_asgi)


# --- Schemas ---
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    user_id: Optional[str] = None
    provider: str = config.get("llm", {}).get("default_provider", "groq")
    model: Optional[str] = None
    temperature: float = float(config.get("llm", {}).get("temperature", 0.0))
    k_final: int = config.get("search", {}).get("k_final", 5)
    # Set to False to skip RAGAS retry and get a faster (single-attempt) response.
    enable_retry: bool = True


class EvaluateRequest(BaseModel):
    """On-demand RAGAS evaluation of a question/answer/contexts triple."""
    question: str
    answer: str
    # Raw context strings — use this when you already have text chunks.
    contexts: Optional[list[str]] = None
    # Alternatively, pass cot_storage dicts (as returned by /chat).
    cot_storage: Optional[list[dict]] = None
    provider: str = config.get("llm", {}).get("default_provider", "groq")
    model: Optional[str] = None


class RenameRequest(BaseModel):
    title: str


class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    rating: int
    comment: Optional[str] = None


# --- Per-request Session Manager ---
def _get_sm(user_id: Optional[str] = None) -> SessionManager:
    """Returns a per-request SessionManager scoped to the given user_id, or the global instance."""
    if user_id and _is_valid_uuid(user_id):
        return SessionManager(user_id=user_id)
    return sm


# --- Shared Agent Logic ---
def _is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def _build_lc_history(history_tuples, masked_message):
    from langchain_core.messages import HumanMessage as HM, AIMessage as AM
    lc_history = []
    for role, content in history_tuples:
        lc_history.append(HM(content=content) if role == "user" else AM(content=content))
    if not lc_history or not isinstance(lc_history[-1], HM) or lc_history[-1].content != masked_message:
        lc_history.append(HM(content=masked_message))
    return lc_history


def _run_agent(session: dict, masked_message: str, provider: str, model: str,
               temperature: float, k_final: int) -> tuple[str, list]:
    """
    Runs the LangGraph RAG agent for a single attempt.

    Returns:
        Tuple of (response_text, cot_storage) where cot_storage is the list of
        retrieved chunks populated by the search tool during this invocation.
    """
    user_id = session.get("user_id")
    log_user_id = user_id if _is_valid_uuid(user_id) else None

    # cot_storage is populated in-place by the search tool during agent execution.
    cot_storage: list = []

    start_retrieval = time.time()
    search_tool = get_search_tool(vm, k_final=k_final, cot_storage=cot_storage)
    retrieval_time = time.time() - start_retrieval
    log_to_db_sync(
        level="INFO", source="RAG_PROFILING",
        message="Context retrieval finished",
        metadata={"duration_seconds": retrieval_time}, user_id=log_user_id
    )

    llm = get_llm(
        provider_key=provider, model=model,
        config={**config, "llm": {**config.get("llm", {}), "temperature": temperature}},
    )
    agent = create_react_agent(llm, [search_tool], prompt=BASE_SYSTEM_PROMPT)
    enriched_prompt, history_tuples = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)
    lc_history = _build_lc_history(history_tuples, masked_message)

    start_generation = time.time()
    result = agent.invoke({"messages": lc_history})
    generation_time = time.time() - start_generation
    response_text = format_response(result["messages"][-1].content)
    log_to_db_sync(
        level="INFO", source="RAG_PROFILING",
        message="LLM response generated",
        metadata={"duration_seconds": generation_time, "provider": provider, "model": model},
        user_id=log_user_id
    )
    return response_text, cot_storage


# --- Routes ---
@app.get("/health")
def health():
    checks = {}

    if vm.is_db_available():
        try:
            with vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM documents")
                count = cur.fetchone()[0]
            checks["database"] = {"status": "ok", "documents": count}
        except Exception as e:
            checks["database"] = {"status": "error", "error": str(e)}
    else:
        checks["database"] = {"status": "error", "error": "Connexion indisponible"}

    checks["embeddings"] = {"status": "ok", "model": "intfloat/multilingual-e5-base"}

    return {"status": "ok", "checks": checks}


@app.get("/health/full")
def health_full():
    """
    Vérifie l'état de tous les composants du système.
    Teste : base de données, embeddings, et chaque clé API configurée.
    """
    results = {}

    # ── Base de données ───────────────────────────────────────────
    if vm.is_db_available():
        try:
            start = time.time()
            with vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM documents")
                count = cur.fetchone()[0]
            results["database"] = {
                "status": "ok",
                "documents": count,
                "latency_ms": round((time.time() - start) * 1000),
            }
        except Exception as e:
            results["database"] = {"status": "error", "error": str(e)}
    else:
        results["database"] = {"status": "error", "error": "Connexion indisponible"}

    # ── Modèle embeddings ─────────────────────────────────────────
    try:
        start = time.time()
        _embeddings.get_text_embedding("test")
        results["embeddings"] = {
            "status": "ok",
            "model": "intfloat/multilingual-e5-base",
            "latency_ms": round((time.time() - start) * 1000),
        }
    except Exception as e:
        results["embeddings"] = {"status": "error", "error": str(e)}

    # ── Clés API (teste uniquement celles configurées) ────────────
    providers_to_check = {
        "groq": ("GROQ_API_KEY", "langchain_groq", "ChatGroq", {"model": "llama-3.1-8b-instant"}),
        "openai": ("OPENAI_API_KEY", "langchain_openai", "ChatOpenAI", {"model": "gpt-4o-mini"}),
        "anthropic": ("ANTHROPIC_API_KEY", "langchain_anthropic", "ChatAnthropic",
                      {"model": "claude-haiku-4-5-20251001"}),
        "gemini": ("GOOGLE_API_KEY", "langchain_google_genai", "ChatGoogleGenerativeAI", {"model": "gemini-2.0-flash"}),
    }

    from langchain_core.messages import HumanMessage as _HM

    for provider_name, (env_var, module, cls_name, kwargs) in providers_to_check.items():
        api_key = os.environ.get(env_var, "")
        if not api_key:
            results[provider_name] = {"status": "not_configured"}
            continue
        try:
            start = time.time()
            mod = __import__(module, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            llm = cls(api_key=api_key, temperature=0, **kwargs)
            llm.invoke([_HM(content="Reply with one word: ok")])
            results[provider_name] = {
                "status": "ok",
                "latency_ms": round((time.time() - start) * 1000),
            }
        except Exception as e:
            results[provider_name] = {"status": "error", "error": str(e)[:120]}

    has_error = any(v.get("status") == "error" for v in results.values())
    return {
        "status": "degraded" if has_error else "ok",
        "checks": results,
    }


@app.get("/providers/{provider}/models")
def list_models(provider: str):
    try:
        return {"models": get_available_models(provider, config)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions")
def list_sessions(user_id: Optional[str] = None):
    return {"sessions": _get_sm(user_id).list_sessions()}


@app.post("/sessions")
def create_session(provider: str = "", model: str = "", user_id: Optional[str] = None):
    request_sm = _get_sm(user_id)
    session = request_sm.new_session(provider=provider, model=model)
    request_sm.save(session)
    return session


@app.get("/sessions/{session_id}")
def get_session(session_id: str, user_id: Optional[str] = None):
    session = _get_sm(user_id).load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, user_id: Optional[str] = None):
    _get_sm(user_id).delete(session_id)
    return {"deleted": session_id}


@app.patch("/sessions/{session_id}/rename")
def rename_session(session_id: str, body: RenameRequest, user_id: Optional[str] = None):
    request_sm = _get_sm(user_id)
    session = request_sm.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["title"] = body.title
    request_sm.save(session)
    return {"session_id": session_id, "title": body.title}


@app.post("/chat")
def chat(req: ChatRequest):
    from core.utils.retry_manager import run_agent_with_retry, RetryExhaustedError

    request_sm = _get_sm(req.user_id)

    if req.session_id:
        session = request_sm.load(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = request_sm.new_session(provider=req.provider, model=req.model or "")

    model = req.model or config.get("llm", {}).get("default_model", "")
    masked_message = pii.mask_text(req.message)
    session.setdefault("messages", []).append({"role": "user", "content": masked_message})
    request_sm.save(session)

    retry_meta: dict = {}

    try:
        if req.enable_retry:
            # ── Retry path: run agent with RAGAS quality gate ─────────────
            response, cot_storage, retry_meta = run_agent_with_retry(
                session=session,
                masked_message=masked_message,
                provider=req.provider,
                model=model,
                temperature=req.temperature,
                k_final=req.k_final,
                agent_func=_run_agent,
                config=config,
            )
        else:
            # ── Fast path: single attempt, no quality check ───────────────
            response, cot_storage = _run_agent(
                session=session,
                masked_message=masked_message,
                provider=req.provider,
                model=model,
                temperature=req.temperature,
                k_final=req.k_final,
            )

    except RetryExhaustedError as e:
        logger.warning(
            "CHAT | All retry attempts exhausted — session=%s attempts=%d last_scores=%s",
            session.get("session_id"), e.attempts, e.last_scores,
        )
        raise HTTPException(status_code=422, detail={
            "message": str(e),
            "attempts": e.attempts,
            "last_scores": e.last_scores,
        })
    except Exception as e:
        logger.error("CHAT | Agent execution failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    session["messages"].append({"role": "assistant", "content": response, "_cot": cot_storage})
    if mm.needs_summarization(session["messages"], session.get("summary", "")):
        session = mm.compress(session, get_llm(
            provider_key=req.provider, model=model,
            config={**config, "llm": {**config.get("llm", {}), "temperature": req.temperature}},
        ))
    session["provider"] = req.provider
    session["model"] = model
    request_sm.save(session)

    return {
        "session_id": session["session_id"],
        "response": response,
        "cot_results": cot_storage,
        # retry_meta is empty ({}) when enable_retry=False
        "retry_meta": retry_meta,
    }


@app.post("/evaluate")
def evaluate_endpoint(req: EvaluateRequest):
    """
    On-demand RAGAS evaluation of a question / answer / context triple.

    Accepts either:
      - ``contexts``   : list of raw text strings
      - ``cot_storage``: list of dicts with a 'content' key (as returned by /chat)

    The shared embeddings singleton (_embeddings) is passed to avoid loading
    the HuggingFace model a second time.

    Returns the same dict shape as evaluate_rag_response().
    """
    from core.utils.ragas_evaluator import evaluate_rag_response

    model = req.model or config.get("llm", {}).get("default_model", "llama-3.3-70b-versatile")

    # Normalise inputs to cot_storage format expected by evaluate_rag_response
    if req.cot_storage is not None:
        cot_storage = req.cot_storage
    elif req.contexts is not None:
        cot_storage = [{"content": c} for c in req.contexts]
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either 'contexts' (list[str]) or 'cot_storage' (list[dict]).",
        )

    result = evaluate_rag_response(
        question=req.question,
        answer=req.answer,
        cot_storage=cot_storage,
        provider=req.provider,
        model=model,
        config=config,
        shared_embeddings=_embeddings,   # reuse the already-loaded model
    )

    if result.get("error") and result.get("faithfulness") is None:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.get("/archives")
def list_archives():
    return {"sources": vm.list_sources()}


# --- Ingestion ---
_ingest_status = {"running": False, "last_status": "idle", "last_message": ""}


def _run_ingestion(file_paths: list):
    global _ingest_status
    from pathlib import Path
    from core.agent.guardian import is_valid_lore_file
    from core.utils.utils import ARCHIVE_DIR, QUARANTINE_DIR, load_api_key
    from converters import convert_csv, convert_markdown, convert_text, convert_json, convert_pdf
    from converters.convert_unstructured import process_with_unstructured
    from core.pipeline.ingestion import generate_document_context
    import shutil

    config = load_config()
    guardian_cfg = config.get("guardian", {})
    ctx_provider = guardian_cfg.get("provider", "groq")
    ctx_model = guardian_cfg.get("model", "llama-3.1-8b-instant")
    api_key = load_api_key()
    total = len(file_paths)

    try:
        context_llm = get_llm(provider_key=ctx_provider, model=ctx_model, config=config)
    except Exception as e:
        context_llm = None
        logger.warning("INGEST | Context LLM unavailable: %s", e)

    new_chunks = 0
    duplicate_chunks = 0
    rejected_files = 0

    try:
        for i, fp in enumerate(file_paths):
            fp = Path(fp)
            _ingest_status["last_message"] = f"Fichier {i + 1}/{total} — Validation de {fp.name}…"

            # 1. Guardian
            try:
                valid, reason = is_valid_lore_file(str(fp), api_key)
            except RuntimeError as e:
                _ingest_status = {"running": False, "last_status": "error",
                                  "last_message": f"Guardian indisponible: {e}"}
                return

            if not valid:
                shutil.move(str(fp), str(QUARANTINE_DIR / fp.name))
                logger.warning("INGEST | Rejeté : %s — %s", fp.name, reason)
                rejected_files += 1
                continue

            # 2. Conversion
            _ingest_status["last_message"] = f"Fichier {i + 1}/{total} — Conversion de {fp.name}…"
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

            # 3. Contexte global
            doc_context = ""
            if context_llm is not None:
                doc_context = generate_document_context(fp, context_llm, chunks)

            base_metadata = {"source": fp.name}
            if doc_context:
                base_metadata["global_context"] = doc_context

            # 4. Vectorisation
            _ingest_status["last_message"] = f"Fichier {i + 1}/{total} — Vectorisation de {fp.name}…"
            for text, meta in chunks:
                inserted = vm.add_document(text, metadata={**meta, **base_metadata})
                if inserted:
                    new_chunks += 1
                else:
                    duplicate_chunks += 1

            # 5. Archive
            shutil.move(str(fp), str(ARCHIVE_DIR / fp.name))
            logger.info("INGEST | OK — %s (%d nouveaux, %d doublons)", fp.name, new_chunks, duplicate_chunks)

        accepted = total - rejected_files
        if rejected_files == total:
            _ingest_status = {"running": False, "last_status": "warning",
                              "last_message": "Fichier refusé — déplacé en quarantaine."}
        elif rejected_files > 0:
            _ingest_status = {"running": False, "last_status": "warning",
                              "last_message": f"{accepted} fichier(s) ajouté(s) — {new_chunks} chunks ajoutés, {duplicate_chunks} doublons. {rejected_files} refusé(s) et déplacé(s) en quarantaine."}
        else:
            _ingest_status = {"running": False, "last_status": "success",
                              "last_message": f"Fichier ajouté ! {new_chunks} chunks ajoutés, {duplicate_chunks} doublons ignorés."}

    except Exception as e:
        _ingest_status = {"running": False, "last_status": "error", "last_message": str(e)}
        logger.error("INGEST | Erreur : %s", e, exc_info=True)


@app.post("/ingest", dependencies=[Depends(_require_api_key)])
async def trigger_ingest(files: list[UploadFile] = File(...)):
    if _ingest_status.get("running"):
        return {"started": False, "detail": "Une ingestion est déjà en cours."}

    from core.utils.utils import NEW_FILES_DIR, ARCHIVE_DIR, QUARANTINE_DIR
    NEW_FILES_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for file in files:
        safe_name = Path(file.filename).name
        dest = NEW_FILES_DIR / safe_name
        contents = await file.read()
        with open(dest, "wb") as f:
            f.write(contents)
        saved_paths.append(dest)
        logger.info("INGEST | Fichier reçu : %s", safe_name)

    _ingest_status.update({"running": True, "last_status": "idle", "last_message": "Démarrage…"})
    t = _threading.Thread(target=_run_ingestion, args=[saved_paths], daemon=True)
    t.start()
    return {"started": True, "files": [f.filename for f in files]}


@app.get("/ingest/status")
def ingest_status():
    return _ingest_status


# --- Logs ---
@app.get("/logs", dependencies=[Depends(_require_api_key)])
def get_logs(lines: int = 100, offset: int = 0, level: Optional[str] = None, source: Optional[str] = None):
    """Fetches logs from the database with optional filters and pagination."""
    if not _ensure_log_conn():
        logger.error("[GET_LOGS] Connexion Supabase (logs) indisponible.")
        raise HTTPException(status_code=503, detail="Connexion logs indisponible")

    try:
        with _log_conn.cursor() as cur:
            base_query = sql.SQL("""
                                 SELECT l.id,
                                        l.created_at,
                                        l.level,
                                        l.source,
                                        l.message,
                                        l.metadata,
                                        p.first_name,
                                        p.last_name
                                 FROM logs l
                                          LEFT JOIN profiles p ON l.user_id = p.id
                                 """)
            conditions = []
            params = []
            if level:
                conditions.append(sql.SQL("l.level = %s"))
                params.append(level)
            if source:
                conditions.append(sql.SQL("l.source = %s"))
                params.append(source)
            if conditions:
                base_query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
            base_query += sql.SQL(" ORDER BY l.created_at DESC LIMIT %s OFFSET %s")
            params.extend([lines, offset])

            cur.execute(base_query, params)
            rows = cur.fetchall()

            logs_list = [
                {
                    "id": row[0], "created_at": row[1], "level": row[2], "source": row[3],
                    "message": row[4], "metadata": row[5],
                    "profiles": {"first_name": row[6], "last_name": row[7]} if row[6] else None
                } for row in rows
            ]
            return {"logs": logs_list}
    except Exception as e:
        logger.error("[GET_LOGS] Failed to fetch logs from DB.", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur interne du serveur lors de la récupération des logs: {e}")


@app.delete("/logs", dependencies=[Depends(_require_api_key)])
def clear_logs():
    """Clears the local log file (does not affect the DB)."""
    try:
        with open(_LOG_FILE, "w") as f:
            f.truncate()
        logger.info("Logs effacés par l'administrateur (fichier local uniquement)")
        return {"cleared": True}
    except Exception as e:
        logger.error("[CLEAR_LOGS] Failed to clear local log file.", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Feedback ---
@app.post("/feedback", status_code=201)
def submit_feedback(req: FeedbackRequest):
    """Enregistre un feedback utilisateur (note 1-5 + commentaire optionnel)."""
    if not (1 <= req.rating <= 5):
        raise HTTPException(status_code=422, detail="La note doit être entre 1 et 5.")
    if _supabase is None:
        raise HTTPException(status_code=503, detail="Client Supabase indisponible.")
    user_id = req.user_id if req.user_id and _is_valid_uuid(req.user_id) else None
    try:
        _supabase.table("feedback").insert({
            "session_id": req.session_id,
            "user_id": user_id,
            "rating": req.rating,
            "comment": req.comment,
        }).execute()
        logger.info(f"Feedback reçu — session={req.session_id} note={req.rating}")
        log_to_db_sync(
            level="INFO",
            source="FEEDBACK",
            message=f"Note {req.rating}/5",
            metadata={"session_id": req.session_id, "rating": req.rating, "comment": req.comment},
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Erreur insertion feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement du feedback.")
    return {"status": "ok"}


# --- Entry Point ---
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)