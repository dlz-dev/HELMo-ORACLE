from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg import sql

import state
from core.utils.logger import logger, _LOG_FILE

router = APIRouter(prefix="/logs")


def _require_api_key(x_api_key: str = Header(...)):
    if not state.ADMIN_API_KEY or x_api_key != state.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


@router.get("", dependencies=[Depends(_require_api_key)])
def get_logs(lines: int = 100, offset: int = 0, level: Optional[str] = None,
             source: Optional[str] = None):
    """Fetches logs from the database with optional filters and pagination."""
    conn = state.get_log_conn()
    if not conn:
        logger.error("[GET_LOGS] Connexion Supabase (logs) indisponible.")
        raise HTTPException(status_code=503, detail="Connexion logs indisponible")

    try:
        with conn.cursor() as cur:
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
                    "profiles": {"first_name": row[6], "last_name": row[7]} if row[6] else None,
                }
                for row in rows
            ]
            return {"logs": logs_list}
    except Exception as e:
        logger.error("[GET_LOGS] Failed to fetch logs from DB.", exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Erreur interne du serveur lors de la récupération des logs: {e}")


@router.delete("", dependencies=[Depends(_require_api_key)])
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