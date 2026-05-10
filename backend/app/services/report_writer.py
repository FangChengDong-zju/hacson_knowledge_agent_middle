from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..models import IntegrationDecision, IntegrationSummary, KnowledgeGraph, Textbook


def generate_integration_report(
    textbooks: list[Textbook],
    graph: KnowledgeGraph,
    decisions: list[IntegrationDecision],
    summary: IntegrationSummary,
) -> str:
    lines = [
        "# 整合报告",
        "",
        "## 整合概览",
        "",
        f"- 教材数量：{len(textbooks)}",
        f"- 原始总字数：{summary.original_chars}",
        f"- 整合后估算字数：{summary.integrated_chars}",
        f"- 压缩比：{summary.compression_ratio:.2%}",
        "",
        "## 整合决策摘要",
        "",
        f"- merge：{summary.merge_count}",
        f"- keep：{summary.keep_count}",
        f"- remove：{summary.remove_count}",
        "",
        "## 知识图谱统计",
        "",
        f"- 节点数：{len(graph.nodes)}",
        f"- 关系数：{len(graph.edges)}",
        "",
        "## 重点整合案例",
        "",
    ]
    for decision in decisions[:5]:
        lines.extend(
            [
                f"### {decision.decision_id} / {decision.action}",
                "",
                f"- 影响节点：{', '.join(decision.affected_nodes)}",
                f"- 理由：{decision.reason}",
                f"- 置信度：{decision.confidence}",
                "",
            ]
        )
    lines.extend(
        [
            "## 教学完整性说明",
            "",
            "本系统采用主干优先策略：核心定义、关键关系、学习顺序保留在整合主干中；案例、重复解释和细节内容降级为可追溯来源索引，并继续进入 RAG 检索范围，避免教学逻辑链路断裂。",
            "",
        ]
    )
    report = "\n".join(lines)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    (settings.report_dir / "整合报告.md").write_text(report, encoding="utf-8")
    return report


def report_path() -> Path:
    return settings.report_dir / "整合报告.md"

