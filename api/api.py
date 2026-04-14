"""
FastAPI backend for HELMo Oracle.

Exposes the RAG pipeline as a REST API so a separate frontend
(e.g. deployed on Vercel) can call it over HTTP.
"""

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import state
from core.utils.logger import logger
from routers import chat, feedback, health, ingest, logs, metrics, sessions


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield


app = FastAPI(title="HELMo Oracle API", version="1.0.0", lifespan=_lifespan)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
if not ALLOWED_ORIGINS:
    logger.warning("ALLOWED_ORIGINS est vide — toutes les origines CORS seront bloquées. Vérifiez votre .env.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.mount("/mcp", state.mcp_asgi)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(ingest.router)
app.include_router(logs.router)
app.include_router(metrics.router)
app.include_router(feedback.router)

# Expose providers endpoint (no dedicated router needed)
from fastapi import HTTPException
from providers import get_available_models


@app.get("/providers/{provider}/models")
def list_models(provider: str):
    try:
        return {"models": get_available_models(provider, state.config)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)