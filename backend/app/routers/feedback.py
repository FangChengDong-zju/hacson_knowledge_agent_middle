from __future__ import annotations

from fastapi import APIRouter

from .. import storage
from ..models import FeedbackRequest, FeedbackResponse
from ..services.feedback import apply_teacher_feedback


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("/chat")
def chat(payload: FeedbackRequest) -> FeedbackResponse:
    decisions = storage.load_decisions()
    response = apply_teacher_feedback(payload.message, decisions, payload.decision_id)
    if response.updated_decision:
        storage.save_decisions(decisions)
    return response

