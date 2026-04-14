from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import state
from core.utils.logger import logger, log_to_db_sync

router = APIRouter()


class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    rating: int
    comment: Optional[str] = None


@router.post("/feedback", status_code=201)
def submit_feedback(req: FeedbackRequest):
    """Enregistre un feedback utilisateur (note 1-5 + commentaire optionnel)."""
    if not (1 <= req.rating <= 5):
        raise HTTPException(status_code=422, detail="La note doit être entre 1 et 5.")
    if state.supabase is None:
        raise HTTPException(status_code=503, detail="Client Supabase indisponible.")
    user_id = req.user_id if req.user_id and state.is_valid_uuid(req.user_id) else None
    try:
        state.supabase.table("feedback").insert({
            "session_id": req.session_id,
            "user_id": user_id,
            "rating": req.rating,
            "comment": req.comment,
        }).execute()
        logger.info(f"Feedback reçu — session={req.session_id} note={req.rating}")
        log_to_db_sync(
            level="INFO",
            source="FEEDBACK",
            message=f"Note {req.rating}/5",
            metadata={"session_id": req.session_id, "rating": req.rating, "comment": req.comment},
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Erreur insertion feedback: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement du feedback.")
    return {"status": "ok"}