"""
FastAPI backend for HELMo Oracle.

Exposes the RAG pipeline as a REST API so a separate frontend
(e.g. deployed on Vercel) can call it over HTTP.
"""

import asyncio
import json
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
from fastapi.responses import StreamingResponse
from langchain_community.embeddings import OllamaEmbeddings
from langgraph.prebuilt import create_react_agent
from psycopg import sql
from pydantic import BaseModel

import redis as _redis_lib

import mcp_server as _mcp_module
from core.agent.judge import _run_judge_sync
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

# Surcharge la section "judge" avec les variables d'environnement du .env
_judge_provider = os.getenv("JUDGE_PROVIDER")
_judge_model = os.getenv("JUDGE_MODEL")
_judge_temp = os.getenv("JUDGE_TEMP")
if _judge_provider or _judge_model or _judge_temp:
    config.setdefault("judge", {})
    if _judge_provider:
        config["judge"]["provider"] = _judge_provider
    if _judge_model:
        config["judge"]["model"] = _judge_model
    if _judge_temp is not None:
        config["judge"]["temperature"] = float(_judge_temp)

logger.info("━" * 50)
logger.info("Oracle API démarrage...")

# --- Service Initialization ---
_embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
)
logger.info("Modèle embeddings chargé : nomic-embed-text (Ollama)")

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
            pass
    # Reconnect
    try:
        if _log_conn is not None and not _log_conn.closed:
            try:
                _log_conn.close()
            except Exception:
                pass
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

# --- Redis Stream (monitoring dashboard) ---
_redis = None
try:
    _redis = _redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379"), decode_responses=True)
    _redis.ping()
    logger.info("Redis connecté (monitoring stream).")
except Exception as _e:
    logger.warning(f"Redis indisponible, monitoring désactivé : {_e}")
    _redis = None

REDIS_STREAM = "oracle:events"
REDIS_MAX_LEN = 500  # garde les 500 derniers events


def _push_event(event_type: str, **kwargs):
    if _redis is None:
        return
    try:
        _redis.xadd(REDIS_STREAM, {"type": event_type, **{k: str(v) for k, v in kwargs.items()}}, maxlen=REDIS_MAX_LEN)
    except Exception:
        pass


_mcp_module.setup(vm, redis=_redis)
# Désactive la protection DNS rebinding (sécurisé car Docker interne uniquement)
from mcp.server.transport_security import TransportSecurityMiddleware
TransportSecurityMiddleware._validate_host = lambda self, host: True
_mcp_asgi = _mcp_module.mcp.sse_app()
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
    yield


app = FastAPI(title="HELMo Oracle API", version="1.0.0", lifespan=_lifespan)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

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
    user_id = session.get("user_id")
    # Correction: S'assurer que user_id est un UUID valide ou None
    log_user_id = user_id if _is_valid_uuid(user_id) else None

    start_retrieval = time.time()
    cot_storage = []
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

    # Database
    if vm.is_db_available():
        try:
            with vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT metadata->>'source') FROM documents")
                count = cur.fetchone()[0]
            checks["database"] = {"status": "ok", "documents": count}
        except Exception as e:
            checks["database"] = {"status": "error", "error": str(e)}
    else:
        checks["database"] = {"status": "error", "error": "Connexion indisponible"}

    # Embeddings
    checks["embeddings"] = {"status": "ok", "model": "nomic-embed-text"}

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
                cur.execute("SELECT COUNT(DISTINCT metadata->>'source') FROM documents")
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
        _embeddings.embed_query("test")
        results["embeddings"] = {
            "status": "ok",
            "model": "nomic-embed-text",
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

    has_error = any(
        v.get("status") == "error"
        for v in results.values()
    )
    return {
        "status": "degraded" if has_error else "ok",
        "checks": results,
    }


@app.get("/metrics")
def get_metrics():
    """Retourne les stats en temps réel depuis le Redis Stream pour le dashboard de monitoring."""
    if _redis is None:
        return {"available": False, "events": [], "stats": {}}

    try:
        raw = _redis.xrevrange(REDIS_STREAM, count=100)
    except Exception as e:
        return {"available": False, "error": str(e), "events": [], "stats": {}}

    events = []
    for entry_id, fields in raw:
        ts_ms = int(entry_id.split("-")[0])
        events.append({
            "id": entry_id,
            "ts": ts_ms / 1000,
            "type": fields.get("type"),
            "question": fields.get("question", ""),
            "provider": fields.get("provider", ""),
            "model": fields.get("model", ""),
            "latency_ms": int(fields.get("latency_ms", 0)),
            "source": fields.get("source", "web"),
            "filename": fields.get("filename", ""),
            "status": fields.get("status", ""),
            "reason": fields.get("reason", ""),
            "new_chunks": int(fields.get("new_chunks", 0)),
            "duplicate_chunks": int(fields.get("duplicate_chunks", 0)),
            "error": fields.get("error", ""),
        })

    now = time.time()
    chat_events = [e for e in events if e["type"] == "chat"]
    ingest_events = [e for e in events if e["type"].startswith("ingest_")]
    last_minute = [e for e in chat_events if now - e["ts"] < 60]
    last_hour = [e for e in chat_events if now - e["ts"] < 3600]
    latencies = [e["latency_ms"] for e in chat_events if e["latency_ms"] > 0]
    total_chunks = sum(e["new_chunks"] for e in ingest_events if e["type"] == "ingest_complete")
    accepted = sum(1 for e in ingest_events if e["type"] == "ingest_guardian" and e["status"] == "accepted")
    rejected = sum(1 for e in ingest_events if e["type"] == "ingest_guardian" and e["status"] == "rejected")

    stats = {
        "total_queries": len(chat_events),
        "queries_last_minute": len(last_minute),
        "queries_last_hour": len(last_hour),
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "db_ok": vm.is_db_available(),
        "total_chunks_ingested": total_chunks,
        "files_accepted": accepted,
        "files_rejected": rejected,
    }

    return {"available": True, "events": events, "stats": stats}


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
async def chat(req: ChatRequest):
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

    async def event_stream():
        _chat_start = time.time()
        # 1. Envoie le session_id immédiatement comme premier event SSE
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session['session_id']})}\n\n"

        try:
            response, cot_storage = await asyncio.to_thread(
                _run_agent,
                session=session, masked_message=masked_message, provider=req.provider,
                model=model, temperature=req.temperature, k_final=req.k_final,
            )
        except Exception as e:
            logger.error(f"Erreur critique dans le RAG: {e}", exc_info=True)

            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # Log dans Redis Stream pour le dashboard de monitoring
        _push_event(
            "chat",
            question=masked_message[:120],
            provider=req.provider,
            model=model,
            latency_ms=round((time.time() - _chat_start) * 1000),
            source="discord" if req.user_id == "discord" else "web",
        )

        # 2. Stream le texte par chunks de ~20 chars pour l'effet visuel
        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)  # 10ms entre chunks — effet naturel

        # 3. Envoie les résultats CoT (sources RAG)
        if cot_storage:
            yield f"data: {json.dumps({'type': 'cot', 'results': cot_storage})}\n\n"

        # 4. Sauvegarde session et signal de fin
        session["messages"].append({"role": "assistant", "content": response, "_cot": cot_storage})
        session["provider"] = req.provider
        session["model"] = model
        request_sm.save(session)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

        # Compression mémoire en arrière-plan (non-bloquant)
        if mm.needs_summarization(session["messages"], session.get("summary", "")):
            async def _compress_session():
                try:
                    session_updated = await asyncio.to_thread(
                        mm.compress, session, get_llm(
                            provider_key=req.provider, model=model,
                            config={**config, "llm": {**config.get("llm", {}), "temperature": req.temperature}},
                        )
                    )
                    session.update(session_updated)
                    request_sm.save(session)
                except Exception as _e:
                    logger.error(f"Erreur compression mémoire : {_e}", exc_info=True)
            asyncio.create_task(_compress_session())

        # Judge en arrière-plan avec timeout
        asyncio.create_task(
            asyncio.wait_for(
                asyncio.to_thread(
                    _run_judge_sync,
                    query=masked_message,
                    response=response,
                    cot_storage=cot_storage,
                    user_id=req.user_id,
                    session_id=session["session_id"],
                    config=config
                ),
                timeout=20.0
            )
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session["session_id"],
        }
    )


@app.get("/archives")
def list_archives():
    return {"sources": vm.list_sources()}


# --- Ingestion ---
_ingest_status = {"running": False, "last_status": "idle", "last_message": "", "files": {}}
_ingest_cancel = _threading.Event()


def _run_ingestion(file_paths: list):
    global _ingest_status
    from pathlib import Path
    from concurrent.futures import ThreadPoolExecutor, as_completed
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

    # Statut par fichier exposé via /ingest/status — dict mis à jour depuis les threads (safe GIL CPython)
    file_statuses: dict = {Path(fp).name: "pending" for fp in file_paths}
    _ingest_status["files"] = file_statuses

    def _process_file(fp):
        """Étapes 1-3 (Guardian → Convert → Context) pour un fichier. S'exécute dans un thread worker."""
        fp = Path(fp)
        name = fp.name

        if _ingest_cancel.is_set():
            return fp, None, "annulé"

        # 1. Guardian
        file_statuses[name] = "validating"
        try:
            valid, reason = is_valid_lore_file(str(fp), api_key)
        except RuntimeError as e:
            raise RuntimeError(f"Guardian indisponible: {e}")

        if not valid:
            file_statuses[name] = "rejected"
            return fp, None, reason

        # 2. Conversion
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

        # 3. Contexte global
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
        if _ingest_cancel.is_set():
            _ingest_status = {"running": False, "last_status": "warning",
                              "last_message": "Ingestion annulée par l'administrateur.", "files": file_statuses}
            return

        max_workers = min(4, total)
        _ingest_status["last_message"] = f"Traitement parallèle de {total} fichier(s)…"

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_fp = {executor.submit(_process_file, fp): fp for fp in file_paths}

            for future in as_completed(future_to_fp):
                try:
                    fp, chunks, base_or_reason = future.result()
                except RuntimeError as e:
                    _ingest_status = {"running": False, "last_status": "error",
                                      "last_message": str(e), "files": file_statuses}
                    return

                fp = Path(fp)

                if chunks is None:
                    reason = base_or_reason
                    if reason != "annulé":
                        shutil.move(str(fp), str(QUARANTINE_DIR / fp.name))
                        logger.warning("INGEST | Rejeté : %s — %s", fp.name, reason)
                        _push_event("ingest_guardian", filename=fp.name, status="rejected", reason=reason[:100])
                    rejected_files += 1
                    continue

                base_metadata = base_or_reason
                _push_event("ingest_guardian", filename=fp.name, status="accepted")

                # 4. Vectorisation en batch (séquentiel — connexion psycopg non thread-safe)
                batch = [(text, {**meta, **base_metadata}) for text, meta in chunks]
                inserted = vm.add_documents_batch(batch, use_late_chunking=True)
                file_dup = len(batch) - inserted
                new_chunks += inserted
                duplicate_chunks += file_dup

                # 5. Archive
                file_statuses[fp.name] = "done"
                shutil.move(str(fp), str(ARCHIVE_DIR / fp.name))
                logger.info("INGEST | OK — %s (%d nouveaux, %d doublons)", fp.name, inserted, file_dup)
                _push_event("ingest_complete", filename=fp.name, new_chunks=inserted, duplicate_chunks=file_dup)

        accepted = total - rejected_files
        if rejected_files == total:
            _ingest_status = {"running": False, "last_status": "warning",
                              "last_message": "Fichier refusé — déplacé en quarantaine.", "files": file_statuses}
        elif rejected_files > 0:
            _ingest_status = {"running": False, "last_status": "warning",
                              "last_message": f"{accepted} fichier(s) ajouté(s) — {new_chunks} chunks ajoutés, {duplicate_chunks} doublons. {rejected_files} refusé(s) et déplacé(s) en quarantaine.",
                              "files": file_statuses}
        else:
            _ingest_status = {"running": False, "last_status": "success",
                              "last_message": f"Fichier ajouté ! {new_chunks} chunks ajoutés, {duplicate_chunks} doublons ignorés.",
                              "files": file_statuses}

    except Exception as e:
        _ingest_status = {"running": False, "last_status": "error", "last_message": str(e), "files": file_statuses}
        logger.error("INGEST | Erreur : %s", e, exc_info=True)
        _push_event("ingest_error", error=str(e)[:120])


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
        safe_name = Path(file.filename).name  # strip any subdirectory prefix (webkitdirectory)
        dest = NEW_FILES_DIR / safe_name
        contents = await file.read()
        with open(dest, "wb") as f:
            f.write(contents)
        saved_paths.append(dest)
        logger.info("INGEST | Fichier reçu : %s", safe_name)

    _ingest_cancel.clear()
    _ingest_status.update({"running": True, "last_status": "idle", "last_message": "Démarrage…"})
    t = _threading.Thread(target=_run_ingestion, args=[saved_paths], daemon=True)
    t.start()
    return {"started": True, "files": [f.filename for f in files]}


@app.get("/ingest/status")
def ingest_status():
    return _ingest_status


@app.post("/ingest/cancel", dependencies=[Depends(_require_api_key)])
def cancel_ingest():
    if not _ingest_status.get("running"):
        return {"cancelled": False, "detail": "Aucune ingestion en cours."}
    _ingest_cancel.set()
    return {"cancelled": True}


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
        logger.error("[GET_LOGS] Failed to fetch logs from DB.", exc_info=True)  # Log the full exception
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