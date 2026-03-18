"""
FastAPI backend for HELMo Oracle.

Exposes the RAG pipeline as a REST API so a separate frontend
(e.g. deployed on Vercel) can call it over HTTP.
"""

from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from core.agent.tools_oracle import get_search_tool
from core.context.memory_manager import MemoryManager
from core.context.session_manager import SessionManager
from core.database.vector_manager import VectorManager
from core.pipeline.pii_manager import PIIManager
from providers import get_llm, get_available_models, PROVIDER_LABELS
from core.utils.utils import load_config, load_base_prompt, format_response


config = load_config()
BASE_SYSTEM_PROMPT = load_base_prompt()

_embeddings = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-base")
vm = VectorManager(embeddings_model=_embeddings)
sm = SessionManager()
mm = MemoryManager(
    max_recent_tokens=config.get("memory", {}).get("max_recent_tokens", 1200),
    min_recent_messages=config.get("memory", {}).get("min_recent_messages", 4),
)
pii = PIIManager()

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="HELMo Oracle API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restreindre au domaine Vercel en production si souhaité
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    # Load or create session
    if req.session_id:
        session = sm.load(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = sm.new_session(provider=req.provider, model=req.model or "")

    # Resolve model (fallback to config default)
    model = req.model or config.get("llm", {}).get("default_model", "")

    # Mask PII before storing and sending to LLM
    masked_message = pii.mask_text(req.message)
    session["messages"] = [{"role": m.role, "content": m.content} for m in req.messages]
    sm.save(session)

    # Build LLM
    try:
        llm = get_llm(
            provider_key=req.provider,
            model=model,
            config={**config, "llm": {**config.get("llm", {}), "temperature": req.temperature}},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM init error: {e}")

    # Build agent — cot_storage collects CoT results for this request
    cot_storage: list = []
    enriched_prompt, history_tuples = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)
    search_tool = get_search_tool(vm, k_final=req.k_final, cot_storage=cot_storage)
    agent = create_react_agent(llm, [search_tool], prompt=enriched_prompt)

    # Convertir les tuples en objets LangChain messages
    from langchain_core.messages import HumanMessage as HM, AIMessage as AM
    lc_history = []
    for role, content in history_tuples:
        if role == "user":
            lc_history.append(HM(content=content))
        else:
            lc_history.append(AM(content=content))

    # S'assurer que le dernier message est bien la question actuelle
    if not lc_history or not isinstance(lc_history[-1], HM) or lc_history[-1].content != masked_message:
        lc_history.append(HM(content=masked_message))

    # Run agent
    try:
        result = agent.invoke({"messages": lc_history})
        response = format_response(result["messages"][-1].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Persist assistant reply
    session["messages"].append({
        "role": "assistant",
        "content": response,
        "_cot": cot_storage,
    })

    # Compress memory if needed
    if mm.needs_summarization(session["messages"], session.get("summary", "")):
        session = mm.compress(session, llm)

    session["provider"] = req.provider
    session["model"] = model
    sm.save(session)

    return {
        "session_id": session["session_id"],
        "response": response,
        "cot_results": cot_storage,
    }


@app.get("/archives")
def list_archives():
    return {"sources": vm.list_sources()}


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

    # Build LLM
    try:
        llm = get_llm(
            provider_key=req.provider,
            model=model,
            config={**config, "llm": {**config.get("llm", {}), "temperature": req.temperature}},
        )
    except Exception as e:
        yield f"3:{_json.dumps(str(e))}\n"
        return

    # Build agent
    cot_storage: list = []
    enriched_prompt, history_tuples = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)
    search_tool = get_search_tool(vm, k_final=req.k_final, cot_storage=cot_storage)
    agent = create_react_agent(llm, [search_tool], prompt=enriched_prompt)

    # Convertir les tuples en objets LangChain messages
    from langchain_core.messages import HumanMessage as HM, AIMessage as AM
    lc_history = []
    for role, content in history_tuples:
        if role == "user":
            lc_history.append(HM(content=content))
        else:
            lc_history.append(AM(content=content))

    # S'assurer que le dernier message est bien la question actuelle
    if not lc_history or not isinstance(lc_history[-1], HM) or lc_history[-1].content != masked_message:
        lc_history.append(HM(content=masked_message))

    # Run and stream
    full_response = ""
    try:
        result = agent.invoke({"messages": lc_history})
        response_text = format_response(result["messages"][-1].content)

        # Stream token by token (Vercel AI SDK data stream format)
        for char in response_text:
            full_response += char
            yield f"0:{_json.dumps(char)}\n"

    except Exception as e:
        yield f"3:{_json.dumps(str(e))}\n"
        return

    # Persist assistant reply
    session["messages"].append({
        "role": "assistant",
        "content": full_response,
        "_cot": cot_storage,
    })

    if mm.needs_summarization(session["messages"], session.get("summary", "")):
        session = mm.compress(session, llm)

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


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)