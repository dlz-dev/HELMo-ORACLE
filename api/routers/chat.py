import asyncio
import json
import queue as _queue
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage as HM, AIMessage as AM
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

import state
from core.agent.judge import _run_judge_sync
from core.agent.tools_oracle import get_search_tool
from core.utils.logger import logger, log_to_db_sync
from core.utils.utils import format_response
from providers import get_llm

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    user_id: Optional[str] = None
    provider: str = state.config.get("llm", {}).get("default_provider", "groq")
    model: Optional[str] = None
    temperature: float = float(state.config.get("llm", {}).get("temperature", 0.0))
    k_final: int = state.config.get("search", {}).get("k_final", 5)


def _build_lc_history(history_tuples, masked_message):
    lc_history = []
    for role, content in history_tuples:
        lc_history.append(HM(content=content) if role == "user" else AM(content=content))
    if not lc_history or not isinstance(lc_history[-1], HM) or lc_history[-1].content != masked_message:
        lc_history.append(HM(content=masked_message))
    return lc_history


def _run_agent(session: dict, masked_message: str, provider: str, model: str,
               temperature: float, k_final: int, step_callback=None) -> tuple[str, list]:
    user_id = session.get("user_id")
    log_user_id = user_id if state.is_valid_uuid(user_id) else None

    if step_callback:
        step_callback("analyse")

    cot_storage = []
    search_tool = get_search_tool(state.vm, k_final=k_final, cot_storage=cot_storage,
                                  step_callback=step_callback)

    llm = get_llm(
        provider_key=provider, model=model,
        config={**state.config, "llm": {**state.config.get("llm", {}), "temperature": temperature}},
    )
    agent = create_react_agent(llm, [search_tool], prompt=state.BASE_SYSTEM_PROMPT)
    enriched_prompt, history_tuples = state.mm.build_agent_input(session, state.BASE_SYSTEM_PROMPT)
    lc_history = _build_lc_history(history_tuples, masked_message)

    if step_callback:
        step_callback("answer")

    start_generation = time.time()
    result = agent.invoke({"messages": lc_history})
    generation_time = time.time() - start_generation
    response_text = format_response(result["messages"][-1].content)
    log_to_db_sync(
        level="INFO", source="RAG_PROFILING",
        message="LLM response generated",
        metadata={"duration_seconds": generation_time, "provider": provider, "model": model},
        user_id=log_user_id,
    )
    return response_text, cot_storage


@router.post("/chat")
async def chat(req: ChatRequest):
    request_sm = state.get_sm(req.user_id)

    if req.session_id:
        session = request_sm.load(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = request_sm.new_session(provider=req.provider, model=req.model or "")

    if not req.user_id or not state.is_valid_uuid(req.user_id):
        guest_msgs = [m for m in session.get("messages", []) if m["role"] == "user"]
        if len(guest_msgs) >= 5:
            raise HTTPException(
                status_code=429,
                detail="Limite de 5 messages atteinte. Connectez-vous pour continuer.",
            )

    model = req.model or state.config.get("llm", {}).get("default_model", "")
    masked_message = state.pii.mask_text(req.message)
    session.setdefault("messages", []).append({"role": "user", "content": masked_message})
    request_sm.save(session)

    async def event_stream():
        _chat_start = time.time()
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session['session_id']})}\n\n"

        step_q: _queue.SimpleQueue = _queue.SimpleQueue()

        def _step_cb(name: str):
            step_q.put(name)

        try:
            agent_task = asyncio.create_task(asyncio.to_thread(
                _run_agent,
                session=session, masked_message=masked_message, provider=req.provider,
                model=model, temperature=req.temperature, k_final=req.k_final,
                step_callback=_step_cb,
            ))

            while not agent_task.done():
                try:
                    step = step_q.get_nowait()
                    yield f"data: {json.dumps({'type': 'step', 'step': step})}\n\n"
                except _queue.Empty:
                    pass
                await asyncio.sleep(0.04)

            while not step_q.empty():
                yield f"data: {json.dumps({'type': 'step', 'step': step_q.get_nowait()})}\n\n"

            response, cot_storage = agent_task.result()

        except Exception as e:
            logger.error(f"Erreur critique dans le RAG: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        state.push_event(
            "chat",
            question=masked_message[:120],
            provider=req.provider,
            model=model,
            latency_ms=round((time.time() - _chat_start) * 1000),
            source="discord" if req.user_id == "discord" else "web",
        )

        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)

        if cot_storage:
            yield f"data: {json.dumps({'type': 'cot', 'results': cot_storage})}\n\n"

        session["messages"].append({"role": "assistant", "content": response, "_cot": cot_storage})
        session["provider"] = req.provider
        session["model"] = model
        request_sm.save(session)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

        if state.mm.needs_summarization(session["messages"], session.get("summary", "")):
            async def _compress_session():
                try:
                    session_updated = await asyncio.to_thread(
                        state.mm.compress, session, get_llm(
                            provider_key=req.provider, model=model,
                            config={**state.config,
                                    "llm": {**state.config.get("llm", {}), "temperature": req.temperature}},
                        )
                    )
                    session.update(session_updated)
                    request_sm.save(session)
                except Exception as _e:
                    logger.error(f"Erreur compression mémoire : {_e}", exc_info=True)
            asyncio.create_task(_compress_session())

        async def _run_judge_task():
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(
                        _run_judge_sync,
                        query=masked_message,
                        response=response,
                        cot_storage=cot_storage,
                        user_id=req.user_id,
                        session_id=session["session_id"],
                        config=state.config,
                    ),
                    timeout=20.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Judge task timed out after 20s.")
            except Exception as _judge_exc:
                logger.error(f"Erreur judge en arrière-plan : {_judge_exc}", exc_info=True)

        asyncio.create_task(_run_judge_task())

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session["session_id"],
        },
    )


@router.post("/chat/sync")
async def chat_sync(req: ChatRequest):
    """Endpoint synchrone pour clients sans support SSE (ex: Roblox)."""
    import uuid as _uuid
    model = req.model or state.config.get("llm", {}).get("default_model", "")
    masked_message = state.pii.mask_text(req.message)
    session = {
        "session_id": str(_uuid.uuid4()),
        "user_id": None,
        "title": "Roblox",
        "provider": req.provider,
        "model": model,
        "messages": [{"role": "user", "content": masked_message}],
        "summary": "",
        "created_at": "",
        "updated_at": "",
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


@router.get("/archives")
def list_archives():
    return {"sources": state.vm.list_sources()}