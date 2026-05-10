from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from ..models import KnowledgeEdge, KnowledgeGraph, KnowledgeNode, SourceRef, Textbook, TextbookOutline, VisualRef


RESOURCE_PATH = Path(__file__).resolve().parents[1] / "resources" / "core_terms.json"
CHINESE_TERM = re.compile(r"[\u4e00-\u9fff]{2,8}")
STOP_TERMS = {"教材", "章节", "内容", "概念", "系统", "主要", "进行", "包括", "由于", "可以", "一个"}


def build_graph_from_textbooks(textbooks: list[Textbook], max_nodes: int = 90) -> KnowledgeGraph:
    ontology = _load_ontology()
    nodes = _extract_ontology_nodes(
        textbooks,
        ontology.get("terms", []),
        ontology.get("category_preferences", {}),
        ontology.get("category_paths", {}),
        max_nodes=max_nodes,
    )
    edges = _build_edges(nodes, ontology.get("relations", []), textbooks)
    return KnowledgeGraph(nodes=nodes, edges=edges)


def build_graph_from_outlines(outlines: list[TextbookOutline], max_nodes: int = 90) -> KnowledgeGraph:
    ontology = _load_ontology()
    relations = ontology.get("relations", [])
    groups: dict[str, dict[str, object]] = {}
    parent_links: Counter[tuple[str, str]] = Counter()

    for outline in outlines:
        item_by_id = {item.outline_id: item for item in outline.items}
        for item in outline.items:
            if item.detail_policy != "graph_core" or not item.core_term:
                continue
            group = groups.setdefault(
                item.core_term,
                {
                    "term": item.core_term,
                    "category": item.category,
                    "keyword_path": item.keyword_path,
                    "textbooks": set(),
                    "source_refs": [],
                    "visual_refs": [],
                    "frequency": 0,
                    "importance": 0.0,
                    "snippet": "",
                    "sample_item": item,
                },
            )
            group["textbooks"].add(outline.textbook_title)  # type: ignore[union-attr]
            group["frequency"] = int(group["frequency"]) + max(item.occurrence_count, 1)
            group["importance"] = max(float(group["importance"]), item.importance_score)
            if not group["snippet"] and item.summary:
                group["snippet"] = item.summary
                group["sample_item"] = item
            group["source_refs"].extend(item.source_refs[:2])  # type: ignore[union-attr]
            group["visual_refs"].extend(item.visual_refs[:2])  # type: ignore[union-attr]

            parent = item_by_id.get(item.parent_id or "")
            if parent and parent.core_term and parent.detail_policy == "graph_core":
                parent_links[(parent.core_term, item.core_term)] += 1

    ranked = sorted(
        groups.values(),
        key=lambda group: (-len(group["textbooks"]), -float(group["importance"]), -int(group["frequency"]), str(group["term"])),
    )[:max_nodes]
    id_by_term: dict[str, str] = {}
    nodes: list[KnowledgeNode] = []
    for index, group in enumerate(ranked, start=1):
        item = group["sample_item"]
        node_id = f"kg_{index:03d}"
        id_by_term[str(group["term"])] = node_id
        source_refs = _dedupe_source_refs(group["source_refs"])[:5]  # type: ignore[arg-type]
        visual_refs = _dedupe_visual_refs(group["visual_refs"])[:4]  # type: ignore[arg-type]
        nodes.append(
            KnowledgeNode(
                id=node_id,
                name=str(group["term"]),
                definition=str(group["snippet"] or f"{group['term']} 是医学教材中的主干知识点。"),
                category=str(group["category"]),
                textbook_id=item.textbook_id,
                chapter_id=item.source_refs[0].chapter_id if item.source_refs else None,
                page=item.page_start,
                source_text=str(group["snippet"]),
                frequency=int(group["frequency"]),
                status="kept",
                importance_score=round(float(group["importance"]), 4),
                granularity=item.granularity,
                keyword_path=list(group["keyword_path"]),
                textbooks=sorted(group["textbooks"]),  # type: ignore[arg-type]
                source_refs=source_refs,
                visual_refs=visual_refs,
            )
        )

    term_paths = {node.name: node.keyword_path for node in nodes}
    path_nodes, path_key_to_id = _build_keyword_layer_nodes(nodes)
    nodes.extend(path_nodes)
    edges = _build_outline_edges(id_by_term, path_key_to_id, term_paths, parent_links, relations)
    return KnowledgeGraph(nodes=nodes, edges=edges)


def _build_keyword_layer_nodes(nodes: list[KnowledgeNode]) -> tuple[list[KnowledgeNode], dict[str, str]]:
    path_textbooks: dict[str, set[str]] = defaultdict(set)
    path_parts_by_key: dict[str, list[str]] = {}
    for node in nodes:
        if len(node.keyword_path) < 2:
            continue
        for index in range(len(node.keyword_path) - 1):
            parts = node.keyword_path[: index + 1]
            key = " > ".join(parts)
            path_parts_by_key[key] = parts
            path_textbooks[key].update(node.textbooks)

    path_key_to_id: dict[str, str] = {}
    path_nodes: list[KnowledgeNode] = []
    for index, key in enumerate(sorted(path_parts_by_key.keys()), start=1):
        node_id = f"path_{index:03d}"
        parts = path_parts_by_key[key]
        path_key_to_id[key] = node_id
        path_nodes.append(
            KnowledgeNode(
                id=node_id,
                name=parts[-1],
                definition=f"医学多级关键词路径节点：{key}",
                category="knowledge_layer",
                textbook_id="multi_source",
                frequency=max(len(path_textbooks[key]), 1),
                status="merged",
                importance_score=1.0,
                keyword_path=parts,
                textbooks=sorted(path_textbooks[key]),
            )
        )
    return path_nodes, path_key_to_id


def _dedupe_source_refs(refs: list[SourceRef]) -> list[SourceRef]:
    seen: set[tuple[str, str | None, int | None]] = set()
    result: list[SourceRef] = []
    for ref in refs:
        key = (ref.textbook_id, ref.chapter_id, ref.page_start)
        if key in seen:
            continue
        seen.add(key)
        result.append(ref)
    return result


def _dedupe_visual_refs(refs: list[VisualRef]) -> list[VisualRef]:
    seen: set[tuple[str, str | None, int | None]] = set()
    result: list[VisualRef] = []
    for ref in refs:
        key = (ref.textbook_id, ref.chapter_id, ref.page_start)
        if key in seen:
            continue
        seen.add(key)
        result.append(ref)
    return result


def _build_outline_edges(
    id_by_term: dict[str, str],
    path_key_to_id: dict[str, str],
    term_paths: dict[str, list[str]],
    parent_links: Counter[tuple[str, str]],
    relations: list[dict[str, object]],
) -> list[KnowledgeEdge]:
    edges: list[KnowledgeEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for relation in relations:
        source_name = str(relation.get("source", ""))
        target_name = str(relation.get("target", ""))
        if source_name not in id_by_term or target_name not in id_by_term:
            continue
        relation_type = str(relation.get("relation_type", "parallel"))
        if relation_type not in {"prerequisite", "parallel", "contains", "applies_to"}:
            relation_type = "parallel"
        key = (id_by_term[source_name], id_by_term[target_name], relation_type)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            KnowledgeEdge(
                source=key[0],
                target=key[1],
                relation_type=relation_type,  # type: ignore[arg-type]
                description=str(relation.get("description", "")),
            )
        )

    for (parent, child), count in parent_links.most_common(100):
        if parent not in id_by_term or child not in id_by_term:
            continue
        key = (id_by_term[parent], id_by_term[child], "contains")
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            KnowledgeEdge(
                source=key[0],
                target=key[1],
                relation_type="contains",
                description=f"outline_parent_child_count={count}",
            )
        )

    path_groups: dict[str, list[str]] = defaultdict(list)
    for term, keyword_path in term_paths.items():
        if len(keyword_path) < 2:
            continue
        for index in range(1, len(keyword_path)):
            source_key = " > ".join(keyword_path[:index])
            if source_key not in path_key_to_id:
                continue
            if index == len(keyword_path) - 1:
                target_term = keyword_path[index]
                if target_term not in id_by_term:
                    continue
                target = id_by_term[target_term]
            else:
                target_key = " > ".join(keyword_path[: index + 1])
                if target_key not in path_key_to_id:
                    continue
                target = path_key_to_id[target_key]
            key = (path_key_to_id[source_key], target, "contains")
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                KnowledgeEdge(
                    source=key[0],
                    target=key[1],
                    relation_type="contains",
                    description="multi_level_keyword_path",
                )
            )
        prefix = " > ".join(keyword_path[:-1])
        path_groups[prefix].append(term)

    for prefix, terms in path_groups.items():
        terms = [term for term in terms if term in id_by_term][:8]
        for left_index, left in enumerate(terms):
            for right in terms[left_index + 1 :]:
                key = (id_by_term[left], id_by_term[right], "parallel")
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    KnowledgeEdge(
                        source=key[0],
                        target=key[1],
                        relation_type="parallel",
                        description=f"same_keyword_path={prefix}",
                    )
                )
    return edges


def _load_ontology() -> dict[str, object]:
    if RESOURCE_PATH.exists():
        return json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))
    return {"terms": [], "relations": []}


def _extract_ontology_nodes(
    textbooks: list[Textbook],
    term_defs: list[dict[str, object]],
    category_preferences: dict[str, list[str]],
    category_paths: dict[str, list[str]],
    max_nodes: int,
) -> list[KnowledgeNode]:
    candidates: list[KnowledgeNode] = []
    for index, term in enumerate(term_defs, start=1):
        names = [str(term.get("name", "")), *[str(item) for item in term.get("synonyms", [])]]
        names = [name for name in names if name]
        candidate_refs: list[tuple[int, int, SourceRef]] = []
        candidate_visual_refs: list[tuple[int, int, VisualRef]] = []
        frequency = 0
        textbook_titles: set[str] = set()
        first_textbook_id = "multi_source"
        first_chapter_id: str | None = None
        first_page: int | None = None

        for textbook in textbooks:
            for chapter in textbook.chapters:
                matched_names = [name for name in names if name in chapter.content or name in chapter.title]
                if not matched_names:
                    continue

                matched_frequency = sum(chapter.content.count(name) for name in matched_names)
                frequency += max(matched_frequency, 1)
                textbook_titles.add(textbook.title)
                if first_textbook_id == "multi_source":
                    first_textbook_id = textbook.textbook_id
                    first_chapter_id = chapter.chapter_id
                    first_page = chapter.page_start

                primary_name = matched_names[0]
                snippet = _source_snippet(chapter.content, primary_name)
                if _snippet_quality(snippet):
                    rank = _preference_rank(category_preferences, str(term.get("category", "")), textbook.title)
                    candidate_refs.append(
                        (
                            rank,
                            chapter.page_start or 9999,
                            SourceRef(
                                textbook_id=textbook.textbook_id,
                                textbook_title=textbook.title,
                                chapter_id=chapter.chapter_id,
                                chapter_title=chapter.title,
                                page_start=chapter.page_start,
                                page_end=chapter.page_end,
                                source_path=textbook.source_path,
                                snippet=snippet,
                            ),
                        )
                    )
                if _has_visual_hint(chapter.content, primary_name):
                    rank = _preference_rank(category_preferences, str(term.get("category", "")), textbook.title)
                    candidate_visual_refs.append(
                        (
                            rank,
                            chapter.page_start or 9999,
                            VisualRef(
                                textbook_id=textbook.textbook_id,
                                textbook_title=textbook.title,
                                chapter_id=chapter.chapter_id,
                                chapter_title=chapter.title,
                                page_start=chapter.page_start,
                                page_end=chapter.page_end,
                                source_path=textbook.source_path,
                                note="本页段存在图/表线索，适合在整合版中保留图像入口。",
                            ),
                        )
                    )

        if frequency <= 0:
            continue

        refs = [item[2] for item in sorted(candidate_refs, key=lambda item: (item[0], item[1]))[:5]]
        visual_refs = [item[2] for item in sorted(candidate_visual_refs, key=lambda item: (item[0], item[1]))[:4]]
        source_text = refs[0].snippet if refs else ""
        node_textbook_id = refs[0].textbook_id if refs else first_textbook_id
        node_chapter_id = refs[0].chapter_id if refs else first_chapter_id
        node_page = refs[0].page_start if refs else first_page
        category = str(term.get("category", "核心概念"))
        definition = source_text or f"{term.get('name')} 是医学教材中的主干知识点。"
        priority = float(term.get("priority", 0.5) or 0.5)
        coverage = len(textbook_titles) / max(len(textbooks), 1)
        importance = round(priority * 0.7 + min(math.log1p(frequency) / 8, 1) * 0.15 + coverage * 0.15, 4)
        candidates.append(
            KnowledgeNode(
                id=f"kg_{index:03d}",
                name=str(term.get("name")),
                definition=definition,
                category=category,
                textbook_id=node_textbook_id,
                chapter_id=node_chapter_id,
                page=node_page,
                source_text=source_text,
                frequency=frequency,
                status="kept",
                importance_score=importance,
                granularity=str(term.get("level", "main")),  # type: ignore[arg-type]
                keyword_path=_keyword_path(category_paths, category, str(term.get("name"))),
                textbooks=sorted(textbook_titles),
                source_refs=refs,
                visual_refs=visual_refs,
            )
        )

    candidates.sort(key=lambda node: (node.granularity != "main", -node.importance_score, -node.frequency, node.name))
    return candidates[:max_nodes]


def _preference_rank(category_preferences: dict[str, list[str]], category: str, textbook_title: str) -> int:
    preferred = category_preferences.get(category, [])
    try:
        return preferred.index(textbook_title)
    except ValueError:
        return 50


def _keyword_path(category_paths: dict[str, list[str]], category: str, term_name: str) -> list[str]:
    return [*category_paths.get(category, []), term_name]


def _build_edges(nodes: list[KnowledgeNode], relations: list[dict[str, object]], textbooks: list[Textbook]) -> list[KnowledgeEdge]:
    by_name = {node.name: node for node in nodes}
    edges: list[KnowledgeEdge] = []
    seen: set[tuple[str, str, str]] = set()

    for relation in relations:
        source_name = str(relation.get("source", ""))
        target_name = str(relation.get("target", ""))
        if source_name not in by_name or target_name not in by_name:
            continue
        relation_type = str(relation.get("relation_type", "parallel"))
        if relation_type not in {"prerequisite", "parallel", "contains", "applies_to"}:
            relation_type = "parallel"
        source = by_name[source_name].id
        target = by_name[target_name].id
        key = (source, target, relation_type)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            KnowledgeEdge(
                source=source,
                target=target,
                relation_type=relation_type,  # type: ignore[arg-type]
                description=str(relation.get("description", "")),
            )
        )

    edges.extend(_cooccurrence_edges(nodes, textbooks, seen, limit=140))
    return edges


def _cooccurrence_edges(
    nodes: list[KnowledgeNode],
    textbooks: list[Textbook],
    seen: set[tuple[str, str, str]],
    limit: int,
) -> list[KnowledgeEdge]:
    term_to_node = {node.name: node for node in nodes}
    counts: Counter[tuple[str, str]] = Counter()
    for textbook in textbooks:
        for chapter in textbook.chapters:
            present = [name for name in term_to_node if name in chapter.content]
            for left_index, left in enumerate(present[:10]):
                for right in present[left_index + 1 : 10]:
                    pair = tuple(sorted((term_to_node[left].id, term_to_node[right].id)))
                    counts[pair] += 1

    edges: list[KnowledgeEdge] = []
    for (source, target), count in counts.most_common(limit):
        key = (source, target, "parallel")
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            KnowledgeEdge(
                source=source,
                target=target,
                relation_type="parallel",
                description=f"两个知识点在 {count} 个章节/页段中共同出现，保留为并列关联。",
            )
        )
    return edges


def _source_snippet(content: str, term: str, radius: int = 90) -> str:
    index = content.find(term)
    if index < 0:
        return ""
    start = max(index - radius, 0)
    end = min(index + len(term) + radius, len(content))
    snippet = re.sub(r"\s+", " ", content[start:end]).strip()
    return snippet[:220]


def _snippet_quality(snippet: str) -> bool:
    if len(snippet) < 20:
        return False
    if len(re.findall(r"\d", snippet)) > 35:
        return False
    if re.search(r"(\d+\s+){8,}", snippet):
        return False
    return True


def _has_visual_hint(content: str, term: str) -> bool:
    index = content.find(term)
    if index < 0:
        return False
    start = max(index - 180, 0)
    end = min(index + len(term) + 180, len(content))
    window = content[start:end]
    return "图" in window or "表" in window


def _top_terms(content: str) -> list[str]:
    terms = [term for term in CHINESE_TERM.findall(content) if term not in STOP_TERMS]
    counter = Counter(terms)
    return [term for term, _ in counter.most_common(12)]
