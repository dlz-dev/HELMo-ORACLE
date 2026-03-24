"""
FastAPI backend for HELMo Oracle.

Exposes the RAG pipeline as a REST API so a separate frontend
(e.g. deployed on Vercel) can call it over HTTP.
"""

# ─── Logging ──────────────────────────────────────────────────────────────────
import logging
from pathlib import Path as _Path
from typing import Optional

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from langgraph.prebuilt import create_react_agent
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pydantic import BaseModel

from core.agent.tools_oracle import get_search_tool
from core.context.memory_manager import MemoryManager
from core.context.session_manager import SessionManager
from core.database.vector_manager import VectorManager
from core.pipeline.pii_manager import PIIManager
from core.utils.utils import load_config, load_base_prompt, format_response
from providers import get_llm, get_available_models, PROVIDER_LABELS
import mcp_server as _mcp_module

_LOG_DIR = _Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "oracle.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),  # garde aussi les logs dans le terminal
    ],
    force=True,
)
logger = logging.getLogger("oracle")

config = load_config()
BASE_SYSTEM_PROMPT = load_base_prompt()

logger.info("━" * 50)
logger.info("Oracle API démarrage...")
_embeddings = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-base")
logger.info("Modèle embeddings chargé : intfloat/multilingual-e5-base")
vm = VectorManager(embeddings_model=_embeddings)
if vm.is_db_available():
    logger.info("VectorManager connecté à Supabase")
else:
    logger.error("VectorManager n'a pas pu se connecter à Supabase")
_mcp_module.setup(vm)
sm = SessionManager()
mm = MemoryManager(
    max_recent_tokens=config.get("memory", {}).get("max_recent_tokens", 1200),
    min_recent_messages=config.get("memory", {}).get("min_recent_messages", 4),
)
pii = PIIManager()

# ─── Auth ─────────────────────────────────────────────────────────────────────

_ADMIN_API_KEY = os.getenv("API_SECRET_KEY", "")

def _require_api_key(x_api_key: str = Header(...)):
    if not _ADMIN_API_KEY or x_api_key != _ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")

# ─── App ──────────────────────────────────────────────────────────────────────

_mcp_asgi = _mcp_module.mcp.streamable_http_app()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with _mcp_asgi.router.lifespan_context(app):
        yield


app = FastAPI(title="HELMo Oracle API", version="1.0.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restreindre au domaine Vercel en production si souhaité
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/mcp", _mcp_asgi)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    provider: str = config.get("llm", {}).get("default_provider", "groq")
    model: Optional[str] = None
    temperature: float = float(config.get("llm", {}).get("temperature", 0.0))
    k_final: int = config.get("search", {}).get("k_final", 5)


class RenameRequest(BaseModel):
    title: str


# ─── Routes ───────────────────────────────────────────────────────────────────

# ─── Shared agent logic ───────────────────────────────────────────────────────

def _build_lc_history(history_tuples, masked_message):
    """Convertit les tuples (role, content) en messages LangChain."""
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
    Construit et exécute l'agent LangGraph.
    Partagé entre la route /chat (sync) et /api/chat (stream).

    Returns:
        (response_text, cot_storage)
    Raises:
        Exception si le LLM ou l'agent échoue.
    """
    if not vm.is_db_available():
        logger.error("CHAT | DB indisponible, réponse directe.")
        return "La base de donnée est actuellement indisponible, veuillez réessayer plus tard.", []

    llm = get_llm(
        provider_key=provider,
        model=model,
        config={**config, "llm": {**config.get("llm", {}), "temperature": temperature}},
    )
    cot_storage: list = []
    enriched_prompt, history_tuples = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)
    search_tool = get_search_tool(vm, k_final=k_final, cot_storage=cot_storage)
    agent = create_react_agent(llm, [search_tool], prompt=enriched_prompt)
    lc_history = _build_lc_history(history_tuples, masked_message)
    result = agent.invoke({"messages": lc_history})
    response_text = format_response(result["messages"][-1].content)
    return response_text, cot_storage


@app.get("/health")
def health():
    return {"status": "ok"}


def list_providers():
    return {"providers": PROVIDER_LABELS}


@app.get("/providers/{provider}/models")
def list_models(provider: str):
    try:
        return {"models": get_available_models(provider, config)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/sessions")
def list_sessions():
    return {"sessions": sm.list_sessions()}


@app.post("/sessions")
def create_session(provider: str = "", model: str = ""):
    session = sm.new_session(provider=provider, model=model)
    sm.save(session)
    return session


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    session = sm.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    sm.delete(session_id)
    return {"deleted": session_id}


@app.patch("/sessions/{session_id}/rename")
def rename_session(session_id: str, body: RenameRequest):
    session = sm.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["title"] = body.title
    sm.save(session)
    return {"session_id": session_id, "title": body.title}


@app.post("/chat")
def chat(req: ChatRequest):
    """Route synchrone — conservée pour compatibilité. Préférer /api/chat (streaming)."""
    if req.session_id:
        session = sm.load(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = sm.new_session(provider=req.provider, model=req.model or "")

    model = req.model or config.get("llm", {}).get("default_model", "")
    masked_message = pii.mask_text(req.message)
    session.setdefault("messages", []).append({"role": "user", "content": masked_message})
    sm.save(session)

    try:
        response, cot_storage = _run_agent(
            session=session,
            masked_message=masked_message,
            provider=req.provider,
            model=model,
            temperature=req.temperature,
            k_final=req.k_final,
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
    sm.save(session)
    return {"session_id": session["session_id"], "response": response, "cot_results": cot_storage}


@app.get("/archives")
def list_archives():
    return {"sources": vm.list_sources()}


# ─── Ingestion ────────────────────────────────────────────────────────────────

import threading as _threading
from fastapi import UploadFile, File

_ingest_status = {"running": False, "last_status": "idle", "last_message": ""}


def _run_ingestion(file_paths):
    global _ingest_status
    from pathlib import Path
    from core.agent.guardian import is_valid_lore_file
    from core.database.vector_manager import VectorManager
    from core.utils.utils import ARCHIVE_DIR, QUARANTINE_DIR
    from converters import convert_csv, convert_markdown, convert_text, convert_json, convert_pdf
    from converters.convert_unstructured import process_with_unstructured
    import shutil

    total = len(file_paths)
    rejected_count = 0
    success_count = 0
    
    try:
        for i, fp in enumerate(file_paths):
            fp = Path(fp)
            _ingest_status["last_message"] = f"Fichier {i+1}/{total} — Validation de {fp.name}…"

            # 1. Guardian
            if not is_valid_lore_file(str(fp)):
                shutil.move(str(fp), str(QUARANTINE_DIR / fp.name))
                logger.warning("INGEST | Rejeté : %s", fp.name)
                rejected_count += 1
                continue

            # 2. Conversion
            _ingest_status["last_message"] = f"Fichier {i+1}/{total} — Conversion de {fp.name}…"
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

            # 3. Vectorisation
            _ingest_status["last_message"] = f"Fichier {i+1}/{total} — Vectorisation de {fp.name}…"
            db = VectorManager(embeddings_model=_embeddings)
            for text, meta in chunks:
                db.add_document(text, metadata={"source": fp.name, **meta})

            # 4. Archive
            shutil.move(str(fp), str(ARCHIVE_DIR / fp.name))
            logger.info("INGEST | OK — %s (%d chunks)", fp.name, len(chunks))
            success_count += 1

        final_status = "error" if rejected_count > 0 else "success"
        message = f"Ingestion terminée. {success_count} succès, {rejected_count} rejet(s)."
        _ingest_status = {"running": False, "last_status": final_status, "last_message": message}

    except Exception as e:
        _ingest_status = {"running": False, "last_status": "error", "last_message": str(e)}
        logger.error("INGEST | Erreur : %s", e)


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
        dest = NEW_FILES_DIR / _Path(file.filename).name
        contents = await file.read()
        with open(dest, "wb") as f:
            f.write(contents)
        saved_paths.append(dest)
        logger.info("INGEST | Fichier reçu : %s", file.filename)

    _ingest_status["running"] = True
    t = _threading.Thread(target=_run_ingestion, args=[saved_paths], daemon=True)
    t.start()
    return {"started": True, "files": [f.filename for f in files]}


@app.get("/ingest/status")
def ingest_status():
    return _ingest_status


# ─── Streaming chat (Vercel AI SDK compatible) ────────────────────────────────

import json as _json
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator


class _SDKMessage(BaseModel):
    role: str
    content: str


class StreamChatRequest(BaseModel):
    messages: list[_SDKMessage] = []
    session_id: Optional[str] = None
    provider: str = config.get("llm", {}).get("default_provider", "groq")
    model: Optional[str] = None
    temperature: float = float(config.get("llm", {}).get("temperature", 0.0))
    k_final: int = config.get("search", {}).get("k_final", 5)


async def _generate_stream(req: StreamChatRequest) -> AsyncGenerator[str, None]:
    """Génère la réponse en streaming au format Vercel AI SDK (data stream protocol)."""
    model = req.model or config.get("llm", {}).get("default_model", "")

    # Extract last user message
    user_msgs = [m for m in req.messages if m.role == "user"]
    if not user_msgs:
        yield f"3:{_json.dumps('Aucun message utilisateur')}\n"
        return
    last_message = user_msgs[-1].content
    masked_message = pii.mask_text(last_message)

    # Load or create session — UNE session par conversation
    if req.session_id:
        session = sm.load(req.session_id) or sm.new_session(provider=req.provider, model=model)
    else:
        session = sm.new_session(provider=req.provider, model=model)

    session_id = session["session_id"]

    # Ajoute uniquement le nouveau message utilisateur (ne pas écraser l'historique)
    session.setdefault("messages", []).append({"role": "user", "content": masked_message})
    sm.save(session)

    # Build agent via fonction partagée
    try:
        response_text, cot_storage = _run_agent(
            session=session,
            masked_message=masked_message,
            provider=req.provider,
            model=model,
            temperature=req.temperature,
            k_final=req.k_final,
        )
    except Exception as e:
        yield f"3:{_json.dumps(str(e))}\n"
        return

    # Stream token by token (Vercel AI SDK data stream format)
    full_response = ""
    for char in response_text:
        full_response += char
        yield f"0:{_json.dumps(char)}\n"

    logger.info(
        "CHAT | provider=%s model=%s session=%s sources=%d tokens~%d",
        req.provider, model, session_id[:8],
        len(cot_storage),
        len(full_response) // 4,
    )

    # Persist assistant reply
    session["messages"].append({
        "role": "assistant",
        "content": full_response,
        "_cot": cot_storage,
    })

    if mm.needs_summarization(session["messages"], session.get("summary", "")):
        _llm_for_compress = get_llm(
            provider_key=req.provider, model=model,
            config={**config, "llm": {**config.get("llm", {}), "temperature": req.temperature}},
        )
        session = mm.compress(session, _llm_for_compress)

    session["provider"] = req.provider
    session["model"] = model
    sm.save(session)

    # Fin du stream — Vercel AI SDK attend ce format
    yield f"d:{_json.dumps({'finishReason': 'stop', 'usage': {'promptTokens': 0, 'completionTokens': 0}})}\n"


@app.post("/api/chat")
async def chat_stream(req: StreamChatRequest):
    """
    Route streaming compatible Vercel AI SDK.
    Utilise le data stream protocol : 0:token 3:error d:finish
    """
    return StreamingResponse(
        _generate_stream(req),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Session-Id": req.session_id or "",
            "X-Vercel-AI-Data-Stream": "v1",
            "Cache-Control": "no-cache",
        },
    )


# ─── Health check complet ─────────────────────────────────────────────────────

@app.get("/health/full")
async def health_full():
    """
    Vérifie l'état de tous les composants du système.
    Teste : base de données, embeddings, et chaque clé API configurée.
    """
    import os
    import time
    results = {}

    # ── Base de données ───────────────────────────────────────────
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

    # ── Modèle embeddings ─────────────────────────────────────────
    try:
        start = time.time()
        vm.embeddings_model.get_text_embedding("test")
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
        "anthropic": ("ANTHROPIC_API_KEY", "langchain_anthropic", "ChatAnthropic", {"model": "claude-haiku-4-5"}),
        "gemini": ("GOOGLE_API_KEY", "langchain_google_genai", "ChatGoogleGenerativeAI", {"model": "gemini-2.0-flash"}),
    }

    from langchain_core.messages import HumanMessage as HM

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
            llm.invoke([HM(content="Reply with one word: ok")])
            results[provider_name] = {
                "status": "ok",
                "latency_ms": round((time.time() - start) * 1000),
            }
        except Exception as e:
            results[provider_name] = {"status": "error", "error": str(e)[:120]}

    # ── Résumé global ─────────────────────────────────────────────
    has_error = any(
        v.get("status") == "error"
        for v in results.values()
    )
    return {
        "status": "degraded" if has_error else "ok",
        "checks": results,
    }


# ─── Test provider ────────────────────────────────────────────────────────────

class TestRequest(BaseModel):
    provider: str
    model: str
    message: str
    temperature: float = 0.0


@app.post("/test")
def test_provider(req: TestRequest):
    """Vérifie qu'un provider/modèle répond correctement."""
    try:
        llm = get_llm(
            provider_key=req.provider,
            model=req.model,
            config={**config, "llm": {**config.get("llm", {}), "temperature": req.temperature}},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur d'initialisation : {e}")

    from langchain_core.messages import HumanMessage
    try:
        result = llm.invoke([HumanMessage(content=req.message)])
        return {
            "provider": req.provider,
            "model": req.model,
            "response": result.content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur LLM : {e}")


# ─── Logs ─────────────────────────────────────────────────────────────────────

@app.get("/logs", dependencies=[Depends(_require_api_key)])
def get_logs(lines: int = 100):
    """Retourne les N dernières lignes du fichier de log."""
    try:
        if not _LOG_FILE.exists():
            return {"logs": [], "total": 0}
        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        recent = all_lines[-lines:]
        return {
            "logs": [l.rstrip() for l in recent],
            "total": len(all_lines),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/logs", dependencies=[Depends(_require_api_key)])
def clear_logs():
    """Vide le fichier de log."""
    try:
        open(_LOG_FILE, "w").close()
        logger.info("Logs effacés par l'administrateur")
        return {"cleared": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # host="0.0.0.0" est requis en production pour écouter sur toutes les interfaces réseau
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)