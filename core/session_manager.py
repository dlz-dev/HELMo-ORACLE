"""
core/session_manager.py

Persistent session storage with automatic environment detection:
  - Local / dev  → JSON files in storage/sessions/<user_id>/
  - Streamlit Cloud → Supabase (table: chat_sessions), filtered by user_id

Multi-user isolation: every operation is scoped to a user_id.
  - Cloud  : user_id = email from st.experimental_user (Streamlit auth)
  - Local  : user_id = "local_dev" (fixed, single-user dev environment)

A "session" contains:
  - session_id    : unique identifier (UUID)
  - user_id       : owner of the session
  - title         : auto-generated from first user message
  - created_at    : ISO timestamp
  - updated_at    : ISO timestamp
  - messages      : full list of {role, content} dicts
  - summary       : condensed memory of older messages (may be empty string)
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import streamlit as st

# ─────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage", "sessions")


def _is_cloud() -> bool:
    """
    Returns True when running on Streamlit Cloud.
    Detection: config.yaml absent → we're in cloud mode using st.secrets.
    """
    config_path = os.path.join(BASE_DIR, "config", "config.yaml")
    return not os.path.exists(config_path)


LOCAL_USER_ID = "local_dev"


def get_current_user_id() -> str:
    """
    Returns the current user's identifier.

    - Streamlit Cloud (auth enabled) : email from st.experimental_user
    - Local dev                       : fixed constant "local_dev"
    """
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
    return datetime.now(timezone.utc).isoformat()


def _make_title(first_user_message: str) -> str:
    """Truncates the first message to create a readable session title."""
    title = first_user_message.strip().replace("\n", " ")
    return title[:60] + "…" if len(title) > 60 else title


# ─────────────────────────────────────────────────────────────────
# Local JSON backend
# ─────────────────────────────────────────────────────────────────

class _LocalBackend:
    """
    Stores sessions as JSON files in storage/sessions/<user_id>/<session_id>.json
    Each user gets their own subdirectory — full isolation even in local/dev.
    """

    def __init__(self, user_id: str):
        self._user_dir = os.path.join(STORAGE_DIR, user_id)
        os.makedirs(self._user_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        return os.path.join(self._user_dir, f"{session_id}.json")

    def save(self, session: dict) -> None:
        session["updated_at"] = _now_iso()
        with open(self._path(session["session_id"]), "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

    def load(self, session_id: str) -> Optional[dict]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self) -> list[dict]:
        """Returns sessions for this user only, sorted by updated_at descending."""
        sessions = []
        for fname in os.listdir(self._user_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self._user_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        sessions.append({
                            "session_id": data["session_id"],
                            "title":      data.get("title", "Untitled"),
                            "updated_at": data.get("updated_at", ""),
                            "provider":   data.get("provider", ""),
                            "model":      data.get("model", ""),
                        })
                except (json.JSONDecodeError, KeyError):
                    continue
        return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)

    def delete(self, session_id: str) -> None:
        path = self._path(session_id)
        if os.path.exists(path):
            os.remove(path)


# ─────────────────────────────────────────────────────────────────
# Supabase backend
# ─────────────────────────────────────────────────────────────────

class _SupabaseBackend:
    """
    Stores sessions in Supabase, scoped by user_id for full multi-user isolation.

    Required SQL (run once in Supabase SQL editor):
    ─────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id  TEXT PRIMARY KEY,
        user_id     TEXT NOT NULL,
        title       TEXT,
        provider    TEXT,
        model       TEXT,
        messages    JSONB,
        summary     TEXT DEFAULT '',
        created_at  TIMESTAMPTZ DEFAULT now(),
        updated_at  TIMESTAMPTZ DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id
        ON chat_sessions(user_id);
    ─────────────────────────────────────────────────
    """

    def __init__(self, user_id: str):
        from supabase import create_client
        url = st.secrets["database"]["supabase_url"]
        key = st.secrets["database"]["supabase_anon_key"]
        self._client = create_client(url, key)
        self._user_id = user_id

    def save(self, session: dict) -> None:
        session["updated_at"] = _now_iso()
        payload = {
            "session_id": session["session_id"],
            "user_id":    self._user_id,           # ← ownership
            "title":      session.get("title", ""),
            "provider":   session.get("provider", ""),
            "model":      session.get("model", ""),
            "messages":   session.get("messages", []),
            "summary":    session.get("summary", ""),
            "updated_at": session["updated_at"],
        }
        self._client.table("chat_sessions").upsert(payload).execute()

    def load(self, session_id: str) -> Optional[dict]:
        res = (
            self._client.table("chat_sessions")
            .select("*")
            .eq("session_id", session_id)
            .eq("user_id", self._user_id)          # ← user cannot load another user's session
            .single()
            .execute()
        )
        return res.data if res.data else None

    def list_sessions(self) -> list[dict]:
        res = (
            self._client.table("chat_sessions")
            .select("session_id, title, updated_at, provider, model")
            .eq("user_id", self._user_id)          # ← user only sees their own sessions
            .order("updated_at", desc=True)
            .limit(50)
            .execute()
        )
        return res.data or []

    def delete(self, session_id: str) -> None:
        (
            self._client.table("chat_sessions")
            .delete()
            .eq("session_id", session_id)
            .eq("user_id", self._user_id)          # ← user cannot delete another user's session
            .execute()
        )


# ─────────────────────────────────────────────────────────────────
# SessionManager — public interface
# ─────────────────────────────────────────────────────────────────

class SessionManager:
    """
    Unified session manager. Automatically uses the right backend.

    Usage in app.py:
        sm = SessionManager()
        session = sm.new_session(provider="groq", model="llama-3.3-70b")
        sm.save(session)
        sessions = sm.list_sessions()
        session = sm.load(session_id)
        sm.delete(session_id)
    """

    def __init__(self):
        self.user_id = get_current_user_id()

        if _is_cloud():
            try:
                self._backend = _SupabaseBackend(self.user_id)
                self.backend_name = "supabase"
            except Exception:
                # Fallback to local if Supabase isn't configured yet
                self._backend = _LocalBackend(self.user_id)
                self.backend_name = "local"
        else:
            self._backend = _LocalBackend(self.user_id)
            self.backend_name = "local"

    def new_session(self, provider: str = "", model: str = "") -> dict:
        """Creates a fresh session dict (not yet saved)."""
        return {
            "session_id": str(uuid.uuid4()),
            "user_id":    self.user_id,
            "title":      "New conversation",
            "provider":   provider,
            "model":      model,
            "messages":   [],
            "summary":    "",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }

    def save(self, session: dict) -> None:
        """Persists the session. Auto-generates title from first user message."""
        # Auto-title on first user message
        if session.get("title") == "New conversation":
            user_msgs = [m for m in session.get("messages", []) if m["role"] == "user"]
            if user_msgs:
                session["title"] = _make_title(user_msgs[0]["content"])
        self._backend.save(session)

    def load(self, session_id: str) -> Optional[dict]:
        """Loads a session by ID. Returns None if not found."""
        return self._backend.load(session_id)

    def list_sessions(self) -> list[dict]:
        """Returns metadata (no messages) for all sessions, newest first."""
        return self._backend.list_sessions()

    def delete(self, session_id: str) -> None:
        """Permanently deletes a session."""
        self._backend.delete(session_id)