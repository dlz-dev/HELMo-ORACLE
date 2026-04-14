from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import state

router = APIRouter(prefix="/sessions")


class RenameRequest(BaseModel):
    title: str


@router.get("")
def list_sessions(user_id: Optional[str] = None):
    return {"sessions": state.get_sm(user_id).list_sessions()}


@router.post("")
def create_session(provider: str = "", model: str = "", user_id: Optional[str] = None):
    request_sm = state.get_sm(user_id)
    session = request_sm.new_session(provider=provider, model=model)
    request_sm.save(session)
    return session


@router.get("/{session_id}")
def get_session(session_id: str, user_id: Optional[str] = None):
    session = state.get_sm(user_id).load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
def delete_session(session_id: str, user_id: Optional[str] = None):
    state.get_sm(user_id).delete(session_id)
    return {"deleted": session_id}


@router.patch("/{session_id}/rename")
def rename_session(session_id: str, body: RenameRequest, user_id: Optional[str] = None):
    request_sm = state.get_sm(user_id)
    session = request_sm.load(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["title"] = body.title
    request_sm.save(session)
    return {"session_id": session_id, "title": body.title}