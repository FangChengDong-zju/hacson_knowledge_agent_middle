from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEMO_DIR = DATA_DIR / "demo"
PROCESSED_DIR = DATA_DIR / "processed"
REPORT_DIR = PROJECT_ROOT / "report"


def read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def compact_text(value: object, limit: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text


def count_textbook_chunks(textbooks: list[dict], chunk_size: int = 760, overlap: int = 120) -> int:
    count = 0
    step = max(chunk_size - overlap, 200)
    for book in textbooks:
        for chapter in book.get("chapters", []):
            content = compact_text(chapter.get("content", ""))
            if len(content) < 120:
                continue
            for start in range(0, len(content), step):
                if len(content[start : start + chunk_size]) >= 120:
                    count += 1
    return count


def format_number(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def percent(value: float) -> str:
    return f"{value * 100:.4f}%"


def source_list(decision: dict) -> str:
    items = []
    for source in decision.get("affected_sources", []):
        items.append(f"{source.get('textbook')} {source.get('chapter')} p{source.get('page')}")
    return "；".join(items) if items else "无"


def render_action_table(action_counts: Counter) -> str:
    rows = ["| 决策类型 | 数量 | 说明 |", "|---|---:|---|"]
    notes = {
        "merge": "合并重复或高度相关的跨教材知识点",
        "keep": "保留独有但重要内容",
        "remove": "移出主干正文但保留来源索引",
        "split": "拆分被误合并的概念",
        "downgrade_detail": "案例、操作、长说明降级为索引",
        "keep_visual_index": "图表、流程图、结构图保留为视觉索引",
    }
    ordered = ["merge", "keep", "remove", "split", "downgrade_detail", "keep_visual_index"]
    for action in ordered:
        rows.append(f"| `{action}` | {action_counts.get(action, 0)} | {notes[action]} |")
    for action, count in sorted(action_counts.items()):
        if action not in ordered:
            rows.append(f"| `{action}` | {count} | 其他扩展决策类型 |")
    return "\n".join(rows)


def render_decision_cases(decisions: list[dict]) -> str:
    lines = []
    for index, decision in enumerate(decisions[:5], start=1):
        common_points = [
            item.get("point", str(item)) if isinstance(item, dict) else str(item)
            for item in decision.get("common_points", [])
        ]
        complementary_points = [
            item.get("point", str(item)) if isinstance(item, dict) else str(item)
            for item in decision.get("complementary_points", [])
        ]
        detail_index = [
            f"{item.get('keyword')}（{item.get('source')}）"
            for item in decision.get("detail_index", [])
            if isinstance(item, dict)
        ]
        visual_refs = [
            f"{item.get('label')}（{item.get('source')}）"
            for item in decision.get("visual_refs", [])
            if isinstance(item, dict)
        ]
        lines.extend(
            [
                f"### 案例 {index}：{decision.get('target_concept')}（{decision.get('decision_id')}）",
                "",
                f"- 决策动作：`{decision.get('action')}`",
                f"- 理由类型：{decision.get('reason_type')}",
                f"- 来源：{source_list(decision)}",
                f"- 共同点：{compact_text('；'.join(common_points) or '无')}",
                f"- 互补点：{compact_text('；'.join(complementary_points) or '无')}",
                f"- 整合后主干：{compact_text(decision.get('integrated_text'))}",
                f"- 整合理由：{compact_text(decision.get('reason'))}",
                f"- 细节索引：{compact_text('；'.join(detail_index) or '无')}",
                f"- 图表索引：{compact_text('；'.join(visual_refs) or '无')}",
                f"- 教学完整性说明：{compact_text(decision.get('teaching_integrity_note'))}",
                "",
            ]
        )
    return "\n".join(lines)


def render_report() -> str:
    parse_summary = read_json(PROCESSED_DIR / "parse_summary.json", {})
    graph_summary = read_json(DEMO_DIR / "graph_summary.json", {})
    decisions: list[dict] = read_json(DEMO_DIR / "integration_decisions_demo.json", [])
    corpus: dict = read_json(DEMO_DIR / "integrated_corpus_demo.json", {})
    decision_graph: dict = read_json(DEMO_DIR / "decision_graph_demo.json", {"nodes": [], "edges": []})
    audit: dict = read_json(DEMO_DIR / "integration_audit_demo.json", {})
    textbooks: list[dict] = read_json(PROCESSED_DIR / "textbooks.json", [])

    totals = parse_summary.get("totals", {})
    books = parse_summary.get("books", [])
    original_chars = int(corpus.get("original_chars") or totals.get("chars") or audit.get("original_chars") or 0)
    target_chars = int(corpus.get("target_chars") or original_chars * 0.3)
    integrated_chars = int(corpus.get("integrated_chars") or audit.get("integrated_chars") or 0)
    compression_ratio = float(corpus.get("compression_ratio") or (integrated_chars / original_chars if original_chars else 0))
    action_counts = Counter(decision.get("action", "unknown") for decision in decisions)
    reason_counts = Counter(decision.get("reason_type", "unknown") for decision in decisions)
    core_count = sum(1 for decision in decisions if decision.get("counts_in_core"))
    index_count = len(decisions) - core_count
    visual_ref_count = sum(len(decision.get("visual_refs", [])) for decision in decisions)
    detail_ref_count = sum(len(decision.get("detail_index", [])) for decision in decisions)
    rag_chunk_count = count_textbook_chunks(textbooks)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_format_note = (
        "赛题基础要求为 `report/整合报告.md`，即 Markdown 文件。"
        "PDF 导出属于后续 P2/体验增强项，本报告先按官方基础格式生成。"
    )

    book_rows = ["| 教材 | 页数 | 章节/知识段 | 原始字符 | 入库字符 |", "|---|---:|---:|---:|---:|"]
    for book in books:
        book_rows.append(
            "| {title} | {pages} | {chapters} | {chars} | {stored} |".format(
                title=book.get("title"),
                pages=format_number(book.get("total_pages")),
                chapters=format_number(book.get("chapter_count")),
                chars=format_number(book.get("total_chars")),
                stored=format_number(book.get("stored_content_chars")),
            )
        )

    reason_rows = ["| 理由类型 | 数量 |", "|---|---:|"]
    for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])):
        reason_rows.append(f"| {reason} | {count} |")

    graph_before_nodes = graph_summary.get("node_count", audit.get("source_graph_nodes", 0))
    graph_before_edges = graph_summary.get("edge_count", audit.get("source_graph_edges", 0))
    graph_after_nodes = len(decision_graph.get("nodes", []))
    graph_after_edges = len(decision_graph.get("edges", []))

    sections = corpus.get("sections", [])
    section_lines = []
    for section in sections:
        section_lines.extend(
            [
                f"### {section.get('section_title')}",
                "",
                compact_text(section.get("core_text")),
                "",
                f"- 关联决策：{', '.join(section.get('decision_ids', []))}",
                f"- 来源：{'；'.join(section.get('source_refs', []))}",
                "",
            ]
        )

    lines = [
        "# 学科知识整合智能体：7 本医学教材整合报告",
        "",
        f"- 生成时间：{generated_at}",
        "- 报告文件：`report/整合报告.md`",
        f"- 格式核查：{report_format_note}",
        "- 报告口径：以赛方 7 本医学教材和当前 demo 整合决策为例，展示可审计的整合闭环。",
        "",
        "## 1. 整合概览",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 教材数量 | {format_number(totals.get('parsed_books', len(books)))} |",
        f"| 总页数 | {format_number(totals.get('pages'))} |",
        f"| 章节/知识段 | {format_number(totals.get('chapters'))} |",
        f"| 原始可用字符数 | {format_number(original_chars)} |",
        f"| 目标上限（30%） | {format_number(target_chars)} |",
        f"| 当前凝练主干字符数 | {format_number(integrated_chars)} |",
        f"| 当前压缩比 | {percent(compression_ratio)} |",
        f"| 教材 RAG chunk | {format_number(rag_chunk_count)} |",
        "",
        "说明：当前体验版采用“主干正文 + 细节索引 + 图表索引”的压缩方式。"
        "被降级内容不消失，而是通过原文页码、关键词和 RAG chunk 保持可追溯。",
        "",
        "### 1.1 教材解析清单",
        "",
        "\n".join(book_rows),
        "",
        "## 2. 整合决策摘要",
        "",
        render_action_table(action_counts),
        "",
        "### 2.1 理由类型分布",
        "",
        "\n".join(reason_rows),
        "",
        f"- 进入主干的决策数：{core_count}",
        f"- 降级为索引/图表的决策数：{index_count}",
        f"- 细节索引条目数：{detail_ref_count}",
        f"- 图表索引条目数：{visual_ref_count}",
        "",
        "## 3. 知识图谱统计",
        "",
        "| 图谱阶段 | 节点数 | 关系数 | 说明 |",
        "|---|---:|---:|---|",
        f"| 候选关键词图谱 | {format_number(graph_before_nodes)} | {format_number(graph_before_edges)} | 从教材 outline 和多级关键词生成，用于候选概念发现 |",
        f"| 整合决策图谱 | {format_number(graph_after_nodes)} | {format_number(graph_after_edges)} | 从 integration_decisions 生成，用于展示合并理由、共同点、互补点和来源教材 |",
        "",
        f"- 候选图谱图表索引数：{format_number(graph_summary.get('visual_ref_count', 0))}",
        "- 设计取舍：候选图谱负责发现概念和跨书关联，最终图谱以整合决策为准，保证每个节点和边都有可解释理由。",
        "",
        "## 4. 30% 凝练版教材主干",
        "",
        "\n".join(section_lines) if section_lines else "暂无凝练章节。",
        "",
        "## 5. 重点整合案例",
        "",
        render_decision_cases(decisions),
        "## 6. 教学完整性说明",
        "",
        "本系统的压缩策略不是删除教材，而是将内容分层：",
        "",
        "- 主干层：定义、分类、机制、因果关系、学习顺序、必要方法。",
        "- 细节索引层：病例、长篇解释、操作步骤、计算过程和扩展阅读，保留关键词与来源页码。",
        "- 图表索引层：结构图、机制图、流程图和表格不参与文本去重，统一汇总为 visual_refs。",
        "- RAG 原文层：7 本教材已生成可检索 chunk，Case A 问答可返回教材名、章节、页码和原文片段。",
        "",
        "当前 demo 保留三条教学主干链路：",
        "",
        "1. 结构-功能链路：以甲状腺为例，整合局部解剖学的结构/毗邻/血供与生理学的激素/代谢调节。",
        "2. 损伤-反应-修复链路：以炎症为例，整合病理学的形态表现与病理生理学的全身反应。",
        "3. 病原-宿主链路：以感染与免疫应答为例，整合医学微生物学的机制基础与传染病学的传播、防治和临床管理。",
        "",
        "因此，即使主干正文被压缩，教师和学生仍可通过细节索引、图表索引和 RAG chunk 回到原教材证据，教学逻辑链路不断裂。",
        "",
        "## 7. 教师反馈与迭代机制",
        "",
        "系统提供 Case B：教师反馈整合入口。教师可以通过自然语言提出个性化要求，例如保留某个病例、拆分某个概念、降低某类细节权重。系统会生成 `decision_overrides`，并在当前会话中同步影响：",
        "",
        "- 整合决策列表。",
        "- 30% 凝练版中的调整说明。",
        "- 最终决策图谱中的教师反馈节点和高亮边。",
        "- 后续发送给 LLM 的整合提示词。",
        "",
        "提示词优先级为：教师写入要求 > Agent 默认整合策略；结构化输出、来源追溯和不得编造证据仍是硬约束。",
        "",
        "## 8. RAG 问答与来源引用",
        "",
        "系统提供 Case A：基于已整合资料的信息查询入口。查询顺序为：",
        "",
        "1. 先查 Case B 已整合资料。",
        "2. 整合资料不足时，检索 7 本教材原文 chunk。",
        "3. 教材也不足时，才进入 LLM/联网检索路径。",
        "",
        "教材 RAG 命中时，回答必须展示教材名、章节、页码和原文片段。未填写 API Key 时，系统不会编造答案，而是返回可追溯原文片段；填写 API Key 后，LLM 被要求只基于命中的教材片段组织答案。",
        "",
        "## 9. 当前局限与下一步",
        "",
        "- 当前整合决策仍以 demo 决策展示 LLM 工作流，后续应将真实 7 本教材分批送入 LLM 生成完整 integration_decisions。",
        "- 当前 RAG 为关键词检索，可继续增强为 BM25 + 向量检索 + rerank。",
        "- 当前图谱为 SVG/Streamlit demo，后续可恢复 Cytoscape 交互以支持点击、筛选、拖拽和多视图切换。",
        "- 当前报告为 Markdown 基础格式，PDF 导出可作为 P2 加分项。",
        "",
        "## 10. 证据文件索引",
        "",
        "- 教材解析验证：`report/local_textbook_loop_check.md`",
        "- 教材解析摘要：`data/processed/parse_summary.json`",
        "- 候选图谱数据：`data/demo/graph_demo.json`",
        "- 候选图谱快照：`report/knowledge_graph_demo.html`、`report/knowledge_graph_snapshot.svg`",
        "- 整合决策：`data/demo/integration_decisions_demo.json`",
        "- 凝练教材：`data/demo/integrated_corpus_demo.json`、`report/integrated_corpus_demo.md`",
        "- 决策图谱：`data/demo/decision_graph_demo.json`",
        "- LLM 提示词设计：`docs/LLM整合提示词设计.md`",
        "- Streamlit 体验页：`streamlit_app.py`",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    report = render_report()
    target = REPORT_DIR / "整合报告.md"
    write_text(target, report)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
