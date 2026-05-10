from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import storage
from ..models import IntegrationDecision, IntegrationSummary
from ..services.alignment import align_graph
from ..services.compression import summarize_integration


router = APIRouter(prefix="/api/integration", tags=["integration"])


@router.post("/run")
def run_integration() -> dict[str, object]:
    textbooks = storage.load_textbooks()
    graph = storage.load_graph()
    decisions = align_graph(graph)
    summary = summarize_integration(textbooks, decisions)
    storage.save_decisions(decisions)
    storage.save_summary(summary)
    return {"decisions": decisions, "summary": summary}


@router.get("/decisions")
def list_decisions() -> list[IntegrationDecision]:
    return storage.load_decisions()


@router.get("/summary")
def get_summary() -> IntegrationSummary:
    return storage.load_summary()


@router.post("/decisions/{decision_id}/override")
def override_decision(decision_id: str, action: str) -> IntegrationDecision:
    decisions = storage.load_decisions()
    for decision in decisions:
        if decision.decision_id == decision_id:
            if action not in {"merge", "keep", "remove"}:
                raise HTTPException(status_code=400, detail="Invalid action")
            decision.action = action  # type: ignore[assignment]
            decision.teacher_override = True
            decision.reason = f"教师手动调整为 {action}"
            storage.save_decisions(decisions)
            return decision
    raise HTTPException(status_code=404, detail="Decision not found")

