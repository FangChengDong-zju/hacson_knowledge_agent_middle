from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .config import ensure_runtime_dirs, settings
from .models import IntegrationDecision, IntegrationSummary, KnowledgeGraph, Textbook, TextbookOutline


T = TypeVar("T", bound=BaseModel)


def _path(name: str) -> Path:
    ensure_runtime_dirs()
    return settings.processed_dir / name


def _read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_textbooks() -> list[Textbook]:
    payload = _read_json(_path("textbooks.json"), [])
    return [Textbook.model_validate(item) for item in payload]


def save_textbooks(textbooks: list[Textbook]) -> None:
    _write_json(_path("textbooks.json"), [item.model_dump() for item in textbooks])


def load_outlines() -> list[TextbookOutline]:
    outline_path = _path("outlines.json")
    demo_path = settings.demo_dir / "outlines_demo.json"
    if outline_path.exists():
        payload = _read_json(outline_path, [])
    elif demo_path.exists():
        payload = _read_json(demo_path, [])
    else:
        payload = []
    return [TextbookOutline.model_validate(item) for item in payload]


def save_outlines(outlines: list[TextbookOutline]) -> None:
    _write_json(_path("outlines.json"), [item.model_dump() for item in outlines])


def load_graph() -> KnowledgeGraph:
    graph_path = _path("graph.json")
    demo_path = settings.demo_dir / "graph_demo.json"
    if graph_path.exists():
        payload = _read_json(graph_path, {"nodes": [], "edges": []})
    elif demo_path.exists():
        payload = _read_json(demo_path, {"nodes": [], "edges": []})
    else:
        payload = {"nodes": [], "edges": []}
    return KnowledgeGraph.model_validate(payload)


def save_graph(graph: KnowledgeGraph) -> None:
    _write_json(_path("graph.json"), graph.model_dump())


def load_decisions() -> list[IntegrationDecision]:
    payload = _read_json(_path("decisions.json"), [])
    return [IntegrationDecision.model_validate(item) for item in payload]


def save_decisions(decisions: list[IntegrationDecision]) -> None:
    _write_json(_path("decisions.json"), [item.model_dump() for item in decisions])


def load_summary() -> IntegrationSummary:
    payload = _read_json(_path("summary.json"), {})
    return IntegrationSummary.model_validate(payload)


def save_summary(summary: IntegrationSummary) -> None:
    _write_json(_path("summary.json"), summary.model_dump())
