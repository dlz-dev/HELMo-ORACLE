import os
import time

from fastapi import APIRouter
from langchain_core.messages import HumanMessage as _HM

import state

router = APIRouter()


@router.get("/health")
def health():
    checks = {}

    if state.vm.is_db_available():
        try:
            with state.vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT metadata->>'source') FROM documents")
                count = cur.fetchone()[0]
            checks["database"] = {"status": "ok", "documents": count}
        except Exception as e:
            checks["database"] = {"status": "error", "error": str(e)}
    else:
        checks["database"] = {"status": "error", "error": "Connexion indisponible"}

    checks["embeddings"] = {"status": "ok", "model": "nomic-embed-text"}

    return {"status": "ok", "checks": checks}


@router.get("/health/full")
def health_full():
    """
    Vérifie l'état de tous les composants du système.
    Teste : base de données, embeddings, et chaque clé API configurée.
    """
    results = {}

    # ── Base de données ───────────────────────────────────────────
    if state.vm.is_db_available():
        try:
            start = time.time()
            with state.vm.conn.cursor() as cur:
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
        state.embeddings.embed_query("test")
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
        "gemini": ("GOOGLE_API_KEY", "langchain_google_genai", "ChatGoogleGenerativeAI",
                   {"model": "gemini-2.0-flash"}),
    }

    for provider_name, (env_var, module, cls_name, kwargs) in providers_to_check.items():
        api_key = os.environ.get(env_var, "")
        if not api_key:
            results[provider_name] = {"status": "not_configured"}
            continue
        try:
            start = time.time()
            mod = __import__(module, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            llm = cls(api_key=api_key, temperature=0, request_timeout=5.0, **kwargs)
            llm.invoke([_HM(content="Reply with one word: ok")])
            results[provider_name] = {
                "status": "ok",
                "latency_ms": round((time.time() - start) * 1000),
            }
        except Exception as e:
            results[provider_name] = {"status": "error", "error": str(e)[:120]}

    has_error = any(v.get("status") == "error" for v in results.values())
    return {"status": "degraded" if has_error else "ok", "checks": results}