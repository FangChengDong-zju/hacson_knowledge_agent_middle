import type { IntegrationDecision, IntegrationSummary } from "../types";

interface Props {
  decisions: IntegrationDecision[];
  summary: IntegrationSummary | null;
}

export default function DecisionPanel({ decisions, summary }: Props) {
  return (
    <section className="panel">
      <h2>整合索引</h2>
      {summary && (
        <div className="summary-grid">
          <span>原始字数</span>
          <strong>{summary.original_chars.toLocaleString()}</strong>
          <span>整合字数</span>
          <strong>{summary.integrated_chars.toLocaleString()}</strong>
          <span>压缩比</span>
          <strong>{(summary.compression_ratio * 100).toFixed(1)}%</strong>
        </div>
      )}
      <div className="decision-list">
        {decisions.slice(0, 8).map((decision) => (
          <article className={`decision ${decision.action}`} key={decision.decision_id}>
            <strong>{decision.action.toUpperCase()} · {decision.decision_id}</strong>
            <p>{decision.reason}</p>
          </article>
        ))}
        {decisions.length === 0 && <p className="muted">尚未生成整合决策。</p>}
      </div>
    </section>
  );
}

