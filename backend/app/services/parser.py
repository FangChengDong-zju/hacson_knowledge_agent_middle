from __future__ import annotations

import re
import json
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader

from ..config import settings
from ..models import Chapter, Textbook


CHAPTER_PATTERN = re.compile(r"(?m)^(第[一二三四五六七八九十百0-9]+[章节篇].{0,40}|Chapter\s+\d+.{0,40}|\d+[.、]\s*.{2,40})$")


def list_local_textbook_files() -> list[dict[str, object]]:
    if not settings.textbook_dir.exists():
        return []
    files = []
    for path in sorted(settings.textbook_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".pdf", ".md", ".txt", ".docx"}:
            files.append(
                {
                    "filename": path.name,
                    "path": str(path),
                    "format": path.suffix.lower().lstrip("."),
                    "size": path.stat().st_size,
                }
            )
    return files


def cached_index_available() -> bool:
    return settings.cached_chunks_path.exists() and settings.cached_stats_path.exists()


def parse_cached_textbook_index(limit: int = 7) -> list[Textbook]:
    stats = json.loads(settings.cached_stats_path.read_text(encoding="utf-8"))
    book_stats = {item["book_id"]: item for item in stats.get("books", [])}
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)

    with settings.cached_chunks_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            grouped[str(item.get("book_id", ""))].append(item)

    textbooks: list[Textbook] = []
    for order, book_id in enumerate(sorted(grouped.keys())[:limit], start=1):
        chunks = grouped[book_id]
        stat = book_stats.get(book_id, {})
        title = str(chunks[0].get("book_title") or stat.get("book_title") or f"教材 {book_id}")
        filename = str(chunks[0].get("source_file") or stat.get("source_file") or f"{book_id}.pdf")
        chapters = _chapters_from_cached_chunks(f"book_{order:03d}", chunks)
        total_chars = sum(chapter.char_count for chapter in chapters)
        textbooks.append(
            Textbook(
                textbook_id=f"book_{order:03d}",
                filename=filename,
                title=title,
                format="pdf",
                total_pages=int(stat.get("pages", 0) or 0),
                total_chars=total_chars,
                status="parsed",
                chapters=chapters,
                source_path=str(settings.textbook_dir / filename),
            )
        )
    return textbooks


def parse_textbook_file(path: Path, textbook_id: str | None = None) -> Textbook:
    textbook_id = textbook_id or _safe_id(path.stem)
    extension = path.suffix.lower()
    if extension == ".pdf":
        pages = _extract_pdf_pages(path)
    elif extension in {".md", ".txt"}:
        pages = [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    elif extension == ".docx":
        pages = [(1, _extract_docx_text(path))]
    else:
        raise ValueError(f"暂不支持的教材格式：{extension}")

    full_text = "\n\n".join(text for _, text in pages).strip()
    chapters = _split_chapters(textbook_id, pages)
    return Textbook(
        textbook_id=textbook_id,
        filename=path.name,
        title=path.stem,
        format=extension.lstrip("."),
        total_pages=len(pages) if extension == ".pdf" else None,
        total_chars=len(full_text),
        status="parsed",
        chapters=chapters,
        source_path=str(path),
    )


def _extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = _clean_page_text(text)
        if text:
            pages.append((index, text))
    return pages


def _extract_docx_text(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(lines)


def _clean_page_text(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"\d+|第\s*\d+\s*页", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _split_chapters(textbook_id: str, pages: list[tuple[int, str]]) -> list[Chapter]:
    joined = "\n".join(text for _, text in pages)
    matches = list(CHAPTER_PATTERN.finditer(joined))
    if not matches:
        content = joined[:12000]
        return [
            Chapter(
                chapter_id=f"{textbook_id}_ch_001",
                textbook_id=textbook_id,
                title="全文",
                page_start=pages[0][0] if pages else None,
                page_end=pages[-1][0] if pages else None,
                content=content,
                char_count=len(content),
            )
        ]

    chapters: list[Chapter] = []
    for index, match in enumerate(matches[:80], start=1):
        start = match.start()
        end = matches[index].start() if index < len(matches) else len(joined)
        title = match.group(1).strip()
        content = joined[start:end].strip()
        chapters.append(
            Chapter(
                chapter_id=f"{textbook_id}_ch_{index:03d}",
                textbook_id=textbook_id,
                title=title,
                page_start=None,
                page_end=None,
                content=content[:16000],
                char_count=len(content),
            )
        )
    return chapters


def _chapters_from_cached_chunks(textbook_id: str, chunks: list[dict[str, object]], pages_per_chapter: int = 25) -> list[Chapter]:
    by_bucket: dict[int, list[dict[str, object]]] = defaultdict(list)
    for chunk in chunks:
        page = int(chunk.get("page") or 1)
        bucket = max((page - 1) // pages_per_chapter, 0)
        by_bucket[bucket].append(chunk)

    chapters: list[Chapter] = []
    for index, bucket in enumerate(sorted(by_bucket.keys()), start=1):
        bucket_chunks = by_bucket[bucket]
        page_start = min(int(item.get("page") or 1) for item in bucket_chunks)
        page_end = max(int(item.get("page") or 1) for item in bucket_chunks)
        content = "\n".join(str(item.get("text", "")).strip() for item in bucket_chunks if str(item.get("text", "")).strip())
        chapters.append(
            Chapter(
                chapter_id=f"{textbook_id}_ch_{index:03d}",
                textbook_id=textbook_id,
                title=f"第 {page_start}-{page_end} 页知识段",
                page_start=page_start,
                page_end=page_end,
                content=content[:18000],
                char_count=len(content),
            )
        )
    return chapters


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value).strip("_")
    return normalized or "book"
