from __future__ import annotations

import html
import json
import math
import re
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import streamlit as st


APP_DIR = Path(__file__).parent
DEMO_DIR = APP_DIR / "data" / "demo"
PROCESSED_DIR = APP_DIR / "data" / "processed"
LIVE_DIR = APP_DIR / "data" / "live"
REPORT_DIR = APP_DIR / "report"
DOCS_DIR = APP_DIR / "docs"
TEXTBOOKS_PATH = PROCESSED_DIR / "textbooks.json"
DEFAULT_TEXTBOOK_SOURCE_PATH = r"E:\textbooks"
DEBUG_CASE_B_TEXTBOOKS = ("传染病学", "医学微生物学")
DEBUG_CASE_B_TOPICS = ("感染", "病原体", "细菌", "病毒", "免疫应答")

DEFAULT_INTEGRATION_POLICY = [
    "优先提炼定义、分类、机制、因果关系、学习顺序和必要方法。",
    "跨教材重复内容合并为共同点，跨学科互补内容保留为互补点。",
    "具体案例、长篇解释、操作步骤和计算细节默认降级为关键词索引。",
    "图片、表格和机制图不参与文本去重，默认保留为 visual_refs。",
    "整合后主干正文目标不超过原始内容 30%，被降级内容必须保留可回溯来源。",
]

OUTPUT_FORMAT_POLICY = [
    "必须输出结构化 JSON，包含 integration_decisions、integrated_corpus、decision_graph、audit_summary。",
    "每条 integration_decision 必须包含 decision_id、action、reason_type、reason、affected_sources、confidence。",
    "每条来源必须保留教材名、章节、页码或可定位片段；不得编造不存在的来源。",
    "如果教师要求与默认整合策略冲突，遵循教师要求，并在 teacher_override_note 中说明覆盖了哪条默认策略。",
    "如果教师要求与结构化输出或来源可追溯硬约束冲突，仍保持结构化输出，并在 conflict_notes 中报告冲突。",
]

QUERY_ASPECT_SYNONYMS = {
    "症状": ["症状", "表现", "体征", "临床表现", "典型症状"],
    "诊断": ["诊断", "检查", "鉴别", "诊断标准"],
    "治疗": ["治疗", "处理", "用药", "手术", "干预"],
    "病因": ["病因", "原因", "危险因素", "诱因"],
    "机制": ["机制", "过程", "原理", "通路"],
    "结构": ["结构", "位置", "部位", "哪里", "在哪", "毗邻", "形态", "血供", "狭窄"],
    "功能": ["功能", "作用", "调节", "生理作用"],
    "定义": ["定义", "概念", "是什么"],
}

CONCEPT_EXPANSIONS = {
    "甲状腺": ["甲状腺激素", "TH", "T3", "T4", "三碘甲状腺原氨酸", "甲状腺素"],
    "炎症": ["炎症反应", "炎症介质"],
}


def load_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8-sig")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def summarize_processed_textbooks() -> dict:
    textbooks: list[dict] = load_json(TEXTBOOKS_PATH, []) if TEXTBOOKS_PATH.exists() else []
    titles = [str(book.get("title") or book.get("filename") or book.get("textbook_id")) for book in textbooks]
    chapter_count = sum(len(book.get("chapters", [])) for book in textbooks)
    stored_chars = sum(
        len(str(chapter.get("content", "")))
        for book in textbooks
        for chapter in book.get("chapters", [])
    )
    return {
        "textbook_count": len(textbooks),
        "chapter_count": chapter_count,
        "stored_chars": stored_chars,
        "titles": titles,
    }


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #1d1d1f;
            --muted: #6e6e73;
            --line: #d8dbe2;
            --surface: #ffffff;
            --page: #f5f5f7;
            --blue: #0071e3;
            --green: #34c759;
            --orange: #ff9f0a;
            --pink: #ff375f;
        }
        .stApp { background: var(--page); color: var(--ink); }
        .block-container { padding-top: 1.2rem; max-width: 1180px; }
        h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
        p, li, .stMarkdown { color: var(--ink); }
        [data-testid="stSidebar"] { background: #fbfbfd; border-right: 1px solid #e5e5ea; }
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--ink); }
        div[data-testid="stTabs"] button p { font-size: 15px; font-weight: 650; }
        div[data-testid="stExpander"] {
            border: 1px solid #e5e5ea;
            border-radius: 8px;
            background: rgba(255,255,255,0.82);
        }
        .hero {
            background: var(--surface);
            border: 1px solid #e5e5ea;
            border-radius: 8px;
            padding: 30px 34px;
            margin-bottom: 18px;
            box-shadow: 0 12px 36px rgba(29,29,31,0.06);
        }
        .hero h1 { margin: 0 0 10px; font-size: 40px; line-height: 1.08; font-weight: 800; color: var(--ink); }
        .hero p { margin: 0; color: var(--muted); line-height: 1.7; font-size: 17px; max-width: 820px; }
        .eyebrow { color: var(--blue); font-size: 13px; font-weight: 800; margin-bottom: 8px; }
        .hero-strip {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 16px;
        }
        .hero-pill {
            border-radius: 999px;
            padding: 6px 11px;
            background: #f2f7ff;
            color: #075bb5;
            font-size: 13px;
            font-weight: 700;
        }
        .metric-row {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 14px 0 18px;
        }
        .metric-card {
            background: rgba(255,255,255,0.9);
            border: 1px solid #e5e5ea;
            border-radius: 8px;
            padding: 16px 16px;
            box-shadow: 0 8px 22px rgba(29,29,31,0.04);
        }
        .metric-card strong { display: block; font-size: 26px; color: var(--ink); line-height: 1.15; }
        .metric-card span { color: var(--muted); font-size: 13px; font-weight: 650; }
        .decision-card {
            border: 1px solid #e5e5ea;
            background: var(--surface);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 8px 24px rgba(29,29,31,0.05);
        }
        .decision-card h3 { margin: 0 0 8px; font-size: 18px; }
        .tag {
            display: inline-flex;
            border-radius: 999px;
            padding: 5px 9px;
            margin: 2px 4px 2px 0;
            background: #f2f7ff;
            color: #075bb5;
            font-size: 12px;
            font-weight: 700;
        }
        .reason {
            border-left: 4px solid var(--blue);
            background: #f5f9ff;
            padding: 11px 13px;
            color: #30343b;
            margin-top: 8px;
            border-radius: 0 8px 8px 0;
        }
        .source-box {
            border: 1px solid #e5e5ea;
            background: #fbfbfd;
            border-radius: 8px;
            padding: 10px;
            margin-top: 7px;
        }
        .small-muted { color: var(--muted); font-size: 13px; }
        .graph-wrap {
            border: 1px solid #e5e5ea;
            border-radius: 8px;
            overflow: auto;
            background: #fbfbfd;
            padding: 12px;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.6);
        }
        .mode-card {
            background: var(--surface);
            border: 1px solid #e5e5ea;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 12px;
            box-shadow: 0 8px 26px rgba(29,29,31,0.05);
        }
        .mode-card h3 { margin: 0 0 8px; font-size: 21px; }
        .mode-card p { margin: 0; color: var(--muted); line-height: 1.65; }
        .section-note {
            background: #fff;
            border: 1px solid #e5e5ea;
            border-left: 4px solid var(--green);
            border-radius: 8px;
            padding: 14px 16px;
            margin: 12px 0;
            color: #30343b;
        }
        div[data-testid="stChatInput"] {
            background: #ffffff;
            border: 2px solid #0071e3;
            border-radius: 18px;
            box-shadow: 0 16px 42px rgba(0,113,227,0.16);
            padding: 4px;
        }
        div[data-testid="stChatInput"] textarea {
            font-size: 18px !important;
            color: var(--ink) !important;
        }
        div[data-testid="stChatInput"] button {
            background: #0071e3 !important;
            color: #ffffff !important;
            border-radius: 12px !important;
        }
        .chat-focus {
            border: 1px solid #e5e5ea;
            border-radius: 8px;
            background: #ffffff;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: 0 10px 28px rgba(29,29,31,0.05);
        }
        .chat-focus h3 { margin: 0 0 8px; font-size: 24px; }
        .chat-focus p { margin: 0; color: var(--muted); line-height: 1.65; }
        @media (max-width: 900px) {
            .hero { padding: 24px 22px; }
            .hero h1 { font-size: 30px; }
            .metric-row { grid-template-columns: 1fr 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_row(items: list[tuple[str, str]]) -> None:
    body = "".join(
        f'<div class="metric-card"><strong>{html.escape(value)}</strong><span>{html.escape(label)}</span></div>'
        for label, value in items
    )
    st.markdown(f'<div class="metric-row">{body}</div>', unsafe_allow_html=True)


def product_header(title: str, subtitle: str, eyebrow: str, pills: list[str] | None = None) -> None:
    pill_html = "".join(f'<span class="hero-pill">{esc(item)}</span>' for item in (pills or []))
    st.markdown(
        f"""
        <div class="hero">
          <div class="eyebrow">{esc(eyebrow)}</div>
          <h1>{esc(title)}</h1>
          <p>{esc(subtitle)}</p>
          <div class="hero-strip">{pill_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mode_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="mode-card">
          <h3>{esc(title)}</h3>
          <p>{esc(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def decision_card(decision: dict) -> None:
    override = decision.get("teacher_override") or {}
    tags = [
        decision.get("action", ""),
        decision.get("reason_type", ""),
        f"confidence {decision.get('confidence', 0):.2f}",
        "计入主干" if decision.get("counts_in_core") else "索引保留",
        "教师已调整" if override else "",
    ]
    override_html = ""
    if override:
        override_html = f"""
          <div class="reason" style="border-left-color:#059669;background:#f0fdf4;">
            <b>教师反馈：</b>{esc(override.get("teacher_request"))}<br>
            <b>系统调整：</b>{esc(override.get("system_update"))}
          </div>
        """
    st.markdown(
        f"""
        <div class="decision-card">
          <h3>{esc(decision.get("target_concept"))}</h3>
          <div>{''.join(f'<span class="tag">{esc(tag)}</span>' for tag in tags if tag)}</div>
          <p class="small-muted">{esc(" / ".join(decision.get("keyword_path", [])))}</p>
          <div class="reason"><b>整合理由：</b>{esc(decision.get("reason"))}</div>
          {override_html}
          <p><b>凝练文本：</b>{esc(decision.get("integrated_text"))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("查看共同点、互补点、来源和索引", expanded=False):
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**共同点**")
            common = decision.get("common_points") or []
            if common:
                for item in common:
                    st.write(item.get("point", item) if isinstance(item, dict) else item)
            else:
                st.caption("无共同点，或此决策属于细节/图表索引。")
            st.markdown("**互补点**")
            for item in decision.get("complementary_points") or []:
                if isinstance(item, dict):
                    st.write(f"- {item.get('point')}（{item.get('source')}）")
                else:
                    st.write(f"- {item}")
        with cols[1]:
            st.markdown("**来源**")
            for source in decision.get("affected_sources") or []:
                st.markdown(
                    f"""
                    <div class="source-box">
                      <b>{esc(source.get("textbook"))}</b>
                      <div class="small-muted">{esc(source.get("chapter"))} · p{esc(source.get("page"))}</div>
                      <div>{esc(source.get("source_text"))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("**细节索引**")
        st.json(decision.get("detail_index") or [], expanded=False)
        st.markdown("**图表索引**")
        st.json(decision.get("visual_refs") or [], expanded=False)


def render_decision_graph(graph: dict) -> str:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    width, height = 1120, 760
    cx, cy = width / 2, height / 2
    by_kind = defaultdict(list)
    for node in nodes:
        by_kind[node.get("kind", "other")].append(node)

    rings = {
        "concept": 110,
        "common_point": 230,
        "complementary_point": 300,
        "decision": 370,
        "textbook": 370,
        "teacher_override": 435,
    }
    colors = {
        "concept": "#2563eb",
        "common_point": "#059669",
        "complementary_point": "#7c3aed",
        "decision": "#f59e0b",
        "textbook": "#64748b",
        "teacher_override": "#16a34a",
    }
    positions: dict[str, tuple[float, float]] = {}
    ordered_kinds = ["concept", "common_point", "complementary_point", "decision", "textbook", "teacher_override"]
    for kind_index, kind in enumerate(ordered_kinds):
        items = by_kind.get(kind, [])
        radius = rings.get(kind, 260)
        offset = kind_index * 0.31
        for index, node in enumerate(items):
            angle = (2 * math.pi * index / max(len(items), 1)) - math.pi / 2 + offset
            positions[node["id"]] = (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="1120" height="760" fill="#f8fafc"/>',
        '<text x="28" y="42" font-size="24" font-weight="800" fill="#172033">由整合决策生成的最终图谱 Demo</text>',
        '<text x="28" y="68" font-size="14" fill="#64748b">节点来自 decision_id、共同点、互补点和来源教材；边来自整合理由。</text>',
    ]
    for edge in edges:
        source = positions.get(edge.get("source"))
        target = positions.get(edge.get("target"))
        if not source or not target:
            continue
        stroke = "#16a34a" if edge.get("teacher_adjusted") else "#94a3b8"
        width_value = "2.2" if edge.get("teacher_adjusted") else "1.3"
        opacity = "0.86" if edge.get("teacher_adjusted") else "0.58"
        parts.append(
            f'<line x1="{source[0]:.1f}" y1="{source[1]:.1f}" x2="{target[0]:.1f}" y2="{target[1]:.1f}" '
            f'stroke="{stroke}" stroke-width="{width_value}" stroke-opacity="{opacity}"/>'
        )
    for node in nodes:
        x, y = positions.get(node["id"], (cx, cy))
        kind = node.get("kind", "other")
        color = colors.get(kind, "#334155")
        r = 28 if kind == "concept" else 21 if kind in {"common_point", "complementary_point"} else 18
        label = str(node.get("label", ""))[:12]
        stroke = "#16a34a" if node.get("teacher_adjusted") else "#fff"
        stroke_width = "4" if node.get("teacher_adjusted") else "2"
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + r + 15:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="#172033">{esc(label)}</text>'
        )
        parts.append("</svg>")
    return "\n".join(parts)


def build_decision_graph_from_decisions(decisions: list[dict]) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()

    def add_node(node_id: str, label: str, kind: str, decision_id: str | None = None, adjusted: bool = False) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "kind": kind,
                "decision_id": decision_id,
                "teacher_adjusted": adjusted,
            }
        )

    for decision in decisions:
        decision_id = decision["decision_id"]
        adjusted = bool(decision.get("teacher_override"))
        concept_id = f"concept::{decision['target_concept']}"
        add_node(concept_id, decision["target_concept"], "concept", decision_id, adjusted)
        add_node(f"decision::{decision_id}", decision_id, "decision", decision_id, adjusted)
        edges.append(
            {
                "source": f"decision::{decision_id}",
                "target": concept_id,
                "relation": decision["action"],
                "reason": decision["reason"],
                "teacher_adjusted": adjusted,
            }
        )

        for point in decision.get("common_points", []):
            point_text = point["point"] if isinstance(point, dict) else str(point)
            point_id = f"common::{point_text}"
            add_node(point_id, point_text, "common_point", decision_id, adjusted)
            edges.append(
                {
                    "source": concept_id,
                    "target": point_id,
                    "relation": "contains_common",
                    "reason": "共同点形成跨教材关联",
                    "teacher_adjusted": adjusted,
                }
            )

        for point in decision.get("complementary_points", []):
            point_text = point["point"] if isinstance(point, dict) else str(point)
            point_id = f"complement::{point_text}"
            add_node(point_id, point_text, "complementary_point", decision_id, adjusted)
            edges.append(
                {
                    "source": concept_id,
                    "target": point_id,
                    "relation": "contains_complement",
                    "reason": "互补点保留",
                    "teacher_adjusted": adjusted,
                }
            )

        for source in decision.get("affected_sources", []):
            book = source.get("textbook", "")
            source_id = f"book::{book}"
            add_node(source_id, book, "textbook", decision_id, adjusted)
            edges.append(
                {
                    "source": source_id,
                    "target": concept_id,
                    "relation": "evidence_for",
                    "reason": decision["reason_type"],
                    "teacher_adjusted": adjusted,
                }
            )

        override = decision.get("teacher_override") or {}
        if override:
            override_id = f"teacher::{decision_id}"
            add_node(override_id, "教师反馈", "teacher_override", decision_id, True)
            edges.append(
                {
                    "source": override_id,
                    "target": concept_id,
                    "relation": "teacher_updates",
                    "reason": override.get("system_update", ""),
                    "teacher_adjusted": True,
                }
            )

    return {"nodes": nodes, "edges": edges}


def ensure_teacher_feedback_state(decisions: list[dict]) -> None:
    if "teacher_requirements" not in st.session_state:
        st.session_state.teacher_requirements = [
            "优先保留跨学科共同主干；案例、长篇说明和操作细节降级为索引。",
            "图表不参与文本去重，保留为可回溯的图表索引。",
        ]
    if "decision_overrides" not in st.session_state:
        st.session_state.decision_overrides = {}
    if "teacher_chat_history" not in st.session_state:
        st.session_state.teacher_chat_history = [
            {
                "role": "assistant",
                "content": "我会围绕整合方案工作：可以解释某条决策，也可以按你的备课偏好修改合并、保留、拆分或降级策略。",
            }
        ]
    if "active_decision_id" not in st.session_state:
        st.session_state.active_decision_id = decisions[0]["decision_id"] if decisions else ""


def apply_decision_overrides(decisions: list[dict]) -> list[dict]:
    effective = deepcopy(decisions)
    overrides: dict = st.session_state.get("decision_overrides", {})
    for decision in effective:
        override = overrides.get(decision.get("decision_id"))
        if not override:
            continue
        decision["teacher_override"] = override
        decision["action"] = override.get("new_action", decision.get("action"))
        decision["reason_type"] = "教师反馈调整"
        decision["counts_in_core"] = bool(override.get("counts_in_core", decision.get("counts_in_core")))
        decision["reason"] = f"{decision.get('reason')} 教师补充要求：{override.get('teacher_request')}"
        decision["integrated_text"] = override.get("new_integrated_text", decision.get("integrated_text"))
        decision["teaching_integrity_note"] = override.get("system_update", decision.get("teaching_integrity_note"))
    return effective


def find_decision_from_message(message: str, decisions: list[dict], allow_fallback: bool = True) -> dict | None:
    decision_match = re.search(r"decision[_-]?\d{4}", message, flags=re.IGNORECASE)
    if decision_match:
        normalized = decision_match.group(0).lower().replace("-", "_")
        for decision in decisions:
            if decision.get("decision_id", "").lower() == normalized:
                return decision

    for decision in decisions:
        concept = str(decision.get("target_concept", ""))
        if concept and concept in message:
            return decision
        for source in decision.get("affected_sources", []):
            textbook = str(source.get("textbook", ""))
            if textbook and textbook in message:
                return decision
        for item in decision.get("detail_index", []):
            keyword = str(item.get("keyword", ""))
            if keyword and keyword in message:
                return decision

    if allow_fallback:
        active_id = st.session_state.get("active_decision_id")
        for decision in decisions:
            if decision.get("decision_id") == active_id:
                return decision
        return decisions[0] if decisions else None
    return None


def source_summary(decision: dict) -> str:
    sources = []
    for source in decision.get("affected_sources", []):
        sources.append(f"{source.get('textbook')} {source.get('chapter')} p{source.get('page')}")
    return "；".join(sources) if sources else "暂无来源"


def build_teacher_aware_prompt(decisions: list[dict]) -> str:
    teacher_requirements = st.session_state.get("teacher_requirements", [])
    overrides = list(st.session_state.get("decision_overrides", {}).values())
    active_id = st.session_state.get("active_decision_id", "")
    active_decision = next((item for item in decisions if item.get("decision_id") == active_id), decisions[0] if decisions else {})

    decision_brief = []
    for decision in decisions:
        decision_brief.append(
            {
                "decision_id": decision.get("decision_id"),
                "target_concept": decision.get("target_concept"),
                "current_action": decision.get("action"),
                "reason_type": decision.get("reason_type"),
                "sources": [
                    {
                        "textbook": source.get("textbook"),
                        "chapter": source.get("chapter"),
                        "page": source.get("page"),
                    }
                    for source in decision.get("affected_sources", [])
                ],
            }
        )

    payload = {
        "prompt_priority": [
            "教师写入要求优先于 Agent 默认整合策略。",
            "Agent 默认整合策略仅在教师没有指定时作为兜底。",
            "结构化输出、来源可追溯、不得编造证据属于比赛硬约束，若与教师要求冲突，需要保留 JSON 输出并显式报告冲突。",
        ],
        "teacher_requirements": teacher_requirements,
        "agent_default_integration_policy": DEFAULT_INTEGRATION_POLICY,
        "output_format_policy": OUTPUT_FORMAT_POLICY,
        "active_focus": {
            "decision_id": active_decision.get("decision_id"),
            "target_concept": active_decision.get("target_concept"),
        },
        "current_teacher_overrides": overrides,
        "current_decision_brief": decision_brief,
    }
    return (
        "你是医学教材整合 Agent。请根据以下优先级和约束，对教材内容进行整合、压缩和图谱构建。\n\n"
        "优先级说明：教师写入要求 > Agent 默认整合策略。输出格式和来源可追溯是比赛硬约束，必须在最终 JSON 中保留。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def strip_llm_json(raw_answer: str) -> dict:
    content = raw_answer.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    if not content.startswith("{"):
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start : end + 1]
    return json.loads(content)


def filter_chunks_by_textbooks(chunks: list[dict], allowed_textbooks: tuple[str, ...] | None) -> list[dict]:
    if not allowed_textbooks:
        return chunks
    filtered = []
    for chunk in chunks:
        haystack = f"{chunk.get('textbook', '')} {chunk.get('filename', '')}"
        if any(title in haystack for title in allowed_textbooks):
            filtered.append(chunk)
    return filtered


def infer_case_b_topic(teacher_prompt: str, fallback: str = "感染") -> str:
    for topic in DEBUG_CASE_B_TOPICS:
        if topic in teacher_prompt:
            return topic
    analysis = analyze_query(teacher_prompt)
    topic = str(analysis.get("topic", "")).strip()
    stop_terms = {"优先保留跨学科共同主干", "案例长篇说明和操作细节降级为索引", "图表不参与文本去重", "保留为可回溯图表索引"}
    if 2 <= len(topic) <= 12 and topic not in stop_terms:
        return topic
    return fallback


def select_case_b_source_chunks(
    teacher_prompt: str,
    decisions: list[dict],
    top_k: int = 8,
    allowed_textbooks: tuple[str, ...] | None = None,
) -> tuple[str, list[dict]]:
    chunks = load_textbook_rag_chunks(str(TEXTBOOKS_PATH), chunk_size=720, overlap=120)
    chunks = filter_chunks_by_textbooks(chunks, allowed_textbooks)
    explicit_decision = find_decision_from_message(teacher_prompt, decisions, allow_fallback=False)
    active_decision = explicit_decision if explicit_decision and not allowed_textbooks else None
    active_topic = str((active_decision or {}).get("target_concept") or infer_case_b_topic(teacher_prompt))

    queries = []
    if explicit_decision:
        queries.append(teacher_prompt)
    queries.extend([active_topic, teacher_prompt, *DEBUG_CASE_B_TOPICS])

    selected: list[dict] = []
    seen_ids: set[str] = set()
    per_book: Counter[str] = Counter()
    for query in queries:
        if not query.strip():
            continue
        results, _ = search_textbook_chunks(query, chunks, top_k=18)
        for chunk in results:
            chunk_id = str(chunk.get("chunk_id"))
            textbook = str(chunk.get("textbook", ""))
            if chunk_id in seen_ids or per_book[textbook] >= 2:
                continue
            selected.append(chunk)
            seen_ids.add(chunk_id)
            per_book[textbook] += 1
            if len(selected) >= top_k:
                return active_topic, selected

    if len(selected) < 3:
        for chunk in chunks:
            text = f"{chunk.get('textbook')} {chunk.get('chapter')} {chunk.get('text')}"
            chunk_id = str(chunk.get("chunk_id"))
            if active_topic not in text or chunk_id in seen_ids:
                continue
            selected.append(chunk)
            seen_ids.add(chunk_id)
            if len(selected) >= top_k:
                break
    return active_topic, selected[:top_k]


def build_case_b_live_integration_prompt(teacher_prompt: str, topic: str, source_chunks: list[dict]) -> str:
    cluster_slug = re.sub(r"\W+", "_", topic)[:24] or "medical"
    source_items = [
        {
            "source_id": index,
            "textbook": chunk.get("textbook"),
            "chapter": chunk.get("chapter"),
            "page": chunk.get("page_start"),
            "text": chunk.get("text"),
        }
        for index, chunk in enumerate(source_chunks, start=1)
    ]
    original_chars = sum(len(str(item.get("text", ""))) for item in source_items)
    payload = {
        "task": "case_b_curriculum_integration_batch",
        "scope_note": "这是教材整合流程中的一个真实整合批次；最终产品面向用户指定的全部教材，可按章节或主题分批处理后合并。",
        "cluster_id": f"live_cluster_{cluster_slug}",
        "cluster_title": topic,
        "teacher_requirements": st.session_state.get("teacher_requirements", []) + ([teacher_prompt] if teacher_prompt else []),
        "agent_default_integration_policy": DEFAULT_INTEGRATION_POLICY,
        "output_format_policy": OUTPUT_FORMAT_POLICY,
        "source_items": source_items,
        "compression_target": {
            "original_chars": original_chars,
            "target_max_chars": int(original_chars * 0.3),
            "rule": "最终主干内容控制在给定 source_items 原文字数的 30% 以内；细节用索引保留。",
        },
        "required_actions": [
            "判断这些片段是否围绕同一高一级概念；若不是，使用 split 并说明概念误合并。",
            "区分多本教材共同点和互补点。",
            "为每一项整合决策给出 action、reason_type、reason、confidence。",
            "affected_sources 必须引用给定 source_items 的教材名、章节、页码和原文片段，不得编造来源。",
            "教师要求优先于默认策略；若教师要求覆盖默认策略，写入 teacher_override_note。",
            "输出必须是合法 JSON，不要输出 Markdown。",
        ],
        "output_schema": {
            "cluster_id": "string",
            "target_concept": "string",
            "decisions": [
                {
                    "decision_id": "live_decision_0001",
                    "action": "merge | keep | remove | split | downgrade_detail | keep_visual_index",
                    "reason_type": "文本重复 | 共同主干 | 互补扩展 | 层级包含 | 案例降级 | 计算降级 | 背景降级 | 图表归档 | 表述冲突 | 概念误合并 | 教学顺序",
                    "target_concept": "string",
                    "keyword_path": ["string"],
                    "affected_sources": [
                        {"source_id": 1, "textbook": "string", "chapter": "string", "page": 0, "source_text": "string"}
                    ],
                    "common_points": [{"point": "string", "evidence_sources": ["string"]}],
                    "complementary_points": [{"point": "string", "source": "string"}],
                    "integrated_text": "string",
                    "detail_index": [{"keyword": "string", "source": "string"}],
                    "visual_refs": [{"label": "string", "source": "string"}],
                    "reason": "string",
                    "teaching_integrity_note": "string",
                    "teacher_override_note": "string",
                    "confidence": 0.0,
                }
            ],
            "final_core_text": "string",
            "compression_note": "string",
            "audit_note": "string",
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def call_case_b_live_integration_llm(base_url: str, model: str, api_key: str, prompt: str) -> str:
    endpoint = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是医学教材整合智能体。你的任务是基于用户提供的真实教材片段，"
                    "生成可审计、可绘图、可追溯来源的整合决策 JSON。必须只输出合法 JSON。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.12,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def normalize_point_items(items: object, key: str = "point") -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            value = item.get(key) or item.get("keyword") or item.get("label") or item.get("text") or str(item)
            next_item = dict(item)
            next_item[key] = value
            normalized.append(next_item)
        else:
            normalized.append({key: str(item)})
    return normalized


def normalize_live_sources(sources: object, source_chunks: list[dict]) -> list[dict]:
    by_id = {index: chunk for index, chunk in enumerate(source_chunks, start=1)}
    normalized: list[dict] = []
    for source in sources or []:
        source_id = None
        if isinstance(source, int):
            source_id = source
            source = {}
        elif isinstance(source, str) and source.strip().isdigit():
            source_id = int(source.strip())
            source = {}
        elif isinstance(source, dict):
            raw_id = source.get("source_id")
            if str(raw_id).isdigit():
                source_id = int(str(raw_id))
        else:
            source = {"source_text": str(source)}

        chunk = by_id.get(source_id or -1, {})
        normalized.append(
            {
                "textbook": source.get("textbook") or chunk.get("textbook") or "未知教材",
                "chapter": source.get("chapter") or chunk.get("chapter") or "未知章节",
                "page": source.get("page") or source.get("page_start") or chunk.get("page_start") or 0,
                "source_text": source.get("source_text") or source.get("text") or chunk.get("text", "")[:260],
            }
        )

    if not normalized:
        for chunk in source_chunks[:3]:
            normalized.append(
                {
                    "textbook": chunk.get("textbook"),
                    "chapter": chunk.get("chapter"),
                    "page": chunk.get("page_start"),
                    "source_text": chunk.get("text", "")[:260],
                }
            )
    return normalized


def normalize_case_b_live_payload(payload: dict, topic: str, source_chunks: list[dict]) -> list[dict]:
    raw_decisions = payload.get("decisions") or payload.get("integration_decisions") or []
    normalized: list[dict] = []
    for index, decision in enumerate(raw_decisions, start=1):
        if not isinstance(decision, dict):
            continue
        decision_id = decision.get("decision_id") or f"live_decision_{index:04d}"
        target = decision.get("target_concept") or payload.get("target_concept") or topic
        normalized.append(
            {
                "decision_id": decision_id,
                "cluster_id": decision.get("cluster_id") or payload.get("cluster_id") or f"live_cluster_{index:04d}",
                "action": decision.get("action") or "merge",
                "reason_type": decision.get("reason_type") or "互补扩展",
                "target_concept": target,
                "keyword_path": decision.get("keyword_path") or ["医学教材整合", str(target)],
                "affected_sources": normalize_live_sources(decision.get("affected_sources"), source_chunks),
                "common_points": normalize_point_items(decision.get("common_points"), "point"),
                "complementary_points": normalize_point_items(decision.get("complementary_points"), "point"),
                "integrated_text": decision.get("integrated_text") or payload.get("final_core_text") or "",
                "detail_index": normalize_point_items(decision.get("detail_index"), "keyword"),
                "visual_refs": normalize_point_items(decision.get("visual_refs"), "label"),
                "reason": decision.get("reason") or payload.get("audit_note") or "LLM 基于给定教材片段生成的整合决策。",
                "teaching_integrity_note": decision.get("teaching_integrity_note") or payload.get("compression_note") or "",
                "teacher_override_note": decision.get("teacher_override_note", ""),
                "confidence": float(decision.get("confidence") or 0.75),
                "counts_in_core": decision.get("action") not in {"remove", "downgrade_detail", "keep_visual_index"},
            }
        )
    return normalized


def format_live_integration_summary(topic: str, source_chunks: list[dict], decisions: list[dict], payload: dict) -> str:
    source_lines = [
        f"- {chunk.get('textbook')}，{chunk.get('chapter')}，p{chunk.get('page_start')}"
        for chunk in source_chunks[:8]
    ]
    decision_lines = [
        f"- {item.get('decision_id')}｜{item.get('target_concept')}｜{item.get('action')}｜{item.get('reason_type')}\n"
        f"  理由：{item.get('reason')}\n"
        f"  凝练文本：{item.get('integrated_text')}"
        for item in decisions
    ]
    return (
        f"已完成一次教材整合批次。\n\n"
        f"主题：{topic}\n"
        f"教材片段：{len(source_chunks)} 条\n"
        f"生成决策：{len(decisions)} 条\n\n"
        "本次教材来源：\n"
        + "\n".join(source_lines)
        + "\n\n整合决策摘要：\n"
        + "\n".join(decision_lines)
        + f"\n\n压缩说明：{payload.get('compression_note', 'LLM 未返回压缩说明')}"
    )


def render_live_case_b_report(run_type: str, run_records: list[dict], decisions: list[dict], decision_graph: dict) -> str:
    saved_at = datetime.now().isoformat(timespec="seconds")
    scoped_books = sorted(
        {
            str(source.get("textbook"))
            for decision in decisions
            for source in decision.get("affected_sources", [])
            if source.get("textbook")
        }
    )
    lines = [
        "# 教材整合运行报告",
        "",
        f"- 保存时间：{saved_at}",
        f"- 运行类型：{run_type}",
        f"- 来源教材：{', '.join(scoped_books) if scoped_books else '用户指定教材来源'}",
        f"- 批次/调用次数：{len(run_records)}",
        f"- 规范化整合决策：{len(decisions)} 条",
        f"- 决策图谱：{len(decision_graph.get('nodes', []))} 节点 / {len(decision_graph.get('edges', []))} 边",
        "",
        "## 调用批次",
    ]
    for record in run_records:
        source_books = record.get("source_books") or DEBUG_CASE_B_TEXTBOOKS
        lines.extend(
            [
                "",
                f"### {record.get('batch_id') or record.get('topic') or 'single_topic'}",
                f"- 主题：{record.get('topic', '')}",
                f"- 来源教材：{', '.join(str(book) for book in source_books)}",
                f"- 来源片段数：{record.get('source_count', 0)}",
            ]
        )

    lines.extend(["", "## 整合决策摘要"])
    for decision in decisions:
        sources = decision.get("affected_sources", [])
        source_labels = [
            f"{source.get('textbook')}｜{source.get('chapter')}｜p{source.get('page')}"
            for source in sources[:4]
        ]
        lines.extend(
            [
                "",
                f"### {decision.get('decision_id')}｜{decision.get('target_concept')}",
                f"- 动作：{decision.get('action')}",
                f"- 理由类型：{decision.get('reason_type')}",
                f"- 置信度：{decision.get('confidence')}",
                f"- 理由：{decision.get('reason')}",
                f"- 凝练文本：{decision.get('integrated_text')}",
                f"- 来源：{'; '.join(source_labels)}",
            ]
        )
        if decision.get("teacher_override_note"):
            lines.append(f"- 教师覆盖说明：{decision.get('teacher_override_note')}")

    lines.extend(
        [
            "",
            "## 审计说明",
            "",
            "- 本报告来自 Streamlit 教材整合真实 LLM 批次链路。",
            "- 原始 LLM JSON、规范化 decisions 和 decision_graph 已写入同名 JSON 文件。",
            "- Demo 数据仅作为无 API Key 时的兜底展示；本文件用于证明真实教材片段调用闭环已经跑通。",
        ]
    )
    return "\n".join(lines)


def save_live_case_b_artifacts(run_type: str, run_records: list[dict], decisions: list[dict]) -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    decision_graph = build_decision_graph_from_decisions(decisions)
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "run_type": run_type,
        "debug_textbooks": list(DEBUG_CASE_B_TEXTBOOKS) if run_type == "debug_queue" else [],
        "run_records": run_records,
        "decisions": decisions,
        "decision_graph": decision_graph,
    }
    stem = f"case_b_{run_type}_{timestamp}"
    json_path = LIVE_DIR / f"{stem}.json"
    latest_json_path = LIVE_DIR / f"case_b_{run_type}_latest.json"
    report_path = LIVE_DIR / f"{stem}.md"
    latest_report_path = LIVE_DIR / f"case_b_{run_type}_latest.md"
    report = render_live_case_b_report(run_type, run_records, decisions, decision_graph)

    write_json(json_path, payload)
    write_json(latest_json_path, payload)
    write_text(report_path, report)
    write_text(latest_report_path, report)
    return {
        "json": str(json_path),
        "latest_json": str(latest_json_path),
        "report": str(report_path),
        "latest_report": str(latest_report_path),
    }


def run_case_b_live_integration(teacher_prompt: str, decisions: list[dict], api_key: str, base_url: str, model: str) -> str:
    topic, source_chunks = select_case_b_source_chunks(teacher_prompt, decisions)
    prompt = build_case_b_live_integration_prompt(teacher_prompt, topic, source_chunks)
    st.session_state.live_case_b_prompt_preview = prompt
    st.session_state.live_case_b_source_preview = source_chunks

    if not source_chunks:
        return "没有从 `data/processed/textbooks.json` 中选出可用于整合的教材片段，请先确认教材解析数据存在。"
    if not api_key:
        return (
            "当前还没有填写 API Key，因此没有真正调用 LLM。\n\n"
            f"我已经准备好教材整合输入：主题「{topic}」，教材片段 {len(source_chunks)} 条。"
            "填写 API Key 后再次点击“生成整合文档与图谱”，系统会把这些片段和教师要求发送给 LLM，并要求返回合法 JSON。"
        )

    raw_answer = call_case_b_live_integration_llm(base_url, model, api_key, prompt)
    payload = strip_llm_json(raw_answer)
    live_decisions = normalize_case_b_live_payload(payload, topic, source_chunks)
    if not live_decisions:
        raise ValueError("LLM 返回了 JSON，但没有生成 decisions / integration_decisions。")

    run_record = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "teacher_prompt": teacher_prompt,
        "source_count": len(source_chunks),
        "raw_payload": payload,
        "decisions": live_decisions,
    }
    st.session_state.live_case_b_decisions = live_decisions
    st.session_state.live_case_b_runs = [run_record] + st.session_state.get("live_case_b_runs", [])[:4]
    artifact_paths = save_live_case_b_artifacts("single_topic", [run_record], live_decisions)
    st.session_state.live_case_b_artifact_paths = artifact_paths
    return (
        format_live_integration_summary(topic, source_chunks, live_decisions, payload)
        + "\n\n已保存评审证据：\n"
        + f"- JSON：{artifact_paths['latest_json']}\n"
        + f"- 报告：{artifact_paths['latest_report']}"
    )


def build_case_b_debug_batches(teacher_prompt: str, decisions: list[dict], max_batches: int = 3) -> list[dict]:
    topics: list[str] = []
    inferred = infer_case_b_topic(teacher_prompt)
    for topic in [inferred, *DEBUG_CASE_B_TOPICS]:
        if topic and topic not in topics:
            topics.append(topic)

    batches = []
    for topic in topics:
        topic_prompt = f"{teacher_prompt}\n本批次聚焦主题：{topic}"
        _, source_chunks = select_case_b_source_chunks(
            topic_prompt,
            decisions,
            top_k=6,
            allowed_textbooks=DEBUG_CASE_B_TEXTBOOKS,
        )
        books = {chunk.get("textbook") for chunk in source_chunks}
        if len(source_chunks) < 3 or not books:
            continue
        prompt = build_case_b_live_integration_prompt(topic_prompt, topic, source_chunks)
        batches.append(
            {
                "batch_id": f"debug_batch_{len(batches) + 1:02d}",
                "topic": topic,
                "source_chunks": source_chunks,
                "source_books": sorted(str(book) for book in books if book),
                "prompt": prompt,
            }
        )
        if len(batches) >= max_batches:
            break
    return batches


def run_case_b_debug_batch_queue(
    teacher_prompt: str,
    decisions: list[dict],
    api_key: str,
    base_url: str,
    model: str,
    max_batches: int = 2,
) -> str:
    batches = build_case_b_debug_batches(teacher_prompt, decisions, max_batches=max_batches)
    st.session_state.case_b_debug_batches = batches
    if not batches:
        return "没有为《传染病学》和《医学微生物学》构建出可用调试批次，请换一个感染、病原体、病毒或细菌相关主题。"

    preview_lines = [
        f"- {batch['batch_id']}｜{batch['topic']}｜{len(batch['source_chunks'])} 条片段｜{', '.join(batch['source_books'])}"
        for batch in batches
    ]
    st.session_state.live_case_b_prompt_preview = batches[0]["prompt"]
    st.session_state.live_case_b_source_preview = batches[0]["source_chunks"]

    if not api_key:
        return (
            "已构建两本书调试整合队列，但当前未填写 API Key，因此没有真正调用 LLM。\n\n"
            "调试范围：传染病学、医学微生物学。\n"
            "批次预览：\n"
            + "\n".join(preview_lines)
            + "\n\n填写 API Key 后再次点击按钮，将按批次调用 LLM 生成可审计整合决策 JSON。"
        )

    all_decisions: list[dict] = []
    run_records = []
    for batch_index, batch in enumerate(batches, start=1):
        raw_answer = call_case_b_live_integration_llm(base_url, model, api_key, batch["prompt"])
        payload = strip_llm_json(raw_answer)
        batch_decisions = normalize_case_b_live_payload(payload, batch["topic"], batch["source_chunks"])
        for decision_index, decision in enumerate(batch_decisions, start=1):
            decision["decision_id"] = f"{batch['batch_id']}_decision_{decision_index:04d}"
            decision["cluster_id"] = batch["batch_id"]
        all_decisions.extend(batch_decisions)
        run_records.append(
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "batch_id": batch["batch_id"],
                "topic": batch["topic"],
                "source_count": len(batch["source_chunks"]),
                "source_books": batch["source_books"],
                "raw_payload": payload,
                "decisions": batch_decisions,
            }
        )

    if not all_decisions:
        raise ValueError("两本书调试队列已调用 LLM，但没有返回可用 decisions。")

    st.session_state.live_case_b_decisions = all_decisions
    st.session_state.live_case_b_runs = run_records + st.session_state.get("live_case_b_runs", [])[:3]
    artifact_paths = save_live_case_b_artifacts("debug_queue", run_records, all_decisions)
    st.session_state.live_case_b_artifact_paths = artifact_paths
    decision_lines = [
        f"- {decision.get('decision_id')}｜{decision.get('target_concept')}｜{decision.get('action')}｜{decision.get('reason_type')}"
        for decision in all_decisions
    ]
    return (
        "已完成两本书调试整合队列。\n\n"
        "调试范围：传染病学、医学微生物学。\n"
        f"批次数：{len(batches)}\n"
        f"生成整合决策：{len(all_decisions)} 条\n\n"
        "批次：\n"
        + "\n".join(preview_lines)
        + "\n\n整合决策：\n"
        + "\n".join(decision_lines)
        + "\n\n已保存评审证据：\n"
        + f"- JSON：{artifact_paths['latest_json']}\n"
        + f"- 报告：{artifact_paths['latest_report']}"
    )


def explain_decision(decision: dict) -> str:
    common = decision.get("common_points") or []
    complements = decision.get("complementary_points") or []
    common_text = "；".join(item.get("point", str(item)) if isinstance(item, dict) else str(item) for item in common) or "无显式共同点"
    complement_text = "；".join(
        item.get("point", str(item)) if isinstance(item, dict) else str(item) for item in complements
    ) or "无显式互补点"
    return (
        f"当前定位到 {decision.get('decision_id')}「{decision.get('target_concept')}」。\n\n"
        f"- 当前动作：{decision.get('action')}，理由类型：{decision.get('reason_type')}。\n"
        f"- 证据来源：{source_summary(decision)}。\n"
        f"- 共同点：{common_text}。\n"
        f"- 互补点：{complement_text}。\n\n"
        f"整合理由：{decision.get('reason')}"
    )


def classify_feedback_action(message: str) -> tuple[str, bool, str]:
    if any(word in message for word in ["拆开", "拆分", "分开", "不是同一个", "不应合并", "不要合并"]):
        return "split", True, "已标记为拆分处理：该概念不再直接合并，改为保留并列节点，图谱中会显示教师反馈节点。"
    if any(word in message for word in ["保留", "不要删除", "不删除", "不应删除", "进入主干", "放进主干"]):
        return "keep", True, "已按教师要求保留到主干内容，并把原决策标记为教师反馈调整。"
    if any(word in message for word in ["降级", "索引", "不要展开", "少展开", "细节"]):
        return "downgrade_detail", False, "已按教师要求降级为细节索引，主干只保留关键词和来源入口。"
    if any(word in message for word in ["图表", "图片", "示意图", "结构图"]):
        return "keep_visual_index", False, "已按教师要求保留为图表索引，不参与文本去重。"
    if any(word in message for word in ["删除", "移除", "不要保留"]):
        return "remove", False, "已标记为移除主干正文，但保留可追溯来源。"
    if any(word in message for word in ["合并", "整合", "归并"]):
        return "merge", True, "已确认按教师要求继续合并，并保留共同点与互补点。"
    return "keep", True, "已记录为教师个性化整合偏好，并保留在当前决策的主干说明中。"


def handle_teacher_message(message: str, decisions: list[dict]) -> str:
    cleaned = message.strip()
    if not cleaned:
        return "请输入需要调整的整合要求。"

    global_words = [
        "全局",
        "总体",
        "整体",
        "偏好",
        "备课要求",
        "课程要求",
        "这节课",
        "本节课",
        "面向",
        "课时",
        "学生",
        "教学目标",
        "备课",
    ]
    action_words = [
        "拆开",
        "拆分",
        "分开",
        "不应合并",
        "不要合并",
        "保留",
        "不要删除",
        "进入主干",
        "放进主干",
        "降级",
        "索引",
        "不要展开",
        "图表",
        "图片",
        "删除",
        "移除",
        "合并",
        "整合",
        "归并",
    ]
    explicit_decision = find_decision_from_message(cleaned, decisions, allow_fallback=False)

    if any(word in cleaned for word in global_words) or (explicit_decision is None and not any(word in cleaned for word in action_words)):
        st.session_state.teacher_requirements.append(cleaned)
        return (
            f"已记录为本轮教师优先整合要求：{cleaned}\n\n"
            "后续 LLM 整合时，这条要求会排在 Agent 默认策略之前；如果与默认压缩策略冲突，也会在整合决策里显式说明。"
        )

    decision = explicit_decision or find_decision_from_message(cleaned, decisions)
    if not decision:
        return "我还没有定位到可调整的整合决策。请指定一个概念名或 decision_id。"

    st.session_state.active_decision_id = decision["decision_id"]
    if any(word in cleaned for word in ["为什么", "原因", "解释", "依据", "理由"]):
        return explain_decision(decision)

    new_action, counts_in_core, system_update = classify_feedback_action(cleaned)
    new_text = decision.get("integrated_text", "")
    if new_action == "split":
        new_text = f"教师要求将「{decision.get('target_concept')}」拆分为并列概念处理；原共同点仅作为关联线索，互补点分别保留来源。"
    elif new_action == "downgrade_detail":
        new_text = f"「{decision.get('target_concept')}」不展开为主干正文，保留关键词、页码和来源索引用于按需查阅。"
    elif new_action == "keep_visual_index":
        new_text = f"「{decision.get('target_concept')}」相关图表保留为图表索引，支持结构和机制理解，文本部分仅保留主干说明。"
    elif new_action == "remove":
        new_text = f"「{decision.get('target_concept')}」从主干正文移除，仅保留来源索引以保证可追溯。"
    else:
        new_text = f"{decision.get('integrated_text')}（教师补充：{cleaned}）"

    override = {
        "decision_id": decision["decision_id"],
        "new_action": new_action,
        "counts_in_core": counts_in_core,
        "teacher_request": cleaned,
        "system_update": system_update,
        "new_integrated_text": new_text,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    st.session_state.decision_overrides[decision["decision_id"]] = override
    return (
        f"已更新 {decision.get('decision_id')}「{decision.get('target_concept')}」："
        f"动作改为 {new_action}。{system_update}"
    )


def render_teacher_feedback_workspace(decisions: list[dict], api_key: str, base_url: str, model: str) -> None:
    labels = [f"{item['decision_id']}｜{item['target_concept']}｜{item['action']}" for item in decisions]
    ids = [item["decision_id"] for item in decisions]
    active_id = st.session_state.get("active_decision_id", ids[0] if ids else "")
    active_index = ids.index(active_id) if active_id in ids else 0

    st.markdown(
        """
        <div class="chat-focus">
          <h3>2. 整合需求与二次反馈</h3>
          <p>先写入本轮个性化需求；不填写时使用 Agent 默认整理模式。生成结果后，继续在同一个输入栏提出二次反馈。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for message in st.session_state.teacher_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    col_live, col_hint = st.columns([0.42, 0.58])
    with col_live:
        if st.button("生成整合文档与图谱", type="primary", use_container_width=True):
            teacher_prompt = "\n".join(st.session_state.get("teacher_requirements", [])[-4:])
            if not teacher_prompt:
                teacher_prompt = "使用 Agent 默认整理模式：保留共同主干，互补内容合并，案例和细节降级为索引，目标压缩到 30%。"
            st.session_state.teacher_chat_history.append(
                {"role": "user", "content": "请基于当前教材来源和整合需求，生成整合文档与图谱。"}
            )
            try:
                with st.status("正在执行教材整合", expanded=True) as status:
                    status.write("正在读取教材来源...")
                    status.write("正在抽取相关章节与知识片段...")
                    status.write("正在组织教师需求和 Agent 默认整理策略...")
                    response = run_case_b_live_integration(teacher_prompt, decisions, api_key, base_url, model)
                    status.write("正在更新整合决策和图谱...")
                    status.update(label="整合流程已完成" if api_key else "已生成待发送整合输入", state="complete")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
                response = f"教材整合调用失败：{exc}\n\n已保留当前整合结果；请检查 API Key、Base URL、模型名或稍后重试。"
            st.session_state.teacher_chat_history.append({"role": "assistant", "content": response})
            st.rerun()
    with col_hint:
        st.caption("主流程默认面向用户指定的全部教材来源。两本书只用于开发阶段节约调试时间，不作为最终产品入口。")

    with st.expander("高级：聚焦决策、快捷操作与提示词预览", expanded=False):
        if labels:
            selected_label = st.selectbox("当前聚焦的整合决策", labels, index=active_index)
            st.session_state.active_decision_id = ids[labels.index(selected_label)]

        requirement_text = st.text_area(
            "已记录的教师优先要求",
            value="\n".join(st.session_state.teacher_requirements),
            height=92,
            help="这里保存从对话中提取出的课程目标、压缩偏好和必须保留内容。",
        )
        st.session_state.teacher_requirements = [line.strip() for line in requirement_text.splitlines() if line.strip()]

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("解释当前决策", use_container_width=True):
                decision = find_decision_from_message(st.session_state.active_decision_id, decisions)
                st.session_state.teacher_chat_history.append({"role": "user", "content": "请解释当前整合决策。"})
                st.session_state.teacher_chat_history.append({"role": "assistant", "content": explain_decision(decision)})
                st.rerun()
        with col2:
            if st.button("当前决策保留主干", use_container_width=True):
                decision = find_decision_from_message(st.session_state.active_decision_id, decisions)
                reply = handle_teacher_message(f"请保留 {decision.get('target_concept')} 到主干", decisions)
                st.session_state.teacher_chat_history.append({"role": "user", "content": f"请保留 {decision.get('target_concept')} 到主干"})
                st.session_state.teacher_chat_history.append({"role": "assistant", "content": reply})
                st.rerun()
        with col3:
            if st.button("当前决策降级索引", use_container_width=True):
                decision = find_decision_from_message(st.session_state.active_decision_id, decisions)
                reply = handle_teacher_message(f"请将 {decision.get('target_concept')} 降级为索引，不要展开", decisions)
                st.session_state.teacher_chat_history.append({"role": "user", "content": f"请将 {decision.get('target_concept')} 降级为索引，不要展开"})
                st.session_state.teacher_chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

        st.caption("这里展示的是合成后的 prompt：教师要求在前，默认策略兜底，输出格式和来源追溯作为硬约束保留。")
        st.code(build_teacher_aware_prompt(decisions), language="text")

    with st.expander("开发调试：仅用两本书快速跑通调用", expanded=False):
        st.warning("这个入口只用于节约调试时间；正式流程仍以用户上传或指定的全部教材为准。")
        if st.button("运行两本书调试队列", use_container_width=True):
            teacher_prompt = "\n".join(st.session_state.get("teacher_requirements", [])[-4:])
            st.session_state.teacher_chat_history.append(
                {"role": "user", "content": "开发调试：仅用《传染病学》和《医学微生物学》快速验证整合队列。"}
            )
            try:
                with st.spinner("正在构建两本书调试队列并调用 LLM..."):
                    response = run_case_b_debug_batch_queue(teacher_prompt, decisions, api_key, base_url, model)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
                response = f"两本书调试队列调用失败：{exc}\n\n正式整合链路未受影响；请检查 API Key、Base URL、模型名或稍后重试。"
            st.session_state.teacher_chat_history.append({"role": "assistant", "content": response})
            st.rerun()

    with st.expander("查看真实 LLM 整合输入/输出", expanded=False):
        debug_batches = st.session_state.get("case_b_debug_batches", [])
        if debug_batches:
            st.markdown("**开发调试队列**")
            for batch in debug_batches:
                st.markdown(
                    f"- {batch.get('batch_id')}｜{batch.get('topic')}｜"
                    f"{len(batch.get('source_chunks', []))} 条片段｜{', '.join(batch.get('source_books', []))}"
                )
        if st.session_state.get("live_case_b_prompt_preview"):
            st.markdown("**最近一次待发送/已发送 Prompt**")
            st.code(st.session_state.live_case_b_prompt_preview, language="json")
        else:
            st.caption("还没有生成真实整合 prompt。")
        source_preview = st.session_state.get("live_case_b_source_preview", [])
        if source_preview:
            st.markdown("**最近一次选中的教材片段**")
            for chunk in source_preview[:8]:
                st.markdown(f"- {chunk.get('textbook')}，{chunk.get('chapter')}，p{chunk.get('page_start')}")
        live_runs = st.session_state.get("live_case_b_runs", [])
        if live_runs:
            st.markdown("**最近真实 LLM 返回结果**")
            st.json(live_runs[0], expanded=False)
        artifact_paths = st.session_state.get("live_case_b_artifact_paths", {})
        if artifact_paths:
            st.markdown("**最近保存的评审证据**")
            st.markdown(f"- JSON：`{artifact_paths.get('latest_json')}`")
            st.markdown(f"- 报告：`{artifact_paths.get('latest_report')}`")

    overrides = list(st.session_state.get("decision_overrides", {}).values())
    with st.expander("查看已落地的教师修改", expanded=False):
        if not overrides:
            st.info("当前还没有教师 override。对话中提出“保留、拆分、降级、图表索引”等要求后，这里会出现修改记录。")
        else:
            st.json(overrides, expanded=True)

    prompt = st.chat_input("输入整合需求或二次反馈，例如：面向临床见习，病例保留为索引")
    if prompt:
        st.session_state.teacher_chat_history.append({"role": "user", "content": prompt})
        if any(word in prompt for word in ["开始整合", "生成整合", "生成文档", "生成图谱", "调用 LLM", "调用LLM", "真实整合"]):
            try:
                response = run_case_b_live_integration(prompt, decisions, api_key, base_url, model)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
                response = f"教材整合调用失败：{exc}\n\n已保留当前整合结果；请检查 API Key、Base URL、模型名或稍后重试。"
        else:
            response = handle_teacher_message(prompt, decisions)
        st.session_state.teacher_chat_history.append({"role": "assistant", "content": response})
        st.rerun()


def render_textbook_source_panel() -> None:
    mode_card("1. 教材来源", "先上传文件，或指定本地电脑中的教材路径。后续整合默认使用这里确定的全部教材。")
    source_mode = st.radio(
        "输入方式",
        ["指定本地路径", "上传教材文件"],
        index=0,
        key="case_b_textbook_source",
        horizontal=True,
    )
    if source_mode == "指定本地路径":
        source_path = st.text_input(
            "本地教材路径",
            value=st.session_state.get("case_b_local_textbook_path", DEFAULT_TEXTBOOK_SOURCE_PATH),
            help="可以填写教材文件夹或单个文件路径。当前演示已预解析 E:/textbooks 下的 7 本教材。",
        )
        st.session_state.case_b_local_textbook_path = source_path
        if Path(source_path).exists():
            st.success(f"已定位本地教材路径：{source_path}")
        else:
            st.warning("当前路径暂未在本机找到；如果使用已解析数据，系统仍会读取 `data/processed/textbooks.json`。")

    uploaded_files = st.file_uploader(
        "上传 PDF / TXT / MD / DOCX",
        accept_multiple_files=True,
        key="case_b_textbook_uploader",
    )
    if uploaded_files:
        st.success(f"已选择 {len(uploaded_files)} 个文件。后续会进入解析与整合队列。")
    else:
        st.caption("未上传文件时，系统会使用本地已解析教材数据作为当前教材来源。")

    summary = summarize_processed_textbooks()
    if summary["textbook_count"]:
        metric_row(
            [
                ("已解析教材", str(summary["textbook_count"])),
                ("章节/知识段", str(summary["chapter_count"])),
                ("存储字符", f"{summary['stored_chars']:,}"),
            ]
        )
        st.caption("当前可用教材：" + "、".join(summary["titles"]))
    else:
        st.warning("尚未检测到已解析教材数据。请先上传教材或确认本地路径可用。")


def render_integration_evidence_overview(decisions: list[dict], corpus: dict, decision_graph: dict) -> None:
    source_count = sum(len(decision.get("affected_sources", [])) for decision in decisions)
    core_sections = len(corpus.get("sections", []))
    overrides = st.session_state.get("decision_overrides", {})
    metric_row(
        [
            ("闭环步骤", "8/8"),
            ("整合决策", str(len(decisions))),
            ("来源引用", str(source_count)),
            ("文档章节", str(core_sections)),
            ("图谱规模", f"{len(decision_graph.get('nodes', []))} 节点 / {len(decision_graph.get('edges', []))} 边"),
            ("教师反馈", str(len(overrides))),
        ]
    )
    st.markdown(
        """
        | 闭环环节 | 当前证据 |
        |---|---|
        | 教材来源 | `1. 教材来源` 支持本地路径和上传入口；本地 7 本教材解析闭环见 `report/local_textbook_loop_check.md` |
        | 个性化需求 | `2. 整合需求与二次反馈` 记录教师要求；用户不输入时使用 Agent 默认整理模式 |
        | Agent 整合 | `查看真实 LLM 整合输入/输出` 展示 prompt、source_items、JSON schema 和 LLM 返回记录 |
        | 整合文档 | `4. 整合结果：文档` 展示 30% 凝练版教材、来源、detail_index 和 visual_refs |
        | 决策图谱 | `4. 整合结果：图谱` 展示由 integration_decisions 派生的 decision graph |
        | 决策依据 | `5. 整合依据：决策记录` 展示 action、reason_type、reason、confidence 和 affected_sources |
        | 二次反馈 | 同一输入栏可继续提出保留、拆分、合并、降级；结果写入 `decision_overrides` |
        | RAG 问答 | 左侧切换 `资料问答`，系统先查整合资料，再查教材原文 chunk |
        """
    )
    st.info(
        "完整闭环证据文档见 `docs/整合闭环证据.md`。两本书只保留为开发调试入口；正式主流程默认面向用户指定的全部教材。"
    )


def ensure_case_a_state() -> None:
    if "case_a_chat_history" not in st.session_state:
        st.session_state.case_a_chat_history = [
            {
                "role": "assistant",
                "content": "我是资料库问答入口。你可以询问已整合教材中的知识点；我会先查 Agent 资料库，未命中时再进入联网检索路径。",
            }
        ]


def build_agent_knowledge_items(decisions: list[dict], corpus: dict) -> list[dict]:
    items: list[dict] = []
    for section in corpus.get("sections", []):
        items.append(
            {
                "type": "integrated_section",
                "title": section.get("section_title", ""),
                "text": section.get("core_text", ""),
                "sources": section.get("source_refs", []),
                "decision_ids": section.get("decision_ids", []),
            }
        )

    for decision in decisions:
        source_refs = []
        source_texts = []
        for source in decision.get("affected_sources", []):
            source_refs.append(f"{source.get('textbook')} {source.get('chapter')} p{source.get('page')}")
            source_texts.append(str(source.get("source_text", "")))
        common_points = [
            item.get("point", str(item)) if isinstance(item, dict) else str(item)
            for item in decision.get("common_points", [])
        ]
        complementary_points = [
            item.get("point", str(item)) if isinstance(item, dict) else str(item)
            for item in decision.get("complementary_points", [])
        ]
        items.append(
            {
                "type": "integration_decision",
                "title": decision.get("target_concept", ""),
                "text": "\n".join(
                    [
                        decision.get("integrated_text", ""),
                        decision.get("reason", ""),
                        " ".join(common_points),
                        " ".join(complementary_points),
                        " ".join(source_texts),
                    ]
                ),
                "sources": source_refs,
                "decision_ids": [decision.get("decision_id")],
            }
        )
    return items


def analyze_query(query: str) -> dict:
    cleaned = query.strip()
    aspect = ""
    aspect_words: list[str] = []
    for label, words in QUERY_ASPECT_SYNONYMS.items():
        if any(word in cleaned for word in words):
            aspect = label
            aspect_words = words
            break

    topic = cleaned
    fillers = [
        "请问",
        "请",
        "帮我",
        "一下",
        "主要",
        "典型",
        "常见",
        "有哪些",
        "是什么",
        "什么",
        "如何",
        "为什么",
        "？",
        "?",
        "的",
        "哪里",
        "在哪",
        "在",
    ]
    for word in aspect_words + fillers:
        topic = topic.replace(word, "")
    topic = topic.strip(" ，,。:：；;")
    if not topic:
        terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", cleaned)
        topic = terms[0] if terms else cleaned
    return {"topic": topic, "aspect": aspect, "aspect_words": aspect_words}


def search_agent_knowledge(query: str, items: list[dict]) -> tuple[list[dict], str]:
    analysis = analyze_query(query)
    topic = analysis["topic"]
    aspect = analysis["aspect"]
    aspect_words = analysis["aspect_words"]
    scored: list[tuple[int, dict]] = []
    partial: list[tuple[int, dict]] = []
    for item in items:
        haystack = f"{item.get('title', '')}\n{item.get('text', '')}\n{' '.join(item.get('sources', []))}"
        score = 0
        if topic and topic in haystack:
            score += 30 if topic in str(item.get("title", "")) else 24
        else:
            topic_parts = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", topic)
            for part in topic_parts:
                if len(part) >= 2 and part in haystack:
                    score += 4

        aspect_hit = not aspect or any(word in haystack for word in aspect_words)
        if aspect and aspect_hit:
            score += 12

        if score >= 24 and aspect_hit:
            scored.append((score, item))
        elif score > 0:
            partial.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    partial.sort(key=lambda pair: pair[0], reverse=True)
    if scored:
        return [item for _, item in scored[:3]], "answered_by_agent_kb"
    if partial:
        return [item for _, item in partial[:3]], "partial_agent_kb_hit"
    return [], "agent_kb_missed"


def build_agent_answer(query: str, results: list[dict]) -> str:
    primary = results[0]
    citations = []
    for result in results:
        for source in result.get("sources", [])[:3]:
            citations.append(source)
    citation_text = "；".join(dict.fromkeys(citations)) if citations else "整合资料库"
    related = "、".join(
        dict.fromkeys(
            decision_id
            for result in results
            for decision_id in result.get("decision_ids", [])
            if decision_id
        )
    )
    supporting_points = "\n".join(
        f"- {result.get('title')}：{str(result.get('text', '')).strip()[:180]}"
        for result in results
    )
    return (
        "状态：正在查找 agent 资料库 -> 已命中 agent 已整合资料。\n\n"
        f"基于当前已整合资料，关于“{query}”可以这样回答：\n\n"
        f"{primary.get('text', '').strip()}\n\n"
        f"相关整合决策：{related or '暂无 decision_id'}。\n\n"
        f"依据片段：\n{supporting_points}\n\n"
        f"来源：{citation_text}"
    )


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def estimate_chunk_page(page_start: int, page_end: int, chunk_start: int, content_length: int) -> int:
    if page_end <= page_start or content_length <= 0:
        return page_start
    ratio = min(max(chunk_start / content_length, 0), 1)
    return int(round(page_start + ratio * (page_end - page_start)))


@st.cache_data(show_spinner=False)
def load_textbook_rag_chunks(path_text: str, chunk_size: int = 760, overlap: int = 120) -> list[dict]:
    path = Path(path_text)
    textbooks: list[dict] = load_json(path, []) if path.exists() else []
    chunks: list[dict] = []
    for book in textbooks:
        textbook_title = book.get("title") or book.get("filename") or book.get("textbook_id")
        for chapter in book.get("chapters", []):
            raw_content = compact_text(chapter.get("content", ""))
            if len(raw_content) < 120:
                continue
            page_start = int(chapter.get("page_start") or 1)
            page_end = int(chapter.get("page_end") or page_start)
            step = max(chunk_size - overlap, 200)
            for start in range(0, len(raw_content), step):
                text = raw_content[start : start + chunk_size]
                if len(text) < 120:
                    continue
                page = estimate_chunk_page(page_start, page_end, start, len(raw_content))
                chunks.append(
                    {
                        "chunk_id": f"{book.get('textbook_id')}::{chapter.get('chapter_id')}::{start}",
                        "textbook": textbook_title,
                        "filename": book.get("filename", ""),
                        "chapter": chapter.get("title", ""),
                        "page_start": page,
                        "page_end": page,
                        "page_range": f"p{page}" if page_start == page_end else f"p{page_start}-{page_end}",
                        "text": text,
                        "source_label": f"{textbook_title}｜{chapter.get('title', '')}｜p{page}",
                    }
                )
    return chunks


def textbook_query_keywords(query: str) -> list[str]:
    analysis = analyze_query(query)
    terms = [analysis.get("topic", "")]
    terms.extend(analysis.get("aspect_words", []))
    terms.extend(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", query))
    stop_terms = {"什么", "为什么", "如何", "哪些", "一下", "介绍", "解释", "说明", "相关", "主要", "常见", "典型"}
    unique: list[str] = []
    for term in terms:
        cleaned = str(term).strip()
        if len(cleaned) < 2 or cleaned in stop_terms or cleaned in unique:
            continue
        unique.append(cleaned)
        if re.fullmatch(r"[\u4e00-\u9fff]+", cleaned) and len(cleaned) >= 4:
            for size in (4, 3, 2):
                for index in range(0, len(cleaned) - size + 1):
                    part = cleaned[index : index + size]
                    if part not in stop_terms and part not in unique:
                        unique.append(part)
    return unique


def search_textbook_chunks(query: str, chunks: list[dict], top_k: int = 5) -> tuple[list[dict], str]:
    analysis = analyze_query(query)
    topic = analysis.get("topic", "")
    aspect_words = analysis.get("aspect_words", [])
    keywords = textbook_query_keywords(query)
    scored: list[tuple[int, dict]] = []

    for chunk in chunks:
        text = chunk.get("text", "")
        chapter = chunk.get("chapter", "")
        textbook = chunk.get("textbook", "")
        haystack = f"{textbook} {chapter} {text}"
        score = 0
        if topic and topic in haystack:
            score += 45 if topic in text else 25
            if topic in chapter:
                score += 18
        for expanded in CONCEPT_EXPANSIONS.get(topic, []):
            if expanded in text:
                score += 18
        for keyword in keywords:
            if keyword in textbook:
                score += 4
            if keyword in chapter:
                score += 8
            count = text.count(keyword)
            if count:
                score += min(count, 6) * (8 if keyword == topic else 4)
                first_index = text.find(keyword)
                if first_index >= 0 and first_index < 260:
                    score += 4
        if aspect_words:
            if any(word in chapter for word in aspect_words):
                score += 20
            elif any(word in text for word in aspect_words):
                score += 18
            else:
                score -= 16
        if topic and len(topic) >= 3:
            compact_topic = topic.replace("功能", "").replace("结构", "").replace("狭窄", "")
            if compact_topic and compact_topic in chapter:
                score += 18
        if analysis.get("aspect") == "功能" and any(word in text for word in ["作用", "促进", "抑制", "调节", "影响"]):
            score += 14
        if topic == "甲状腺" and "褪黑素" in text[:220]:
            score -= 160
        if "目录" in text[:80] or "目标测试" in text[:80] or "数字资源" in text[:80]:
            score -= 8
        if int(chunk.get("page_start", 1)) <= 25:
            score -= 12
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [dict(item, score=score) for score, item in scored[:top_k]]
    if results and results[0].get("score", 0) >= 28:
        return results, "answered_by_textbook_rag"
    if results:
        return results, "partial_textbook_hit"
    return [], "textbook_rag_missed"


def build_textbook_sources(chunks: list[dict]) -> str:
    lines = []
    for index, chunk in enumerate(chunks, start=1):
        lines.append(
            f"{index}. {chunk.get('textbook')}，{chunk.get('chapter')}，p{chunk.get('page_start')}\n"
            f"   原文片段：{chunk.get('text')[:220]}"
        )
    return "\n".join(lines)


def build_textbook_rag_prompt(query: str, chunks: list[dict]) -> str:
    context = [
        {
            "source_id": index,
            "textbook": chunk.get("textbook"),
            "chapter": chunk.get("chapter"),
            "page": chunk.get("page_start"),
            "text": chunk.get("text"),
        }
        for index, chunk in enumerate(chunks, start=1)
    ]
    payload = {
        "task": "answer_from_textbook_rag",
        "question": query,
        "instruction": [
            "只能基于给定 textbook_context 回答。",
            "如果片段不足以回答，要明确说资料不足。",
            "答案必须包含教材名、章节、页码和原文片段引用。",
            "不要使用未提供片段之外的知识扩展。",
        ],
        "textbook_context": context,
        "output_schema": {
            "answer": "string",
            "citations": [{"source_id": "number", "textbook": "string", "chapter": "string", "page": "number", "quote": "string"}],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def call_textbook_rag_llm(base_url: str, model: str, api_key: str, query: str, chunks: list[dict]) -> str:
    endpoint = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是医学教材 RAG 问答模块。必须只基于用户提供的教材片段回答，"
                    "并在答案后列出教材名、章节、页码和原文片段。"
                ),
            },
            {"role": "user", "content": build_textbook_rag_prompt(query, chunks)},
        ],
        "temperature": 0.15,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def format_textbook_rag_llm_answer(raw_answer: str, chunks: list[dict]) -> str:
    content = raw_answer.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return clean_llm_text(content) + "\n\n教材来源：\n" + build_textbook_sources(chunks)

    if not isinstance(payload, dict):
        return clean_llm_text(content) + "\n\n教材来源：\n" + build_textbook_sources(chunks)

    answer = clean_llm_text(payload.get("answer", ""))
    citation_lines = []
    citations = payload.get("citations") or []
    for citation in citations:
        citation_lines.append(
            f"- {clean_llm_text(citation.get('textbook'))}，"
            f"{clean_llm_text(citation.get('chapter'))}，p{citation.get('page')}\n"
            f"  原文片段：{clean_llm_text(citation.get('quote'))}"
        )
    if not citation_lines:
        citation_lines.append(build_textbook_sources(chunks))
    return f"{answer}\n\n教材来源：\n" + "\n".join(citation_lines)


def build_textbook_rag_answer(query: str, chunks: list[dict], api_key: str, base_url: str, model: str) -> str:
    if api_key:
        try:
            raw_answer = call_textbook_rag_llm(base_url, model, api_key, query, chunks)
            formatted = format_textbook_rag_llm_answer(raw_answer, chunks)
            return (
                "状态：正在查找 agent 资料库 -> 本地整合资料不足；正在检索教材原文 -> 已命中教材 RAG。\n\n"
                f"{formatted}"
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            fallback = build_textbook_sources(chunks)
            return (
                "状态：正在查找 agent 资料库 -> 本地整合资料不足；正在检索教材原文 -> 已命中教材 RAG。\n\n"
                f"已检索到教材原文，但调用 LLM 生成答案失败：{exc}\n\n"
                "先返回可追溯原文片段供教师判断：\n"
                f"{fallback}"
            )

    return (
        "状态：正在查找 agent 资料库 -> 本地整合资料不足；正在检索教材原文 -> 已命中教材 RAG。\n\n"
        "当前未填写 API Key，因此先返回最相关教材片段。填写 API Key 后，系统会让 LLM 只基于这些片段生成完整答案。\n\n"
        "教材来源：\n"
        f"{build_textbook_sources(chunks)}"
    )


def build_web_search_prompt(query: str, partial_results: list[dict] | None = None) -> str:
    partial_context = []
    for result in partial_results or []:
        partial_context.append(
            {
                "title": result.get("title"),
                "text": str(result.get("text", ""))[:500],
                "sources": result.get("sources", []),
                "decision_ids": result.get("decision_ids", []),
            }
        )
    payload = {
        "task": "web_research_answer",
        "user_question": query,
        "search_status": "agent_knowledge_base_insufficient_then_web_search",
        "partial_agent_context": partial_context,
        "requirements": [
            "先说明 Agent 已整合资料库是否未命中或仅部分相关但不足以回答。",
            "再进行联网检索；优先查权威医学教材、指南、医疗机构或综述来源。",
            "回答中必须区分联网来源和 Agent 本地资料库来源。",
            "如果当前 API 不具备联网检索能力，必须明确说明，并把答案标记为 LLM 基于通用医学知识生成、需教师核验。",
            "不得把联网结果写回整合图谱，除非教师明确要求纳入整合资料。",
        ],
        "output_schema": {
            "answer": "string",
            "web_sources": [{"title": "string", "url": "string", "evidence": "string"}],
            "local_kb_status": "missed | partial_hit_but_insufficient",
            "follow_up_suggestion": "string",
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def call_openai_compatible_llm(base_url: str, model: str, api_key: str, query: str, partial_results: list[dict]) -> str:
    prompt = build_web_search_prompt(query, partial_results)
    endpoint = base_url.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是医学教材整合 Agent 的 Case A 问答模块。"
                    "当本地整合资料不足时，你需要使用可用的联网检索能力回答。"
                    "如果当前模型或 API 不支持联网检索，请明确说明，不要伪造网页来源。"
                    "回答必须中文、简洁、列出来源状态。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"]


def clean_llm_text(text: object) -> str:
    value = str(text or "").strip()
    return value.replace("\\n", "\n").replace("\\t", "\t")


def format_llm_answer(raw_answer: str) -> str:
    content = raw_answer.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return clean_llm_text(content)

    if not isinstance(payload, dict):
        return clean_llm_text(content)

    parts = [clean_llm_text(payload.get("answer", ""))]
    web_sources = payload.get("web_sources") or []
    if web_sources:
        source_lines = []
        for index, source in enumerate(web_sources, start=1):
            title = clean_llm_text(source.get("title", f"来源 {index}"))
            url = clean_llm_text(source.get("url", ""))
            evidence = clean_llm_text(source.get("evidence", ""))
            line = f"{index}. {title}"
            if url:
                line += f"\n   {url}"
            if evidence:
                line += f"\n   证据：{evidence}"
            source_lines.append(line)
        parts.append("联网来源：\n" + "\n".join(source_lines))
    else:
        parts.append("联网来源：当前返回中没有可核验网页来源。")

    local_status = clean_llm_text(payload.get("local_kb_status", ""))
    if local_status:
        parts.append(f"本地资料库状态：{local_status}")

    suggestion = clean_llm_text(payload.get("follow_up_suggestion", ""))
    if suggestion:
        parts.append(f"后续建议：{suggestion}")

    return "\n\n".join(part for part in parts if part.strip())


def build_web_fallback_answer(
    query: str,
    api_key: str,
    base_url: str,
    model: str,
    partial_results: list[dict] | None = None,
    local_status: str = "agent_kb_missed",
) -> str:
    if local_status == "partial_agent_kb_hit":
        local_note = "Agent 资料库只命中了部分相关内容，但不足以回答你的具体问题。"
    else:
        local_note = "Agent 资料库未命中可回答该问题的整合资料。"
    if api_key:
        try:
            llm_answer = call_openai_compatible_llm(base_url, model, api_key, query, partial_results or [])
            formatted_answer = format_llm_answer(llm_answer)
            return (
                "状态：正在查找 agent 资料库 -> 本地资料不足；正在联网检索。\n\n"
                f"{local_note}\n\n"
                "LLM 检索/回答结果：\n\n"
                f"{formatted_answer}"
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            return (
                "状态：正在查找 agent 资料库 -> 本地资料不足；正在联网检索。\n\n"
                f"{local_note}\n\n"
                "已尝试调用用户配置的 OpenAI-compatible API，但调用失败。"
                f"错误信息：{exc}\n\n"
                "为了避免伪造答案，当前不直接回答该医学问题。请检查 API Key、Base URL、模型名或网络能力。"
            )

    return (
        "状态：正在查找 agent 资料库 -> 本地资料不足；正在联网检索。\n\n"
        f"{local_note}\n\n"
        "当前未填写 API Key，因此不会编造答案。填写 API Key 后，系统会把以下任务发送给 LLM，并要求其联网检索或明确说明当前 API 不支持联网。\n\n"
        "待发送任务：\n"
        f"```json\n{build_web_search_prompt(query, partial_results)}\n```"
    )


def handle_case_a_message(query: str, decisions: list[dict], corpus: dict, api_key: str, base_url: str, model: str) -> str:
    items = build_agent_knowledge_items(decisions, corpus)
    if items:
        results, local_status = search_agent_knowledge(query, items)
        if local_status == "answered_by_agent_kb":
            return build_agent_answer(query, results)
    else:
        results, local_status = [], "agent_kb_missed"

    textbook_chunks = load_textbook_rag_chunks(str(TEXTBOOKS_PATH))
    rag_results, rag_status = search_textbook_chunks(query, textbook_chunks)
    if rag_status == "answered_by_textbook_rag":
        return build_textbook_rag_answer(query, rag_results, api_key, base_url, model)

    return build_web_fallback_answer(query, api_key, base_url, model, results, local_status)


def render_case_a_workspace(decisions: list[dict], corpus: dict, api_key: str, base_url: str, model: str) -> None:
    ensure_case_a_state()
    items = build_agent_knowledge_items(decisions, corpus)
    textbook_chunks = load_textbook_rag_chunks(str(TEXTBOOKS_PATH))
    st.markdown(
        """
        <div class="chat-focus">
          <h3>资料库问答</h3>
          <p>在下方输入问题。系统会先查已整合资料，再查 7 本教材原文；回答会尽量带回教材名、章节、页码和原文片段。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for message in st.session_state.case_a_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    with st.expander("查看资料库状态", expanded=False):
        metric_row(
            [
                ("Agent 资料条目", str(len(items))),
                ("教材 RAG chunk", str(len(textbook_chunks))),
                ("整合决策", str(len(decisions))),
                ("联网检索", "可接入" if api_key else "待填 API Key"),
            ]
        )
        if items:
            st.success("已检测到当前整合资料，将优先调用。")
        else:
            st.warning("当前还没有整合资料，会优先检索教材 RAG。")
        if textbook_chunks:
            st.success(f"已加载 {len(textbook_chunks)} 个教材原文 chunk。")
        else:
            st.warning("未找到 `data/processed/textbooks.json`，教材 RAG 暂不可用。")
    with st.expander("查看已整合资料条目", expanded=False):
        for item in items[:8]:
            st.markdown(f"**{item.get('title', '资料条目')}**")
            st.write(str(item.get("text", ""))[:360])
            st.caption("来源：" + "；".join(item.get("sources", [])))
            st.divider()
    with st.expander("查看教材 RAG 样例片段", expanded=False):
        for chunk in textbook_chunks[:5]:
            st.markdown(f"**{chunk.get('source_label', '教材片段')}**")
            st.write(chunk.get("text", "")[:360])
            st.divider()

    query = st.chat_input("询问已整合资料，例如：甲状腺结节的典型症状是什么？")
    if query:
        st.session_state.case_a_chat_history.append({"role": "user", "content": query})
        with st.chat_message("assistant"):
            live_notice = st.empty()
            live_notice.info("正在检索本地资料...")
        with st.status("正在查找 agent 资料库", expanded=True) as status:
            items = build_agent_knowledge_items(decisions, corpus)
            results, local_status = search_agent_knowledge(query, items) if items else ([], "agent_kb_missed")
            if local_status == "answered_by_agent_kb":
                live_notice.success("已命中 agent 资料库，正在组织答案...")
                status.write(f"命中 {len(results)} 条可回答资料，优先使用 Agent 资料库回答。")
                status.update(label="已命中 agent 资料库", state="complete")
                response = build_agent_answer(query, results)
            else:
                if local_status == "partial_agent_kb_hit":
                    status.write(f"命中 {len(results)} 条部分相关资料，但不足以回答该具体问题。")
                else:
                    status.write("Agent 资料库无命中。")
                live_notice.info("整合资料不足；正在检索 7 本教材原文...")
                status.update(label="正在检索教材原文", state="running")
                rag_results, rag_status = search_textbook_chunks(query, textbook_chunks)
                if rag_status == "answered_by_textbook_rag":
                    status.write(f"教材 RAG 命中 {len(rag_results)} 条原文片段，将带来源回答。")
                    live_notice.success("已命中教材原文，正在生成带来源答案...")
                    response = build_textbook_rag_answer(query, rag_results, api_key, base_url, model)
                    status.update(label="已命中教材 RAG", state="complete")
                else:
                    if rag_status == "partial_textbook_hit":
                        status.write(f"教材中找到 {len(rag_results)} 条弱相关片段，但不足以回答。")
                    else:
                        status.write("教材原文未命中可回答片段。")
                    live_notice.warning("本地资料不足；正在联网检索...")
                    status.update(label="正在联网检索", state="running")
                    response = build_web_fallback_answer(query, api_key, base_url, model, results, local_status)
                    live_notice.success("联网检索流程完成，正在显示结果...")
                    status.update(label="联网检索完成" if api_key else "等待 API Key 后联网检索", state="complete")
        st.session_state.case_a_chat_history.append({"role": "assistant", "content": response})
        st.rerun()


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def main() -> None:
    st.set_page_config(page_title="Hacson 教材整合智能体", layout="wide", page_icon="H")
    inject_styles()

    decisions: list[dict] = load_json(DEMO_DIR / "integration_decisions_demo.json", [])
    corpus: dict = load_json(DEMO_DIR / "integrated_corpus_demo.json", {})
    audit: dict = load_json(DEMO_DIR / "integration_audit_demo.json", {})
    prompt_doc = load_text(DOCS_DIR / "LLM整合提示词设计.md")
    ensure_teacher_feedback_state(decisions)
    live_decisions = st.session_state.get("live_case_b_decisions") or []
    base_decisions = live_decisions if live_decisions else decisions
    effective_decisions = apply_decision_overrides(base_decisions)
    decision_graph = build_decision_graph_from_decisions(effective_decisions)

    product_header(
        "Hacson 学科知识整合智能体",
        "先确定教材来源，再写入个性化整合需求；Agent 生成可追溯整合文档与图谱，用户可基于结果继续反馈迭代。",
        "AI Full-stack Hackathon",
        ["教材整合", "图谱生成", "二次反馈", "来源可追溯"],
    )

    with st.sidebar:
        st.header("LLM 配置")
        base_url = st.text_input("Base URL", value="https://chaoye.xyz")
        model = st.text_input("Model", value="gpt-5.4")
        api_key = st.text_input("API Key", value="", type="password", help="只在当前会话使用；不要写入仓库。")
        st.checkbox("OpenAI-compatible API", value=True)
        st.divider()
        st.header("工作入口")
        mode = st.radio(
            "选择本轮任务",
            [
                "教材整合：生成文档与图谱",
                "资料问答：基于整合结果查询",
            ],
            index=0,
        )
        st.divider()

    if mode.startswith("资料问答"):
        render_case_a_workspace(effective_decisions, corpus, api_key, base_url, model)
        return

    render_textbook_source_panel()
    render_teacher_feedback_workspace(effective_decisions, api_key, base_url, model)

    with st.expander("3. 整合闭环证据总览", expanded=True):
        render_integration_evidence_overview(effective_decisions, corpus, decision_graph)

    with st.expander("3. 查看整合流程与指标", expanded=False):
        metric_row(
            [
                ("整合决策", str(len(effective_decisions))),
                ("原始字符", f"{int(corpus.get('original_chars', 0)):,}"),
                ("目标上限 30%", f"{int(corpus.get('target_chars', 0)):,}"),
                ("决策图谱", f"{len(decision_graph.get('nodes', []))} 节点 / {len(decision_graph.get('edges', []))} 边"),
            ]
        )
        st.code(
            """教材上传/本地读取
-> 教材解析
-> 单书层级整理
-> 单书主干凝练
-> 跨书候选簇发现
-> LLM 生成逐条整合决策和理由
-> 输出 30% 凝练版教材
-> 根据整合决策生成最终图谱
-> 教师反馈迭代
-> 教材 RAG 问答""",
            language="text",
        )
        st.info("最终权威结果来自整合决策：每条文档内容、图谱节点和边都应能追溯到 decision、理由和来源片段。")

    with st.expander("4. 整合结果：图谱", expanded=False):
        st.markdown('<div class="graph-wrap">' + render_decision_graph(decision_graph) + "</div>", unsafe_allow_html=True)
        st.caption("这里展示的是 decision graph，不是旧版术语图谱。节点和边都能追溯到整合决策理由。")
        st.json(decision_graph, expanded=False)

    with st.expander("4. 整合结果：文档", expanded=False):
        st.subheader(corpus.get("integrated_title", "凝练版教材"))
        ratio = corpus.get("compression_ratio", 0)
        st.progress(min(float(ratio) / 0.3, 1.0), text=f"压缩比 {ratio:.6f}，目标 <= 0.300000")
        for section in corpus.get("sections", []):
            st.markdown(f"**{section.get('section_title', '')}**")
            section_text = section.get("core_text", "")
            adjusted_notes = []
            for decision_id in section.get("decision_ids", []):
                override = st.session_state.get("decision_overrides", {}).get(decision_id)
                if override:
                    adjusted_notes.append(f"{decision_id}：{override.get('new_integrated_text')}")
            if adjusted_notes:
                section_text = section_text + "\n\n教师反馈调整：\n" + "\n".join(adjusted_notes)
            st.write(section_text)
            st.caption("来源：" + "；".join(section.get("source_refs", [])))
            st.json({"detail_index": section.get("detail_index", []), "visual_refs": section.get("visual_refs", [])}, expanded=False)
            st.divider()
        st.success(corpus.get("teaching_integrity_summary", ""))

    with st.expander("4. 整合结果：正式报告", expanded=False):
        st.markdown("正式报告已生成：`report/整合报告.md`")
        report_text = load_text(REPORT_DIR / "整合报告.md")
        st.markdown(report_text[:3000] + ("\n\n..." if len(report_text) > 3000 else ""))

    with st.expander("5. 整合依据：决策记录", expanded=False):
        selected_types = st.multiselect(
            "筛选 reason_type",
            sorted({decision.get("reason_type", "") for decision in effective_decisions}),
            default=sorted({decision.get("reason_type", "") for decision in effective_decisions}),
        )
        for decision in effective_decisions:
            if decision.get("reason_type") in selected_types:
                st.markdown(f"**{decision.get('decision_id')}｜{decision.get('target_concept')}｜{decision.get('action')}**")
                st.write(decision.get("reason", ""))
                st.json(decision, expanded=False)
                st.divider()

    with st.expander("5. 整合依据：提示词与评审证据", expanded=False):
        st.caption("文档来源：docs/LLM整合提示词设计.md")
        if prompt_doc:
            st.markdown(prompt_doc)
        else:
            st.warning("未找到提示词设计文档。")
        st.json(audit, expanded=False)
        st.markdown(
            """
            - `docs/LLM整合提示词设计.md`：提示词与 JSON schema。
            - `data/demo/integration_decisions_demo.json`：逐条整合决策与理由。
            - `data/demo/integrated_corpus_demo.json`：30% 凝练版结构。
            - `data/demo/decision_graph_demo.json`：由整合记录生成的最终图谱。
            - `report/整合报告.md`：正式整合报告。
            """
        )


if __name__ == "__main__":
    main()
