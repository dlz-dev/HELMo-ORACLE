"""
Persistent session storage module with automatic environment detection.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.utils.utils import STORAGE_DIR

logger = logging.getLogger("oracle")

# Constants
LOCAL_USER_ID = "local_dev"


def _is_cloud() -> bool:
    """Detects if running in production (env var ENV=production)."""
    return os.environ.get("ENV", "local") == "production"


def get_current_user_id() -> Optional[str]:
    """
    Retrieves the current user's identifier. Returns a valid UUID or None.
    """
    user_id_str = os.environ.get("USER_ID")
    if not user_id_str:
        return None
    try:
        # Ensure the ID is a valid UUID, otherwise treat as anonymous
        return str(uuid.UUID(user_id_str))
    except ValueError:
        logger.warning(f"USER_ID '{user_id_str}' is not a valid UUID. Treating as anonymous.")
        return None


def _now_iso() -> str:
    """Returns the current UTC time as an ISO formatted string."""
    return datetime.now(timezone.utc).isoformat()


def _make_title(first_user_message: str) -> str:
    """Truncates the first user message to create a readable session title."""
    title = first_user_message.strip().replace("\n", " ")
    return title[:60] + "…" if len(title) > 60 else title


class _LocalBackend:
    """Stores sessions as JSON files locally, scoped by user_id."""

    def __init__(self, user_id: str) -> None:
        self._user_dir = os.path.join(STORAGE_DIR, user_id)
        os.makedirs(self._user_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        return os.path.join(self._user_dir, f"{session_id}.json")

    def save(self, session: Dict[str, Any]) -> None:
        session["updated_at"] = _now_iso()
        with open(self._path(session["session_id"]), "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(session_id)
        if not os.path.exists(path): return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        for fname in os.listdir(self._user_dir):
            if not fname.endswith(".json"): continue
            try:
                with open(os.path.join(self._user_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id"), "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", ""), "provider": data.get("provider", ""),
                        "model": data.get("model", ""),
                    })
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)

    def delete(self, session_id: str) -> None:
        path = self._path(session_id)
        if os.path.exists(path): os.remove(path)


class _SupabaseBackend:
    """Stores sessions in a Supabase database, scoped by user_id."""

    def __init__(self, user_id: str) -> None:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        self._client = create_client(url, key)
        self._user_id = user_id

    def save(self, session: Dict[str, Any]) -> None:
        session["updated_at"] = _now_iso()
        payload = {
            "session_id": session["session_id"], "user_id": self._user_id,
            "title": session.get("title", ""), "provider": session.get("provider", ""),
            "model": session.get("model", ""), "messages": session.get("messages", []),
            "summary": session.get("summary", ""), "updated_at": session["updated_at"],
        }
        self._client.table("chat_sessions").upsert(payload).execute()

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        res = self._client.table("chat_sessions").select("*").eq("session_id", session_id).eq("user_id",
                                                                                              self._user_id).single().execute()
        return res.data if res.data else None

    def list_sessions(self) -> List[Dict[str, Any]]:
        res = self._client.table("chat_sessions").select("session_id, title, updated_at, provider, model").eq("user_id",
                                                                                                              self._user_id).order(
            "updated_at", desc=True).limit(50).execute()
        return res.data or []

    def delete(self, session_id: str) -> None:
        self._client.table("chat_sessions").delete().eq("session_id", session_id).eq("user_id", self._user_id).execute()


class SessionManager:
    """Unified session manager that automatically routes to the correct backend."""

    def __init__(self, user_id: Optional[str] = None) -> None:
        # Per-request: explicit user_id provided (from frontend auth)
        if user_id:
            effective_user = user_id
        elif _is_cloud():
            effective_user = get_current_user_id() or "anonymous_local"
        else:
            effective_user = LOCAL_USER_ID

        self.user_id = effective_user

        if _is_cloud():
            try:
                self._backend = _SupabaseBackend(effective_user)
                self.backend_name = "supabase"
                logger.info(f"SessionManager using Supabase backend for user {effective_user}.")
            except Exception as e:
                logger.error(f"Supabase backend failed for user {effective_user}, falling back to local. Error: {e}")
                self._backend = _LocalBackend(effective_user)
                self.backend_name = "local_fallback"
        else:
            self._backend = _LocalBackend(effective_user)
            self.backend_name = "local"
            logger.info(f"SessionManager using local backend for user '{effective_user}'.")

    def new_session(self, provider: str = "", model: str = "") -> Dict[str, Any]:
        return {
            "session_id": str(uuid.uuid4()), "user_id": self.user_id,
            "title": "New conversation", "provider": provider, "model": model,
            "messages": [], "summary": "", "created_at": _now_iso(), "updated_at": _now_iso(),
        }

    def save(self, session: Dict[str, Any]) -> None:
        if session.get("title") == "New conversation":
            user_msgs = [m for m in session.get("messages", []) if m["role"] == "user"]
            if user_msgs:
                session["title"] = _make_title(user_msgs[0]["content"])
        self._backend.save(session)

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._backend.load(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return self._backend.list_sessions()

    def delete(self, session_id: str) -> None:
        self._backend.delete(session_id)
