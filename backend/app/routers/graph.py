from __future__ import annotations

from fastapi import APIRouter

from .. import storage
from ..models import GraphBuildResponse, KnowledgeGraph
from ..services.extractor import build_graph_from_outlines, build_graph_from_textbooks
from ..services.outline_builder import build_outlines_from_textbooks


router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.post("/build")
def build_graph() -> GraphBuildResponse:
    outlines = storage.load_outlines()
    if outlines:
        graph = build_graph_from_outlines(outlines)
    else:
        textbooks = storage.load_textbooks()
        outlines = build_outlines_from_textbooks(textbooks)
        storage.save_outlines(outlines)
        graph = build_graph_from_outlines(outlines) if outlines else build_graph_from_textbooks(textbooks)
    storage.save_graph(graph)
    return GraphBuildResponse(graph=graph, node_count=len(graph.nodes), edge_count=len(graph.edges))


@router.get("")
def get_graph() -> KnowledgeGraph:
    return storage.load_graph()
