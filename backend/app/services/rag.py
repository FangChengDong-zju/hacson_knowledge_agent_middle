from __future__ import annotations

import math
import re
from collections import Counter

from ..models import Chunk, Citation, RAGAnswer, Textbook


CHINESE_RUN = re.compile(r"[\u4e00-\u9fff]+")
LATIN_TERM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-./+%]*")


def build_chunks(textbooks: list[Textbook], chunk_size: int = 700, overlap: int = 80) -> list[Chunk]:
    chunks: list[Chunk] = []
    for book in textbooks:
        for chapter in book.chapters:
            text = chapter.content
            start = 0
            chunk_index = 1
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]
                chunks.append(
                    Chunk(
                        chunk_id=f"{chapter.chapter_id}_chunk_{chunk_index:03d}",
                        textbook_id=book.textbook_id,
                        chapter_id=chapter.chapter_id,
                        page_start=chapter.page_start,
                        text=chunk_text,
                        keywords=query_terms(chunk_text)[:12],
                    )
                )
                if end == len(text):
                    break
                start = max(end - overlap, start + 1)
                chunk_index += 1
    return chunks


def answer_question(textbooks: list[Textbook], question: str, top_k: int = 5) -> RAGAnswer:
    chunks = build_chunks(textbooks)
    ranked = search_chunks(chunks, question, top_k)
    if not ranked:
        return RAGAnswer(answer="当前知识库中未找到相关信息。", citations=[], source_chunks=[])

    citations: list[Citation] = []
    source_texts: list[str] = []
    book_by_id = {book.textbook_id: book for book in textbooks}
    chapter_by_id = {chapter.chapter_id: chapter for book in textbooks for chapter in book.chapters}
    for score, chunk in ranked:
        book = book_by_id.get(chunk.textbook_id)
        chapter = chapter_by_id.get(chunk.chapter_id)
        citations.append(
            Citation(
                textbook=book.title if book else chunk.textbook_id,
                chapter=chapter.title if chapter else chunk.chapter_id,
                page=chunk.page_start,
                relevance_score=round(score, 3),
                chunk_id=chunk.chunk_id,
                source_text=chunk.text[:300],
            )
        )
        source_texts.append(chunk.text[:500])

    first = ranked[0][1]
    answer = f"根据当前教材索引，最相关内容指出：{first.text[:180]}..."
    return RAGAnswer(answer=answer, citations=citations, source_chunks=source_texts)


def search_chunks(chunks: list[Chunk], query: str, top_k: int) -> list[tuple[float, Chunk]]:
    terms = query_terms(query)
    frequencies = _document_frequencies(chunks, terms)
    ranked: list[tuple[float, Chunk]] = []
    for chunk in chunks:
        score = _score_chunk(chunk.text, terms, frequencies, len(chunks))
        if score > 0:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[:top_k]


def query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for item in LATIN_TERM.findall(query):
        if len(item) >= 2:
            terms.append(item.lower())
    for run in CHINESE_RUN.findall(query):
        if len(run) <= 4:
            terms.append(run)
        else:
            terms.extend(run[index : index + 2] for index in range(len(run) - 1))
            terms.extend(run[index : index + 3] for index in range(len(run) - 2))
    counter = Counter(terms)
    return [term for term, _ in counter.most_common()]


def _document_frequencies(chunks: list[Chunk], terms: list[str]) -> dict[str, int]:
    frequencies: dict[str, int] = {}
    for term in terms:
        frequencies[term] = sum(1 for chunk in chunks if term in _haystack(chunk.text, term))
    return frequencies


def _score_chunk(text: str, terms: list[str], frequencies: dict[str, int], total_chunks: int) -> float:
    score = 0.0
    for term in terms:
        count = _haystack(text, term).count(term)
        if count:
            idf = math.log((total_chunks + 1) / (frequencies.get(term, 0) + 1)) + 1.0
            score += min(count, 4) * idf * (1.0 + math.log1p(len(term)))
    return score


def _haystack(text: str, term: str) -> str:
    return text.lower() if re.search(r"[A-Za-z0-9]", term) else text

