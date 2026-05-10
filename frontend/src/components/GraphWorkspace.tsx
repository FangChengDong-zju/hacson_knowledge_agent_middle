import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import type { KnowledgeGraph, KnowledgeNode } from "../types";

interface Props {
  graph: KnowledgeGraph;
}

export default function GraphWorkspace({ graph }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [selected, setSelected] = useState<KnowledgeNode | null>(null);
  const categoryLabel = (category: string) => (category === "knowledge_layer" ? "知识层级" : category);

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...graph.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.name,
            frequency: node.frequency,
            status: node.status,
            category: node.category,
            textbookCount: node.textbooks?.length ?? 1,
            granularity: node.granularity ?? "main",
            node,
          },
        })),
        ...graph.edges.map((edge, index) => ({
          data: { id: `edge_${index}`, source: edge.source, target: edge.target, label: edge.relation_type },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": "#2563eb",
            color: "#172033",
            width: "mapData(textbookCount, 1, 7, 34, 82)",
            height: "mapData(textbookCount, 1, 7, 34, 82)",
            "font-size": 11,
            "text-wrap": "wrap",
            "text-max-width": 80,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#9aa7bd",
            "target-arrow-color": "#9aa7bd",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: 'node[status = "merged"]',
          style: { "background-color": "#7c3aed" },
        },
        {
          selector: 'node[category = "感染免疫"]',
          style: { "background-color": "#0891b2" },
        },
        {
          selector: 'node[category = "病理过程"]',
          style: { "background-color": "#dc2626" },
        },
        {
          selector: 'node[category = "生理机制"]',
          style: { "background-color": "#059669" },
        },
        {
          selector: 'node[category = "基础结构"]',
          style: { "background-color": "#7c3aed" },
        },
        {
          selector: 'node[category = "knowledge_layer"]',
          style: {
            "background-color": "#172033",
            color: "#0f172a",
            "border-width": 3,
            "border-color": "#f59e0b",
          },
        },
        {
          selector: 'node[status = "removed"]',
          style: { "background-color": "#dc2626" },
        },
      ],
      layout: { name: "cose", animate: false },
    });
    cy.on("tap", "node", (event) => {
      setSelected(event.target.data("node") as KnowledgeNode);
    });
    return () => cy.destroy();
  }, [graph]);

  return (
    <section className="graph-panel">
      <div className="panel-heading">
        <h2>知识图谱</h2>
        <span>{graph.nodes.length} 节点 / {graph.edges.length} 关系</span>
      </div>
      <div className="graph-canvas" ref={containerRef}>
        {graph.nodes.length === 0 && <p className="empty-state">解析教材后构建图谱。</p>}
      </div>
      {selected && (
        <aside className="node-detail">
          <div className="node-detail-head">
            <strong>{selected.name}</strong>
            <span>{categoryLabel(selected.category)}</span>
          </div>
          <p className="keyword-path">{selected.keyword_path?.join(" / ")}</p>
          <p>{selected.definition}</p>
          <div className="node-meta">
            <span>{selected.textbooks?.length ?? 1} 本教材</span>
            <span>{selected.frequency.toLocaleString()} 次出现</span>
            <span>{selected.granularity === "detail_index" ? "细节索引" : "主干节点"}</span>
          </div>
          {selected.textbooks?.length ? (
            <div className="source-strip">
              {selected.textbooks.map((title) => <span key={title}>{title}</span>)}
            </div>
          ) : null}
          {selected.source_refs?.length ? (
            <div className="ref-list">
              <h3>来源索引</h3>
              {selected.source_refs.slice(0, 3).map((ref) => (
                <article key={`${ref.textbook_id}-${ref.chapter_id}-${ref.page_start}`}>
                  <strong>{ref.textbook_title}</strong>
                  <small>{ref.chapter_title} · 页 {ref.page_start ?? "-"}</small>
                  <p>{ref.snippet}</p>
                </article>
              ))}
            </div>
          ) : null}
          {selected.visual_refs?.length ? (
            <small className="visual-hint">图表索引：{selected.visual_refs.length} 处，保留原文 PDF 页段入口。</small>
          ) : null}
        </aside>
      )}
    </section>
  );
}
