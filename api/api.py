"""
FastAPI backend for HELMo Oracle.

Expose le pipeline RAG comme API REST pour le frontend.
"""

import asyncio
import json
import os
import queue
import shutil
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import redis as _redis_lib
import uvicorn
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from psycopg import sql
from pydantic import BaseModel

import core.pipeline.ingestion_worker as ingestion_worker
import mcp_server as _mcp_module
from core.agent.judge import _run_judge_sync
from core.agent.tools_oracle import get_search_tool
from core.context.memory_manager import MemoryManager
from core.context.session_manager import SessionManager
from core.database.db_connection import ensure_log_conn, get_log_conn, supabase_client
from core.database.vector_manager import VectorManager
from core.pipeline.pii_manager import PIIManager
from core.utils.logger import _LOG_FILE, log_to_db_sync, logger
from core.utils.utils import ARCHIVE_DIR, NEW_FILES_DIR, QUARANTINE_DIR, format_response, load_base_prompt, load_config
from providers import get_available_models, get_llm

# ── Configuration ──────────────────────────────────────────────────────────────

config = load_config()
BASE_SYSTEM_PROMPT = load_base_prompt()

# Surcharge la section "judge" avec les variables d'environnement du .env
_judge_overrides = {
    "provider": os.getenv("JUDGE_PROVIDER"),
    "model": os.getenv("JUDGE_MODEL"),
    "temperature": os.getenv("JUDGE_TEMP"),
}
if any(_judge_overrides.values()):
    config.setdefault("judge", {})
    for key, val in _judge_overrides.items():
        if val is not None:
            config["judge"][key] = float(val) if key == "temperature" else val

logger.info("━" * 50)
logger.info("Oracle API démarrage...")

# ── Services ───────────────────────────────────────────────────────────────────

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

# ── Redis Stream (monitoring dashboard) ───────────────────────────────────────

_redis = None
try:
    _redis = _redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379"), decode_responses=True)
    _redis.ping()
    logger.info("Redis connecté (monitoring stream).")
except Exception as e:
    logger.warning(f"Redis indisponible, monitoring désactivé : {e}")
    _redis = None

REDIS_STREAM = "oracle:events"
REDIS_MAX_LEN = 500


def _push_event(event_type: str, **kwargs):
    if _redis is None:
        return
    try:
        _redis.xadd(REDIS_STREAM, {"type": event_type, **{k: str(v) for k, v in kwargs.items()}},
                    maxlen=REDIS_MAX_LEN)
    except Exception:
        pass


# ── MCP + services ─────────────────────────────────────────────────────────────

_mcp_module.setup(vm, redis=_redis)
from mcp.server.transport_security import TransportSecurityMiddleware

TransportSecurityMiddleware._validate_host = lambda self, host: True  # Docker interne uniquement
_mcp_asgi = _mcp_module.mcp.sse_app()

ingestion_worker.setup(vm, _push_event)

sm = SessionManager()
mm = MemoryManager(
    max_recent_tokens=config.get("memory", {}).get("max_recent_tokens", 1200),
    min_recent_messages=config.get("memory", {}).get("min_recent_messages", 4),
)
pii = PIIManager()

# ── Auth ───────────────────────────────────────────────────────────────────────

_ADMIN_API_KEY = os.getenv("API_SECRET_KEY", "")


def _require_api_key(x_api_key: str = Header(...)):
    if not _ADMIN_API_KEY or x_api_key != _ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


# ── FastAPI App ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield


app = FastAPI(title="HELMo Oracle API", version="1.0.0", lifespan=_lifespan)

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)
app.mount("/mcp", _mcp_asgi)


# ── Schemas ────────────────────────────────────────────────────────────────────

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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_valid_uuid(val) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def _get_sm(user_id: Optional[str] = None) -> SessionManager:
    return SessionManager(user_id=user_id) if user_id and _is_valid_uuid(user_id) else sm


def _build_lc_history(history_tuples: list, masked_message: str) -> list:
    history = [HumanMessage(content=c) if r == "user" else AIMessage(content=c) for r, c in history_tuples]
    if not history or not isinstance(history[-1], HumanMessage) or history[-1].content != masked_message:
        history.append(HumanMessage(content=masked_message))
    return history


def _run_agent(session: dict, masked_message: str, provider: str, model: str,
               temperature: float, k_final: int, step_callback=None) -> tuple[str, list]:
    log_user_id = session.get("user_id") if _is_valid_uuid(session.get("user_id")) else None

    if step_callback:
        step_callback("analyse")

    cot_storage = []
    search_tool = get_search_tool(vm, k_final=k_final, cot_storage=cot_storage, step_callback=step_callback)
    llm = get_llm(
        provider_key=provider, model=model,
        config={**config, "llm": {**config.get("llm", {}), "temperature": temperature}},
    )
    agent = create_react_agent(llm, [search_tool], prompt=BASE_SYSTEM_PROMPT)
    _, history_tuples = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)
    lc_history = _build_lc_history(history_tuples, masked_message)

    if step_callback:
        step_callback("answer")

    start = time.time()
    result = agent.invoke({"messages": lc_history})
    response_text = format_response(result["messages"][-1].content)

    log_to_db_sync(
        level="INFO", source="RAG_PROFILING",
        message="LLM response generated",
        metadata={"duration_seconds": time.time() - start, "provider": provider, "model": model},
        user_id=log_user_id,
    )
    return response_text, cot_storage


# ── Routes : Health ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    checks = {"embeddings": {"status": "ok", "model": "nomic-embed-text"}}
    if vm.is_db_available():
        try:
            with vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT metadata->>'source') FROM documents")
                checks["database"] = {"status": "ok", "documents": cur.fetchone()[0]}
        except Exception as e:
            checks["database"] = {"status": "error", "error": str(e)}
    else:
        checks["database"] = {"status": "error", "error": "Connexion indisponible"}
    return {"status": "ok", "checks": checks}


@app.get("/health/full")
def health_full():
    """Vérifie l'état de tous les composants (DB, embeddings, clés API)."""
    results = {}

    if vm.is_db_available():
        try:
            start = time.time()
            with vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT metadata->>'source') FROM documents")
                results["database"] = {"status": "ok", "documents": cur.fetchone()[0],
                                       "latency_ms": round((time.time() - start) * 1000)}
        except Exception as e:
            results["database"] = {"status": "error", "error": str(e)}
    else:
        results["database"] = {"status": "error", "error": "Connexion indisponible"}

    try:
        start = time.time()
        _embeddings.embed_query("test")
        results["embeddings"] = {"status": "ok", "model": "nomic-embed-text",
                                 "latency_ms": round((time.time() - start) * 1000)}
    except Exception as e:
        results["embeddings"] = {"status": "error", "error": str(e)}

    providers_to_check = {
        "groq": ("GROQ_API_KEY", "langchain_groq", "ChatGroq", {"model": "llama-3.1-8b-instant"}),
        "openai": ("OPENAI_API_KEY", "langchain_openai", "ChatOpenAI", {"model": "gpt-4o-mini"}),
        "anthropic": ("ANTHROPIC_API_KEY", "langchain_anthropic", "ChatAnthropic",
                      {"model": "claude-haiku-4-5-20251001"}),
        "gemini": ("GOOGLE_API_KEY", "langchain_google_genai", "ChatGoogleGenerativeAI", {"model": "gemini-2.0-flash"}),
    }
    for provider_name, (env_var, module, cls_name, kwargs) in providers_to_check.items():
        api_key = os.environ.get(env_var, "")
        if not api_key:
            results[provider_name] = {"status": "not_configured"}
            continue
        try:
            start = time.time()
            cls = getattr(__import__(module, fromlist=[cls_name]), cls_name)
            cls(api_key=api_key, temperature=0, **kwargs).invoke([HumanMessage(content="Reply with one word: ok")])
            results[provider_name] = {"status": "ok", "latency_ms": round((time.time() - start) * 1000)}
        except Exception as e:
            results[provider_name] = {"status": "error", "error": str(e)[:120]}

    has_error = any(v.get("status") == "error" for v in results.values())
    return {"status": "degraded" if has_error else "ok", "checks": results}


# ── Routes : Metrics ───────────────────────────────────────────────────────────

@app.get("/metrics")
def get_metrics():
    """Stats réelles + flux Redis pour le dashboard admin."""
    db_docs = 0
    db_available = vm.is_db_available()
    if db_available:
        try:
            with vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT metadata->>'source') FROM documents")
                db_docs = cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Metrics SQL Error (docs): {e}")

    user_count = 1
    if ensure_log_conn():
        try:
            with get_log_conn().cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM profiles")
                user_count = cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Metrics SQL Error (users): {e}")

    base_stats = {"total_chunks_ingested": db_docs, "total_users": user_count, "db_ok": db_available}

    if _redis is None:
        return {"available": False, "events": [], "stats": base_stats}

    try:
        raw = _redis.xrevrange(REDIS_STREAM, count=100)
    except Exception as e:
        logger.error(f"Metrics Redis Error: {e}")
        return {"available": False, "error": str(e), "events": [], "stats": base_stats}

    events = [
        {
            "id": entry_id,
            "ts": int(entry_id.split("-")[0]) / 1000,
            "type": fields.get("type"),
            "question": fields.get("question", ""),
            "provider": fields.get("provider", ""),
            "latency_ms": int(fields.get("latency_ms", 0)),
            "source": fields.get("source", "web"),
            "filename": fields.get("filename", ""),
            "status": fields.get("status", ""),
            "reason": fields.get("reason", ""),
            "new_chunks": int(fields.get("new_chunks", 0)),
            "duplicate_chunks": int(fields.get("duplicate_chunks", 0)),
            "error": fields.get("error", ""),
        }
        for entry_id, fields in raw
    ]

    now = time.time()
    chat_events = [e for e in events if e["type"] == "chat"]
    latencies = [e["latency_ms"] for e in chat_events if e["latency_ms"] > 0]

    stats = {
        **base_stats,
        "total_queries": len(chat_events),
        "queries_last_minute": sum(1 for e in chat_events if now - e["ts"] < 60),
        "queries_last_hour": sum(1 for e in chat_events if now - e["ts"] < 3600),
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
    }
    return {"available": True, "events": events, "stats": stats}


# ── Routes : Providers & Sessions ─────────────────────────────────────────────

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


# ── Routes : Chat ──────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    request_sm = _get_sm(req.user_id)

    if req.session_id:
        session = request_sm.load(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = request_sm.new_session(provider=req.provider, model=req.model or "")

    # Limite invités : 5 messages max par session
    if not req.user_id or not _is_valid_uuid(req.user_id):
        guest_msgs = [m for m in session.get("messages", []) if m["role"] == "user"]
        if len(guest_msgs) >= 5:
            raise HTTPException(status_code=429,
                                detail="Limite de 5 messages atteinte. Connectez-vous pour continuer.")

    model = req.model or config.get("llm", {}).get("default_model", "")
    masked_message = pii.mask_text(req.message)
    session.setdefault("messages", []).append({"role": "user", "content": masked_message})
    request_sm.save(session)

    async def event_stream():
        chat_start = time.time()
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session['session_id']})}\n\n"

        step_q: queue.SimpleQueue = queue.SimpleQueue()

        try:
            agent_task = asyncio.create_task(asyncio.to_thread(
                _run_agent,
                session=session, masked_message=masked_message, provider=req.provider,
                model=model, temperature=req.temperature, k_final=req.k_final,
                step_callback=lambda name: step_q.put(name),
            ))

            while not agent_task.done():
                try:
                    step = step_q.get_nowait()
                    yield f"data: {json.dumps({'type': 'step', 'step': step})}\n\n"
                except queue.Empty:
                    pass
                await asyncio.sleep(0.04)

            while not step_q.empty():
                yield f"data: {json.dumps({'type': 'step', 'step': step_q.get_nowait()})}\n\n"

            response, cot_storage = agent_task.result()

        except Exception as e:
            logger.error(f"Erreur critique dans le RAG: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        _push_event(
            "chat",
            question=masked_message[:120],
            provider=req.provider,
            model=model,
            latency_ms=round((time.time() - chat_start) * 1000),
            source="discord" if req.user_id == "discord" else "web",
        )

        for i in range(0, len(response), 20):
            yield f"data: {json.dumps({'type': 'text', 'content': response[i:i + 20]})}\n\n"
            await asyncio.sleep(0.01)

        if cot_storage:
            yield f"data: {json.dumps({'type': 'cot', 'results': cot_storage})}\n\n"

        session["messages"].append({"role": "assistant", "content": response, "_cot": cot_storage})
        session["provider"] = req.provider
        session["model"] = model
        request_sm.save(session)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

        if mm.needs_summarization(session["messages"], session.get("summary", "")):
            async def _compress():
                try:
                    session_updated = await asyncio.to_thread(
                        mm.compress, session,
                        get_llm(provider_key=req.provider, model=model,
                                config={**config, "llm": {**config.get("llm", {}), "temperature": req.temperature}}),
                    )
                    session.update(session_updated)
                    request_sm.save(session)
                except Exception as e:
                    logger.error(f"Erreur compression mémoire : {e}", exc_info=True)

            asyncio.create_task(_compress())

        asyncio.create_task(asyncio.wait_for(
            asyncio.to_thread(
                _run_judge_sync,
                query=masked_message, response=response, cot_storage=cot_storage,
                user_id=req.user_id, session_id=session["session_id"], config=config,
            ),
            timeout=20.0,
        ))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "X-Session-Id": session["session_id"]},
    )


@app.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    """Endpoint synchrone pour clients sans support SSE (ex: Roblox)."""
    model = req.model or config.get("llm", {}).get("default_model", "")
    masked_message = pii.mask_text(req.message)
    session = {
        "session_id": str(uuid.uuid4()),
        "user_id": None, "title": "Roblox",
        "provider": req.provider, "model": model,
        "messages": [{"role": "user", "content": masked_message}],
        "summary": "", "created_at": "", "updated_at": "",
    }
    try:
        response, _ = await asyncio.to_thread(
            _run_agent,
            session=session, masked_message=masked_message, provider=req.provider,
            model=model, temperature=req.temperature, k_final=req.k_final,
        )
    except Exception as e:
        logger.error(f"Erreur chat/sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return {"response": response}


# ── Routes : Archives ──────────────────────────────────────────────────────────

@app.get("/archives")
def list_archives():
    return {"sources": vm.list_sources()}


# ── Routes : Ingestion ─────────────────────────────────────────────────────────

@app.post("/ingest", dependencies=[Depends(_require_api_key)])
async def trigger_ingest(files: list[UploadFile] = File(...)):
    if ingestion_worker.status.get("running"):
        return {"started": False, "detail": "Une ingestion est déjà en cours."}

    for d in (NEW_FILES_DIR, ARCHIVE_DIR, QUARANTINE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for file in files:
        safe_name = Path(file.filename).name
        dest = NEW_FILES_DIR / safe_name if safe_name.startswith("lore_") else QUARANTINE_DIR / safe_name
        with open(dest, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        if safe_name.startswith("lore_"):
            saved_paths.append(dest)
            logger.info("INGEST | Fichier reçu : %s", safe_name)
        else:
            logger.warning("INGEST | Refusé (nom invalide) — mis en quarantaine : %s", safe_name)

    if not saved_paths:
        return {"started": False, "detail": "Aucun fichier valide. Tous les fichiers ont été mis en quarantaine."}

    ingestion_worker.cancel_event.clear()
    ingestion_worker.status.update({"running": True, "last_status": "idle", "last_message": "Démarrage…"})
    threading.Thread(target=ingestion_worker.run, args=[saved_paths], daemon=True).start()
    return {"started": True, "files": [f.filename for f in files]}


@app.get("/ingest/status")
def ingest_status():
    return ingestion_worker.status


@app.post("/ingest/cancel", dependencies=[Depends(_require_api_key)])
def cancel_ingest():
    if not ingestion_worker.status.get("running"):
        return {"cancelled": False, "detail": "Aucune ingestion en cours."}
    ingestion_worker.cancel_event.set()
    return {"cancelled": True}


# ── Routes : Logs ──────────────────────────────────────────────────────────────

@app.get("/logs", dependencies=[Depends(_require_api_key)])
def get_logs(lines: int = 100, offset: int = 0, level: Optional[str] = None, source: Optional[str] = None):
    """Récupère les logs depuis Supabase avec filtres et pagination optionnels."""
    if not ensure_log_conn():
        logger.error("[GET_LOGS] Connexion Supabase (logs) indisponible.")
        raise HTTPException(status_code=503, detail="Connexion logs indisponible")

    try:
        with get_log_conn().cursor() as cur:
            query = sql.SQL("""
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
            conditions, params = [], []
            if level:
                conditions.append(sql.SQL("l.level = %s"))
                params.append(level)
            if source:
                conditions.append(sql.SQL("l.source = %s"))
                params.append(source)
            if conditions:
                query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
            query += sql.SQL(" ORDER BY l.created_at DESC LIMIT %s OFFSET %s")
            params.extend([lines, offset])

            cur.execute(query, params)
            rows = cur.fetchall()

        return {
            "logs": [
                {"id": r[0], "created_at": r[1], "level": r[2], "source": r[3],
                 "message": r[4], "metadata": r[5],
                 "profiles": {"first_name": r[6], "last_name": r[7]} if r[6] else None}
                for r in rows
            ]
        }
    except Exception as e:
        logger.error("[GET_LOGS] Failed to fetch logs from DB.", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des logs: {e}")


@app.delete("/logs", dependencies=[Depends(_require_api_key)])
def clear_logs():
    """Efface le fichier de log local (n'affecte pas la DB)."""
    try:
        with open(_LOG_FILE, "w") as f:
            f.truncate()
        logger.info("Logs effacés par l'administrateur (fichier local uniquement)")
        return {"cleared": True}
    except Exception as e:
        logger.error("[CLEAR_LOGS] Failed to clear local log file.", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Routes : Feedback ──────────────────────────────────────────────────────────

@app.post("/feedback", status_code=201)
def submit_feedback(req: FeedbackRequest):
    """Enregistre un feedback utilisateur (note 1-5 + commentaire optionnel)."""
    if not (1 <= req.rating <= 5):
        raise HTTPException(status_code=422, detail="La note doit être entre 1 et 5.")
    if supabase_client is None:
        raise HTTPException(status_code=503, detail="Client Supabase indisponible.")

    user_id = req.user_id if req.user_id and _is_valid_uuid(req.user_id) else None
    try:
        supabase_client.table("feedback").insert({
            "session_id": req.session_id, "user_id": user_id,
            "rating": req.rating, "comment": req.comment,
        }).execute()
        logger.info(f"Feedback reçu — session={req.session_id} note={req.rating}")
        log_to_db_sync(
            level="INFO", source="FEEDBACK",
            message=f"Note {req.rating}/5",
            metadata={"session_id": req.session_id, "rating": req.rating, "comment": req.comment},
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Erreur insertion feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement du feedback.")
    return {"status": "ok"}


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
