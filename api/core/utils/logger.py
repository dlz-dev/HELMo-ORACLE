"""
Centralized logging configuration and database logging for HELMo Oracle.
"""

import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "oracle.log"

# Configure the main 'oracle' logger
log_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler for rotating file logs
rotating_handler = RotatingFileHandler(
    _LOG_FILE,
    maxBytes=5_000_000,
    backupCount=3,
    encoding="utf-8"
)
rotating_handler.setFormatter(log_formatter)

# Handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

# Get the root logger for 'oracle' and add handlers
logger = logging.getLogger("oracle")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    logger.addHandler(rotating_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False  # Prevent messages from being passed to the root logger

# Module-level state for database connection
_shared_db_conn: Optional[psycopg.Connection] = None


def set_shared_conn(conn: Optional[psycopg.Connection]) -> None:
    """Sets the shared database connection for logging."""
    global _shared_db_conn
    _shared_db_conn = conn

    if conn:
        logger.info("[Logger] Connexion DB partagée initialisée pour le logger.")
    else:
        logger.warning("[Logger] Connexion DB partagée NON disponible.")


def _log_to_db_sync(
        level: str,
        source: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
) -> None:
    """Synchronously inserts a log entry into the database."""
    if _shared_db_conn is None or _shared_db_conn.closed:
        logger.error("[DB_LOG_SYNC_FAIL] La connexion partagée n'est pas disponible ou est fermée.")
        return

    try:
        # Cursor is isolated per thread context
        with _shared_db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO logs (level, source, message, metadata, user_id)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (level, source, message, json.dumps(metadata) if metadata else None, user_id)
            )
        _shared_db_conn.commit()
        logger.info(f"[DB_LOG_SYNC_SUCCESS] Log inséré pour la source: {source}")
    except Exception as e:
        logger.error(
            f"[DB_LOG_SYNC_FAIL] Erreur lors de l'insertion du log pour la source {source}: {e}",
            exc_info=True
        )
        _shared_db_conn.rollback()


# Alias for synchronous operations
log_to_db_sync = _log_to_db_sync


def get_logger(name: str) -> logging.Logger:
    """Returns a namespaced child logger."""
    return logging.getLogger(f"oracle.{name}")


async def log_to_db(
        level: str,
        source: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
) -> None:
    """Offloads the synchronous DB logging to a separate thread to prevent blocking the async loop."""
    try:
        await asyncio.to_thread(_log_to_db_sync, level, source, message, metadata, user_id)
    except Exception as e:
        logger.error(f"[LOG_TO_DB_ASYNC_FAIL] Erreur dans le thread de logging: {e}", exc_info=True)
