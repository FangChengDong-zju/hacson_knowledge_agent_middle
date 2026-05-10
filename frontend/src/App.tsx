import { useEffect, useState } from "react";
import { api } from "./api";
import GraphWorkspace from "./components/GraphWorkspace";
import QAWorkspace from "./components/QAWorkspace";
import DecisionPanel from "./components/DecisionPanel";
import UploadPanel from "./components/UploadPanel";
import type { IntegrationDecision, IntegrationSummary, KnowledgeGraph, Textbook } from "./types";

export default function App() {
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [graph, setGraph] = useState<KnowledgeGraph>({ nodes: [], edges: [] });
  const [decisions, setDecisions] = useState<IntegrationDecision[]>([]);
  const [summary, setSummary] = useState<IntegrationSummary | null>(null);
  const [status, setStatus] = useState("准备就绪");

  async function refresh() {
    const [books, graphData, decisionData] = await Promise.all([api.textbooks(), api.graph(), api.decisions()]);
    setTextbooks(books);
    setGraph(graphData);
    setDecisions(decisionData);
    try {
      setSummary(await api.summary());
    } catch {
      setSummary(null);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function parseLocal() {
    setStatus("正在解析 E:/textbooks 教材；如存在缓存会优先使用缓存...");
    const books = await api.parseLocalTextbooks();
    setTextbooks(books);
    setStatus(`已解析 ${books.length} 本教材`);
  }

  async function uploadTextbooks(files: FileList) {
    setStatus("正在上传并解析临时教材...");
    const books = await api.uploadTextbooks(files);
    setTextbooks(books);
    setStatus(`已纳入 ${books.length} 本教材，可重新整理层级并构建图谱`);
  }

  async function buildOutlines() {
    setStatus("正在整理教材层级：章节 -> 一级知识点 -> 二级知识点...");
    const result = await api.buildOutlines();
    setStatus(`层级已生成：${result.textbook_count} 本教材 / ${result.item_count} 个层级项`);
  }

  async function buildGraph() {
    setStatus("正在基于多级关键词构建跨教材知识图谱...");
    const result = await api.buildGraph();
    setGraph(result.graph);
    setStatus(`图谱已生成：${result.node_count} 节点 / ${result.edge_count} 关系`);
  }

  async function runIntegration() {
    setStatus("正在整合与压缩...");
    const result = await api.runIntegration();
    setDecisions(result.decisions);
    setSummary(result.summary);
    setStatus("整合完成");
  }

  async function generateReport() {
    setStatus("正在生成整合报告...");
    await api.generateReport();
    setStatus("整合报告已生成");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>学科知识整合智能体</h1>
          <p>{status}</p>
        </div>
        <div className="actions">
          <button onClick={parseLocal}>解析本地教材</button>
          <button onClick={buildOutlines}>整理层级</button>
          <button onClick={buildGraph}>构建图谱</button>
          <button onClick={runIntegration}>整合压缩</button>
          <button onClick={generateReport}>生成报告</button>
        </div>
      </header>

      <section className="workspace">
        <aside className="left-panel">
          <UploadPanel textbooks={textbooks} onUpload={uploadTextbooks} />
          <DecisionPanel decisions={decisions} summary={summary} />
        </aside>
        <GraphWorkspace graph={graph} />
        <QAWorkspace decisions={decisions} onDecisionUpdated={refresh} />
      </section>
    </main>
  );
}
