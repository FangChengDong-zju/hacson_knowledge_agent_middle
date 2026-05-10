export type DecisionAction = "merge" | "keep" | "remove";

export interface Textbook {
  textbook_id: string;
  filename: string;
  title: string;
  format: string;
  total_pages?: number | null;
  total_chars: number;
  status: string;
  error?: string | null;
}

export interface KnowledgeNode {
  id: string;
  name: string;
  definition: string;
  category: string;
  textbook_id: string;
  chapter_id?: string | null;
  page?: number | null;
  frequency: number;
  status: string;
  source_text: string;
  importance_score?: number;
  granularity?: "main" | "detail_index";
  textbooks?: string[];
  source_refs?: SourceRef[];
  visual_refs?: VisualRef[];
}

export interface SourceRef {
  textbook_id: string;
  textbook_title: string;
  chapter_id?: string | null;
  chapter_title: string;
  page_start?: number | null;
  page_end?: number | null;
  source_path?: string | null;
  snippet: string;
}

export interface VisualRef {
  textbook_id: string;
  textbook_title: string;
  chapter_id?: string | null;
  chapter_title: string;
  page_start?: number | null;
  page_end?: number | null;
  source_path?: string | null;
  note: string;
}

export interface KnowledgeEdge {
  source: string;
  target: string;
  relation_type: string;
  description: string;
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface TextbookOutline {
  textbook_id: string;
  textbook_title: string;
  item_count: number;
}

export interface IntegrationDecision {
  decision_id: string;
  action: DecisionAction;
  affected_nodes: string[];
  result_node?: string | null;
  reason: string;
  confidence: number;
  teacher_override: boolean;
}

export interface IntegrationSummary {
  textbook_count: number;
  original_chars: number;
  integrated_chars: number;
  compression_ratio: number;
  merge_count: number;
  keep_count: number;
  remove_count: number;
}

export interface Citation {
  textbook: string;
  chapter: string;
  page?: number | null;
  relevance_score: number;
  source_text: string;
}

export interface RAGAnswer {
  answer: string;
  citations: Citation[];
  source_chunks: string[];
}
