import time

from fastapi import APIRouter, Depends, Header, HTTPException

import state
from core.utils.logger import logger

router = APIRouter()


def _require_api_key(x_api_key: str = Header(...)):
    if not state.ADMIN_API_KEY or x_api_key != state.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


@router.get("/metrics", dependencies=[Depends(_require_api_key)])
def get_metrics():
    """Retourne les stats réelles et le flux Redis pour le dashboard admin."""
    db_docs = 0
    db_available = False
    if state.vm.is_db_available():
        db_available = True
        try:
            with state.vm.conn.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT metadata->>'source') FROM documents")
                db_docs = cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Metrics SQL Error (docs): {e}")

    user_count = 0
    conn = state.get_log_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM profiles")
                user_count = cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Metrics SQL Error (users): {e}")
            user_count = 1
    else:
        user_count = 1

    if state.redis is None:
        return {
            "available": False,
            "events": [],
            "stats": {
                "total_chunks_ingested": db_docs,
                "total_users": user_count,
                "db_ok": db_available,
            },
        }

    try:
        raw = state.redis.xrevrange(state.REDIS_STREAM, count=100)
    except Exception as e:
        logger.error(f"Metrics Redis Error: {e}")
        return {
            "available": False,
            "error": str(e),
            "events": [],
            "stats": {
                "total_chunks_ingested": db_docs,
                "total_users": user_count,
                "db_ok": db_available,
            },
        }

    events = []
    for entry_id, fields in raw:
        ts_ms = int(entry_id.split("-")[0])
        events.append({
            "id": entry_id,
            "ts": ts_ms / 1000,
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
        })

    now = time.time()
    chat_events = [e for e in events if e["type"] == "chat"]
    last_minute = [e for e in chat_events if now - e["ts"] < 60]
    last_hour = [e for e in chat_events if now - e["ts"] < 3600]
    latencies = [e["latency_ms"] for e in chat_events if e["latency_ms"] > 0]

    stats = {
        "total_queries": len(chat_events),
        "queries_last_minute": len(last_minute),
        "queries_last_hour": len(last_hour),
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "db_ok": db_available,
        "total_chunks_ingested": db_docs,
        "total_users": user_count,
    }

    return {"available": True, "events": events, "stats": stats}