from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import storage
from ..config import settings
from ..models import Textbook
from ..services.parser import cached_index_available, list_local_textbook_files, parse_cached_textbook_index, parse_textbook_file


router = APIRouter(prefix="/api/textbooks", tags=["textbooks"])


@router.get("/local")
def local_textbooks() -> list[dict[str, object]]:
    files = list_local_textbook_files()
    return [{**item, "cached_index_available": cached_index_available()} for item in files]


@router.get("")
def list_textbooks() -> list[Textbook]:
    return storage.load_textbooks()


@router.post("/parse-local")
def parse_local_textbooks(limit: int = 7) -> list[Textbook]:
    if cached_index_available():
        parsed = parse_cached_textbook_index(limit=limit)
        storage.save_textbooks(parsed)
        return parsed

    parsed: list[Textbook] = []
    for index, item in enumerate(list_local_textbook_files()[:limit], start=1):
        path = Path(str(item["path"]))
        try:
            parsed.append(parse_textbook_file(path, textbook_id=f"book_{index:03d}"))
        except Exception as exc:  # noqa: BLE001 - API should return per-file failure.
            parsed.append(
                Textbook(
                    textbook_id=f"book_{index:03d}",
                    filename=path.name,
                    title=path.stem,
                    format=path.suffix.lower().lstrip("."),
                    status="failed",
                    source_path=str(path),
                    error=str(exc),
                )
            )
    storage.save_textbooks(parsed)
    return parsed


@router.post("/upload")
async def upload_textbooks(files: list[UploadFile] = File(...)) -> list[Textbook]:
    existing = storage.load_textbooks()
    parsed = existing[:]
    for file in files:
        filename = Path(file.filename or "uploaded_textbook").name
        if Path(filename).suffix.lower() not in {".pdf", ".md", ".txt", ".docx"}:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {filename}")
        target = settings.upload_dir / filename
        target.write_bytes(await file.read())
        textbook_id = f"book_{len(parsed) + 1:03d}"
        try:
            parsed.append(parse_textbook_file(target, textbook_id=textbook_id))
        except Exception as exc:  # noqa: BLE001 - keep upload failures visible in UI.
            parsed.append(
                Textbook(
                    textbook_id=textbook_id,
                    filename=target.name,
                    title=target.stem,
                    format=target.suffix.lower().lstrip("."),
                    status="failed",
                    source_path=str(target),
                    error=str(exc),
                )
            )
    storage.save_textbooks(parsed)
    return parsed


@router.get("/{textbook_id}")
def get_textbook(textbook_id: str) -> Textbook:
    for textbook in storage.load_textbooks():
        if textbook.textbook_id == textbook_id:
            return textbook
    raise HTTPException(status_code=404, detail="Textbook not found")
