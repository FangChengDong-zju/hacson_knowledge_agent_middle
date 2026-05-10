import type {
  IntegrationDecision,
  IntegrationSummary,
  KnowledgeGraph,
  RAGAnswer,
  Textbook,
  TextbookOutline,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; app: string; textbook_dir: string }>("/api/health"),
  localTextbooks: () => request<Array<{ filename: string; path: string; format: string; size: number }>>("/api/textbooks/local"),
  parseLocalTextbooks: () => request<Textbook[]>("/api/textbooks/parse-local", { method: "POST" }),
  uploadTextbooks: async (files: FileList | File[]) => {
    const form = new FormData();
    Array.from(files).forEach((file) => form.append("files", file));
    const response = await fetch(`${API_BASE}/api/textbooks/upload`, { method: "POST", body: form });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json() as Promise<Textbook[]>;
  },
  textbooks: () => request<Textbook[]>("/api/textbooks"),
  buildOutlines: () => request<{ outlines: TextbookOutline[]; textbook_count: number; item_count: number }>("/api/outlines/build", { method: "POST" }),
  outlines: () => request<TextbookOutline[]>("/api/outlines"),
  buildGraph: () => request<{ graph: KnowledgeGraph; node_count: number; edge_count: number }>("/api/graph/build", { method: "POST" }),
  graph: () => request<KnowledgeGraph>("/api/graph"),
  runIntegration: () => request<{ decisions: IntegrationDecision[]; summary: IntegrationSummary }>("/api/integration/run", { method: "POST" }),
  decisions: () => request<IntegrationDecision[]>("/api/integration/decisions"),
  summary: () => request<IntegrationSummary>("/api/integration/summary"),
  ragStatus: () => request<{ textbook_count: number; chunk_count: number }>("/api/rag/status"),
  ask: (question: string) => request<RAGAnswer>("/api/rag/query", { method: "POST", body: JSON.stringify({ question }) }),
  feedback: (message: string, decision_id?: string) =>
    request<{ reply: string; updated_decision?: IntegrationDecision }>("/api/feedback/chat", {
      method: "POST",
      body: JSON.stringify({ message, decision_id }),
    }),
  generateReport: () => request<{ path: string; content: string }>("/api/report/generate", { method: "POST" }),
};
