"""
FastAPI backend for HELMo Oracle.

Exposes the RAG pipeline as a REST API so a separate frontend
(e.g. deployed on Vercel) can call it over HTTP.
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Optional
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from langgraph.prebuilt import create_react_agent
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pydantic import BaseModel
from psycopg import sql

import mcp_server as _mcp_module
from core.agent.tools_oracle import get_search_tool
from core.context.memory_manager import MemoryManager
from core.context.session_manager import SessionManager
from core.database.vector_manager import VectorManager
from core.pipeline.pii_manager import PIIManager
# Import logger and utils from the corrected logger module
from core.utils.logger import logger, set_shared_conn, log_to_db_sync
from core.utils.utils import load_config, load_base_prompt, format_response
from providers import get_llm, get_available_models, PROVIDER_LABELS

# --- Configuration Loading ---
config = load_config()
BASE_SYSTEM_PROMPT = load_base_prompt()

logger.info("━" * 50)
logger.info("Oracle API démarrage...")

# --- Service Initialization ---
_embeddings = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-base")
logger.info("Modèle embeddings chargé : intfloat/multilingual-e5-base")

vm = VectorManager(embeddings_model=_embeddings)
set_shared_conn(vm.conn) # Pass the connection to the shared logger

if vm.is_db_available():
    logger.info("VectorManager connecté à PostgreSQL.")
else:
    logger.error("VectorManager n'a PAS pu se connecter à PostgreSQL. Les logs DB et la recherche seront indisponibles.")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
    search_tool = get_search_tool(vm, k_final=k_final, cot_storage=[])
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
    return response_text, []

# --- Routes ---
@app.get("/health")
def health():
    checks = {}

    # Database
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

    # Embeddings
    checks["embeddings"] = {"status": "ok", "model": "intfloat/multilingual-e5-base"}

    return {"status": "ok", "checks": checks}

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

    try:
        response, cot_storage = _run_agent(
            session=session, masked_message=masked_message, provider=req.provider,
            model=model, temperature=req.temperature, k_final=req.k_final,
        )
    except Exception as e:
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
    return {"session_id": session["session_id"], "response": response, "cot_results": cot_storage}

@app.get("/archives")
def list_archives():
    return {"sources": vm.list_sources()}

# --- Ingestion ---
_ingest_status = {"running": False, "last_status": "idle", "last_message": ""}
# ... (ingestion code remains the same)

# --- Logs ---
@app.get("/logs", dependencies=[Depends(_require_api_key)])
def get_logs(lines: int = 100, level: Optional[str] = None, source: Optional[str] = None):
    """Fetches logs from the database with optional filters."""
    if not vm.is_db_available():
        logger.error("[GET_LOGS] DB not available.")
        raise HTTPException(status_code=503, detail="Base de données indisponible")

    try:
        with vm.conn.cursor() as cur:
            base_query = sql.SQL("""
                SELECT l.id, l.created_at, l.level, l.source, l.message, l.metadata, p.first_name, p.last_name
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
            base_query += sql.SQL(" ORDER BY l.created_at DESC LIMIT %s")
            params.append(lines)
            
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
        logger.error("[GET_LOGS] Failed to fetch logs from DB.", exc_info=True) # Log the full exception
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

# --- Entry Point ---
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
