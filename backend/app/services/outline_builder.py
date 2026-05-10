from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ..models import KnowledgeOutlineItem, SourceRef, Textbook, TextbookOutline, VisualRef


RESOURCE_PATH = Path(__file__).resolve().parents[1] / "resources" / "core_terms.json"


def build_outlines_from_textbooks(textbooks: list[Textbook], max_terms_per_chapter: int = 6) -> list[TextbookOutline]:
    ontology = _load_ontology()
    terms = ontology.get("terms", [])
    relations = ontology.get("relations", [])
    category_paths = ontology.get("category_paths", {})
    outlines: list[TextbookOutline] = []

    for textbook in textbooks:
        items: list[KnowledgeOutlineItem] = []
        root_id = f"{textbook.textbook_id}_outline_root"
        items.append(
            KnowledgeOutlineItem(
                outline_id=root_id,
                textbook_id=textbook.textbook_id,
                level="book",
                order=0,
                title=textbook.title,
                summary=f"{textbook.title} 教材结构化提纲。",
                page_start=1,
                page_end=textbook.total_pages,
                char_count=textbook.total_chars,
                detail_policy="detail_index",
            )
        )

        for chapter_index, chapter in enumerate(textbook.chapters, start=1):
            chapter_id = f"{textbook.textbook_id}_outline_ch_{chapter_index:03d}"
            items.append(
                KnowledgeOutlineItem(
                    outline_id=chapter_id,
                    textbook_id=textbook.textbook_id,
                    parent_id=root_id,
                    level="chapter",
                    order=chapter_index,
                    title=chapter.title,
                    summary=_chapter_summary(chapter.content),
                    page_start=chapter.page_start,
                    page_end=chapter.page_end,
                    char_count=chapter.char_count,
                    detail_policy="detail_index",
                    source_refs=[_source_ref(textbook, chapter.chapter_id, chapter.title, chapter.page_start, chapter.page_end, chapter.content[:220])],
                )
            )

            if chapter.page_end and chapter.page_end <= 25:
                continue

            ranked_terms = _rank_terms(chapter.content, terms)
            level1_terms = ranked_terms[:max_terms_per_chapter]
            for term_index, term in enumerate(level1_terms, start=1):
                term_name = str(term["name"])
                item_id = f"{chapter_id}_l1_{term_index:02d}"
                snippet = _source_snippet(chapter.content, term_name)
                visual_refs = [_visual_ref(textbook, chapter.chapter_id, chapter.title, chapter.page_start, chapter.page_end)] if _has_visual_hint(chapter.content, term_name) else []
                items.append(
                    KnowledgeOutlineItem(
                        outline_id=item_id,
                        textbook_id=textbook.textbook_id,
                        parent_id=chapter_id,
                        level="level1",
                        order=term_index,
                        title=term_name,
                        category=str(term.get("category", "")),
                        core_term=term_name,
                        summary=snippet or f"{term_name} 是本页段的主干知识点。",
                        keywords=[term_name, *[str(item) for item in term.get("synonyms", [])]][:5],
                        keyword_path=_keyword_path(category_paths, str(term.get("category", "")), term_name),
                        page_start=chapter.page_start,
                        page_end=chapter.page_end,
                        char_count=len(snippet),
                        occurrence_count=int(term.get("count", 1)),
                        importance_score=float(term.get("score", 0.0)),
                        granularity=str(term.get("level", "main")),  # type: ignore[arg-type]
                        detail_policy="graph_core" if term.get("level", "main") == "main" else "detail_index",
                        source_refs=[_source_ref(textbook, chapter.chapter_id, chapter.title, chapter.page_start, chapter.page_end, snippet)],
                        visual_refs=visual_refs,
                    )
                )

                for rel_index, related in enumerate(_related_terms(term_name, ranked_terms, relations)[:3], start=1):
                    related_name = str(related["name"])
                    related_snippet = _source_snippet(chapter.content, related_name)
                    items.append(
                        KnowledgeOutlineItem(
                            outline_id=f"{item_id}_l2_{rel_index:02d}",
                            textbook_id=textbook.textbook_id,
                            parent_id=item_id,
                            level="level2",
                            order=rel_index,
                            title=related_name,
                            category=str(related.get("category", "")),
                            core_term=related_name,
                            summary=related_snippet or f"{related_name} 是 {term_name} 的相关知识点。",
                            keywords=[related_name],
                            keyword_path=_keyword_path(category_paths, str(related.get("category", "")), related_name),
                            page_start=chapter.page_start,
                            page_end=chapter.page_end,
                            char_count=len(related_snippet),
                            occurrence_count=int(related.get("count", 1)),
                            importance_score=float(related.get("score", 0.0)),
                            granularity=str(related.get("level", "main")),  # type: ignore[arg-type]
                            detail_policy="graph_core" if related.get("level", "main") == "main" else "detail_index",
                            source_refs=[_source_ref(textbook, chapter.chapter_id, chapter.title, chapter.page_start, chapter.page_end, related_snippet)],
                        )
                    )

        outlines.append(
            TextbookOutline(
                textbook_id=textbook.textbook_id,
                textbook_title=textbook.title,
                source_path=textbook.source_path,
                total_chars=textbook.total_chars,
                item_count=len(items),
                items=items,
            )
        )
    return outlines


def _load_ontology() -> dict[str, object]:
    if RESOURCE_PATH.exists():
        return json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))
    return {"terms": [], "relations": []}


def _keyword_path(category_paths: dict[str, list[str]], category: str, term_name: str) -> list[str]:
    return [*category_paths.get(category, []), term_name]


def _rank_terms(content: str, terms: list[dict[str, object]]) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    for term in terms:
        names = [str(term.get("name", "")), *[str(item) for item in term.get("synonyms", [])]]
        count = sum(content.count(name) for name in names if name)
        if count <= 0:
            continue
        priority = float(term.get("priority", 0.5) or 0.5)
        level_boost = 0.18 if term.get("level", "main") == "main" else 0.0
        score = priority + min(count / 40, 0.22) + level_boost
        ranked.append({**term, "count": count, "score": round(score, 4)})
    return sorted(ranked, key=lambda item: (-float(item["score"]), -int(item["count"]), str(item["name"])))


def _related_terms(term_name: str, ranked_terms: list[dict[str, object]], relations: list[dict[str, object]]) -> list[dict[str, object]]:
    relation_names: set[str] = set()
    for relation in relations:
        source = str(relation.get("source", ""))
        target = str(relation.get("target", ""))
        if source == term_name:
            relation_names.add(target)
        if target == term_name:
            relation_names.add(source)
    fallback_category = next((str(item.get("category", "")) for item in ranked_terms if item.get("name") == term_name), "")
    related = [
        item
        for item in ranked_terms
        if item.get("name") != term_name
        and (str(item.get("name")) in relation_names or str(item.get("category", "")) == fallback_category)
    ]
    return related


def _chapter_summary(content: str) -> str:
    cleaned = re.sub(r"\s+", " ", content).strip()
    return cleaned[:260]


def _source_snippet(content: str, term: str, radius: int = 90) -> str:
    index = content.find(term)
    if index < 0:
        return ""
    start = max(index - radius, 0)
    end = min(index + len(term) + radius, len(content))
    return re.sub(r"\s+", " ", content[start:end]).strip()[:220]


def _has_visual_hint(content: str, term: str) -> bool:
    index = content.find(term)
    if index < 0:
        return False
    window = content[max(index - 180, 0) : min(index + len(term) + 180, len(content))]
    return "图" in window or "表" in window


def _source_ref(
    textbook: Textbook,
    chapter_id: str | None,
    chapter_title: str,
    page_start: int | None,
    page_end: int | None,
    snippet: str,
) -> SourceRef:
    return SourceRef(
        textbook_id=textbook.textbook_id,
        textbook_title=textbook.title,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        page_start=page_start,
        page_end=page_end,
        source_path=textbook.source_path,
        snippet=snippet,
    )


def _visual_ref(
    textbook: Textbook,
    chapter_id: str | None,
    chapter_title: str,
    page_start: int | None,
    page_end: int | None,
) -> VisualRef:
    return VisualRef(
        textbook_id=textbook.textbook_id,
        textbook_title=textbook.title,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        page_start=page_start,
        page_end=page_end,
        source_path=textbook.source_path,
        note="本页段存在图/表线索，图像内容应作为整合版视觉索引保留。",
    )
