"""
Persistent session storage module with automatic environment detection.

Handles multi-user isolation and seamlessly switches between local JSON
storage (for development) and Supabase (for Streamlit Cloud).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st
from core.utils.utils import BASE_DIR, STORAGE_DIR

# Constants
LOCAL_USER_ID = "local_dev"


def _is_cloud() -> bool:
    """Detects if the application is running on Streamlit Cloud."""
    config_path = os.path.join(BASE_DIR, "config", "config.yaml")
    return not os.path.exists(config_path)


def get_current_user_id() -> str:
    """Retrieves the current user's identifier based on the environment."""
    if _is_cloud():
        try:
            user = st.experimental_user
            if user and user.email:
                return user.email.lower().strip()
        except Exception:
            pass
        return "anonymous"
    return LOCAL_USER_ID


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
        """Persists a session dictionary to a local JSON file."""
        session["updated_at"] = _now_iso()
        with open(self._path(session["session_id"]), "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Loads a session dictionary from local storage."""
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Retrieves all sessions for the current user, sorted by updated_at."""
        sessions = []
        for fname in os.listdir(self._user_dir):
            if not fname.endswith(".json"):
                continue
            
            try:
                with open(os.path.join(self._user_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id"),
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", ""),
                        "provider": data.get("provider", ""),
                        "model": data.get("model", ""),
                    })
            except (json.JSONDecodeError, KeyError):
                continue
                
        return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)

    def delete(self, session_id: str) -> None:
        """Deletes a local session file."""
        path = self._path(session_id)
        if os.path.exists(path):
            os.remove(path)


class _SupabaseBackend:
    """Stores sessions in a Supabase database, scoped by user_id."""

    def __init__(self, user_id: str) -> None:
        from supabase import create_client
        url = st.secrets["database"]["supabase_url"]
        key = st.secrets["database"]["supabase_anon_key"]
        self._client = create_client(url, key)
        self._user_id = user_id

    def save(self, session: Dict[str, Any]) -> None:
        """Upserts a session record in the Supabase database."""
        session["updated_at"] = _now_iso()
        payload = {
            "session_id": session["session_id"],
            "user_id": self._user_id,
            "title": session.get("title", ""),
            "provider": session.get("provider", ""),
            "model": session.get("model", ""),
            "messages": session.get("messages", []),
            "summary": session.get("summary", ""),
            "updated_at": session["updated_at"],
        }
        self._client.table("chat_sessions").upsert(payload).execute()

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Loads a session record from the Supabase database."""
        res = (
            self._client.table("chat_sessions")
            .select("*")
            .eq("session_id", session_id)
            .eq("user_id", self._user_id)
            .single()
            .execute()
        )
        return res.data if res.data else None

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Retrieves all session metadata for the user from Supabase."""
        res = (
            self._client.table("chat_sessions")
            .select("session_id, title, updated_at, provider, model")
            .eq("user_id", self._user_id)
            .order("updated_at", desc=True)
            .limit(50)
            .execute()
        )
        return res.data or []

    def delete(self, session_id: str) -> None:
        """Deletes a session record from the Supabase database."""
        (
            self._client.table("chat_sessions")
            .delete()
            .eq("session_id", session_id)
            .eq("user_id", self._user_id)
            .execute()
        )


class SessionManager:
    """Unified session manager that automatically routes to the correct backend."""

    def __init__(self) -> None:
        self.user_id = get_current_user_id()

        if _is_cloud():
            try:
                self._backend = _SupabaseBackend(self.user_id)
                self.backend_name = "supabase"
            except Exception:
                self._backend = _LocalBackend(self.user_id)
                self.backend_name = "local"
        else:
            self._backend = _LocalBackend(self.user_id)
            self.backend_name = "local"

    def new_session(self, provider: str = "", model: str = "") -> Dict[str, Any]:
        """Creates and returns a fresh session dictionary."""
        return {
            "session_id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "title": "New conversation",
            "provider": provider,
            "model": model,
            "messages": [],
            "summary": "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }

    def save(self, session: Dict[str, Any]) -> None:
        """Persists the session, auto-generating a title if it is new."""
        if session.get("title") == "New conversation":
            user_msgs = [m for m in session.get("messages", []) if m["role"] == "user"]
            if user_msgs:
                session["title"] = _make_title(user_msgs[0]["content"])
        self._backend.save(session)

    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Loads a session by its ID."""
        return self._backend.load(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Returns metadata for all sessions, sorted by newest first."""
        return self._backend.list_sessions()

    def delete(self, session_id: str) -> None:
        """Permanently deletes a session."""
        self._backend.delete(session_id)