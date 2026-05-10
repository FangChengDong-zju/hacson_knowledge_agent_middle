from __future__ import annotations

from fastapi import APIRouter

from .. import storage
from ..services.report_writer import generate_integration_report, report_path


router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("/generate")
def generate_report() -> dict[str, str]:
    report = generate_integration_report(
        storage.load_textbooks(),
        storage.load_graph(),
        storage.load_decisions(),
        storage.load_summary(),
    )
    return {"path": str(report_path()), "content": report}


@router.get("")
def get_report() -> dict[str, str]:
    path = report_path()
    return {"path": str(path), "content": path.read_text(encoding="utf-8") if path.exists() else ""}

