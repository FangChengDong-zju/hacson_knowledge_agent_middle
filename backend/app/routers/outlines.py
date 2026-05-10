from __future__ import annotations

from fastapi import APIRouter

from .. import storage
from ..models import OutlineBuildResponse, TextbookOutline
from ..services.outline_builder import build_outlines_from_textbooks


router = APIRouter(prefix="/api/outlines", tags=["outlines"])


@router.post("/build")
def build_outlines() -> OutlineBuildResponse:
    outlines = build_outlines_from_textbooks(storage.load_textbooks())
    storage.save_outlines(outlines)
    item_count = sum(outline.item_count for outline in outlines)
    return OutlineBuildResponse(outlines=outlines, textbook_count=len(outlines), item_count=item_count)


@router.get("")
def get_outlines() -> list[TextbookOutline]:
    return storage.load_outlines()
