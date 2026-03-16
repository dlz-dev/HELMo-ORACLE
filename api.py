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

# ─── Singletons (loaded once at startup) ─────────────────────────────────────

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


@app.get("/providers")
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
        raise HTTPException(status_code=500, detail=f"LLM init error: {e}")

    # Build agent — cot_storage collects CoT results for this request
    cot_storage: list = []
    enriched_prompt, history = mm.build_agent_input(session, BASE_SYSTEM_PROMPT)
    search_tool = get_search_tool(vm, k_final=req.k_final, cot_storage=cot_storage)
    agent = create_react_agent(llm, [search_tool], prompt=enriched_prompt)

    # Run agent
    try:
        result = agent.invoke({"messages": history})
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


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
