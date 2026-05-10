from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ParseStatus = Literal["pending", "parsing", "parsed", "failed"]
DecisionAction = Literal["merge", "keep", "remove"]
RelationType = Literal["prerequisite", "parallel", "contains", "applies_to"]
Granularity = Literal["main", "detail_index"]
OutlineLevel = Literal["book", "chapter", "level1", "level2", "level3", "detail_index"]
DetailPolicy = Literal["graph_core", "detail_index", "visual_index"]


class Chapter(BaseModel):
    chapter_id: str
    textbook_id: str
    title: str
    page_start: int | None = None
    page_end: int | None = None
    content: str
    char_count: int


class Textbook(BaseModel):
    textbook_id: str
    filename: str
    title: str
    format: str
    total_pages: int | None = None
    total_chars: int = 0
    status: ParseStatus = "pending"
    chapters: list[Chapter] = Field(default_factory=list)
    source_path: str | None = None
    error: str | None = None


class SourceRef(BaseModel):
    textbook_id: str
    textbook_title: str = ""
    chapter_id: str | None = None
    chapter_title: str = ""
    page_start: int | None = None
    page_end: int | None = None
    source_path: str | None = None
    snippet: str = ""


class VisualRef(BaseModel):
    textbook_id: str
    textbook_title: str = ""
    chapter_id: str | None = None
    chapter_title: str = ""
    page_start: int | None = None
    page_end: int | None = None
    source_path: str | None = None
    note: str = ""


class KnowledgeNode(BaseModel):
    id: str
    name: str
    definition: str
    category: str = "核心概念"
    textbook_id: str
    chapter_id: str | None = None
    page: int | None = None
    source_text: str = ""
    frequency: int = 1
    status: Literal["raw", "merged", "kept", "removed"] = "raw"
    importance_score: float = 0.0
    granularity: Granularity = "main"
    keyword_path: list[str] = Field(default_factory=list)
    textbooks: list[str] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    visual_refs: list[VisualRef] = Field(default_factory=list)


class KnowledgeOutlineItem(BaseModel):
    outline_id: str
    textbook_id: str
    parent_id: str | None = None
    level: OutlineLevel
    order: int = 0
    title: str
    category: str = ""
    core_term: str = ""
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)
    keyword_path: list[str] = Field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    char_count: int = 0
    occurrence_count: int = 0
    importance_score: float = 0.0
    granularity: Granularity = "main"
    detail_policy: DetailPolicy = "graph_core"
    source_refs: list[SourceRef] = Field(default_factory=list)
    visual_refs: list[VisualRef] = Field(default_factory=list)


class TextbookOutline(BaseModel):
    textbook_id: str
    textbook_title: str
    source_path: str | None = None
    total_chars: int = 0
    item_count: int = 0
    items: list[KnowledgeOutlineItem] = Field(default_factory=list)


class KnowledgeEdge(BaseModel):
    source: str
    target: str
    relation_type: RelationType
    description: str = ""


class KnowledgeGraph(BaseModel):
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)


class IntegrationDecision(BaseModel):
    decision_id: str
    action: DecisionAction
    affected_nodes: list[str]
    result_node: str | None = None
    reason: str
    confidence: float = 0.0
    teacher_override: bool = False


class IntegrationSummary(BaseModel):
    textbook_count: int = 0
    original_chars: int = 0
    integrated_chars: int = 0
    compression_ratio: float = 0.0
    merge_count: int = 0
    keep_count: int = 0
    remove_count: int = 0


class Chunk(BaseModel):
    chunk_id: str
    textbook_id: str
    chapter_id: str
    page_start: int | None = None
    text: str
    keywords: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    textbook: str
    chapter: str
    page: int | None = None
    relevance_score: float = 0.0
    chunk_id: str | None = None
    source_text: str = ""


class RAGAnswer(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    source_chunks: list[str] = Field(default_factory=list)


class GraphBuildResponse(BaseModel):
    graph: KnowledgeGraph
    node_count: int
    edge_count: int


class OutlineBuildResponse(BaseModel):
    outlines: list[TextbookOutline]
    textbook_count: int
    item_count: int


class FeedbackRequest(BaseModel):
    message: str
    decision_id: str | None = None


class FeedbackResponse(BaseModel):
    reply: str
    updated_decision: IntegrationDecision | None = None
