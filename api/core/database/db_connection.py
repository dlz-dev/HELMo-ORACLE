"""
Gestion des connexions bases de données :
- Supabase (psycopg) pour les logs et profils
- Supabase Python client pour le feedback
"""

import os

import psycopg
from supabase import create_client as _create_supabase_client

from core.utils.logger import logger, set_shared_conn

# ── Connexion psycopg (logs/profils) ──────────────────────────────────────────

_LOG_DB_URL = os.getenv("LOG_DATABASE_URL", "")
_log_conn = None

if _LOG_DB_URL:
    try:
        _log_conn = psycopg.connect(_LOG_DB_URL, autocommit=False, connect_timeout=10)
        logger.info("Connexion Supabase (logs) initialisée.")
    except Exception as e:
        logger.error(f"Impossible de se connecter à Supabase pour les logs : {e}")

set_shared_conn(_log_conn)


def ensure_log_conn() -> bool:
    """Vérifie et reconnecte si nécessaire la connexion Supabase. Retourne True si disponible."""
    global _log_conn
    if not _LOG_DB_URL:
        return False

    if _log_conn is not None and not _log_conn.closed:
        try:
            with _log_conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            pass

    try:
        if _log_conn is not None and not _log_conn.closed:
            try:
                _log_conn.close()
            except Exception:
                pass
        _log_conn = psycopg.connect(_LOG_DB_URL, autocommit=False, connect_timeout=10)
        set_shared_conn(_log_conn)
        logger.info("Connexion Supabase (logs) reconnectée.")
        return True
    except Exception as e:
        logger.error(f"ensure_log_conn: Reconnexion échouée : {e}")
        _log_conn = None
        set_shared_conn(None)
        return False


def get_log_conn():
    return _log_conn


# ── Client Supabase Python (feedback) ─────────────────────────────────────────

supabase_client = None
_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

if _SUPABASE_URL and _SUPABASE_KEY:
    try:
        supabase_client = _create_supabase_client(_SUPABASE_URL, _SUPABASE_KEY)
        logger.info("Client Supabase initialisé.")
    except Exception as e:
        logger.error(f"Impossible d'initialiser le client Supabase : {e}")
