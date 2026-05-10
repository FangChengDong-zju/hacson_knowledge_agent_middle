from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .. import storage
from ..models import RAGAnswer
from ..services.rag import answer_question, build_chunks


router = APIRouter(prefix="/api/rag", tags=["rag"])


class RAGQuery(BaseModel):
    question: str


@router.post("/index")
def build_index() -> dict[str, int]:
    chunks = build_chunks(storage.load_textbooks())
    return {"chunk_count": len(chunks), "textbook_count": len(storage.load_textbooks())}


@router.get("/status")
def status() -> dict[str, int]:
    textbooks = storage.load_textbooks()
    chunks = build_chunks(textbooks)
    return {"textbook_count": len(textbooks), "chunk_count": len(chunks)}


@router.post("/query")
def query(payload: RAGQuery) -> RAGAnswer:
    return answer_question(storage.load_textbooks(), payload.question)

