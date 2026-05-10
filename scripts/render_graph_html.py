from __future__ import annotations

import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "graph.json"
HTML_PATH = PROJECT_ROOT / "report" / "knowledge_graph_demo.html"
SVG_PATH = PROJECT_ROOT / "report" / "knowledge_graph_snapshot.svg"

WIDTH = 1800
HEIGHT = 1120
CENTER_X = WIDTH / 2
CENTER_Y = 540

CATEGORY_COLORS = {
    "knowledge_layer": "#172033",
    "基础结构": "#7c3aed",
    "器官系统": "#4f46e5",
    "生理机制": "#059669",
    "生理指标": "#0d9488",
    "病理过程": "#dc2626",
    "病理生理": "#ea580c",
    "疾病总论": "#be123c",
    "感染免疫": "#0891b2",
    "传染病": "#2563eb",
    "方法与评价": "#64748b",
}

CATEGORY_LABELS = {
    "knowledge_layer": "知识层级",
}


def main() -> None:
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(f"Graph JSON not found: {GRAPH_PATH}")

    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8-sig"))
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    positions = layout_nodes(nodes)
    category_counts = Counter(node.get("category", "") for node in nodes)
    relation_counts = Counter(edge.get("relation_type", "") for edge in edges)
    visual_refs = sum(len(node.get("visual_refs") or []) for node in nodes)
    textbook_titles = sorted(
        {
            title
            for node in nodes
            for title in (node.get("textbooks") or [])
            if isinstance(title, str) and title
        }
    )

    svg = build_svg(nodes, edges, positions, category_counts, relation_counts)
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(svg, encoding="utf-8")
    HTML_PATH.write_text(
        build_html(graph, positions, svg, category_counts, relation_counts, visual_refs, textbook_titles),
        encoding="utf-8",
    )
    print(f"Wrote HTML graph: {HTML_PATH}")
    print(f"Wrote SVG snapshot: {SVG_PATH}")
    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")


def layout_nodes(nodes: list[dict]) -> dict[str, dict[str, float]]:
    top_paths = sorted(
        {
            (node.get("keyword_path") or ["未分类"])[0] or "未分类"
            for node in nodes
        }
    )
    angle_by_top = {
        top: (2 * math.pi * index / max(len(top_paths), 1)) - math.pi / 2
        for index, top in enumerate(top_paths)
    }
    category_nodes: dict[str, list[dict]] = defaultdict(list)
    layer_nodes: list[dict] = []
    for node in nodes:
        if node.get("category") == "knowledge_layer":
            layer_nodes.append(node)
        else:
            category_nodes[node.get("category", "未分类")].append(node)

    positions: dict[str, dict[str, float]] = {}

    for node in layer_nodes:
        path = node.get("keyword_path") or [node.get("name", "未分类")]
        top = path[0] if path else "未分类"
        depth = max(len(path), 1)
        angle = angle_by_top.get(top, 0)
        radius = 90 + (depth - 1) * 82
        positions[node["id"]] = {
            "x": CENTER_X + math.cos(angle) * radius,
            "y": CENTER_Y + math.sin(angle) * radius,
            "r": 22 + max(0, 4 - depth) * 4,
        }

    categories = sorted(category_nodes.keys())
    category_angles = {
        category: (2 * math.pi * index / max(len(categories), 1)) - math.pi / 2
        for index, category in enumerate(categories)
    }
    for category, items in category_nodes.items():
        base_angle = category_angles[category]
        cluster_x = CENTER_X + math.cos(base_angle) * 360
        cluster_y = CENTER_Y + math.sin(base_angle) * 360
        count = len(items)
        sorted_items = sorted(
            items,
            key=lambda node: (
                -(len(node.get("textbooks") or [])),
                -int(node.get("frequency") or 0),
                node.get("name", ""),
            ),
        )
        for index, node in enumerate(sorted_items):
            ring = 1 + index // 10
            slot = index % 10
            angle = base_angle + (slot - 4.5) * 0.22 + ring * 0.05
            radius = 72 + ring * 58
            if count <= 4:
                radius = 54
            positions[node["id"]] = {
                "x": cluster_x + math.cos(angle) * radius,
                "y": cluster_y + math.sin(angle) * radius,
                "r": 16 + min(len(node.get("textbooks") or []), 7) * 2.7,
            }
    return positions


def build_svg(
    nodes: list[dict],
    edges: list[dict],
    positions: dict[str, dict[str, float]],
    category_counts: Counter,
    relation_counts: Counter,
) -> str:
    nodes_by_id = {node["id"]: node for node in nodes}
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L0,6 L9,3 z" fill="#94a3b8" />',
        "</marker>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">',
        '<feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#0f172a" flood-opacity="0.16"/>',
        "</filter>",
        "</defs>",
        '<rect x="0" y="0" width="1800" height="1120" fill="#f8fafc"/>',
        '<text x="40" y="52" font-size="30" font-weight="800" fill="#172033">医学教材多级关键词知识图谱</text>',
        '<text x="40" y="84" font-size="16" fill="#64748b">层级节点连接医学知识轴，术语节点合并跨教材重复概念；节点越大表示出现教材越多。</text>',
    ]

    legend_x = 40
    legend_y = 124
    for index, (category, count) in enumerate(sorted(category_counts.items())):
        x = legend_x + (index % 4) * 270
        y = legend_y + (index // 4) * 30
        color = CATEGORY_COLORS.get(category, "#64748b")
        label = CATEGORY_LABELS.get(category, category)
        parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')
        parts.append(f'<text x="{x + 14}" y="{y + 5}" font-size="13" fill="#334155">{esc(label)} ({count})</text>')

    edge_style = {
        "contains": ("#64748b", 0.55, 1.4),
        "parallel": ("#94a3b8", 0.23, 1.0),
        "prerequisite": ("#f59e0b", 0.58, 1.7),
        "applies_to": ("#0ea5e9", 0.46, 1.5),
    }
    parts.append('<g id="edges">')
    for edge in edges:
        source = positions.get(edge.get("source"))
        target = positions.get(edge.get("target"))
        if not source or not target:
            continue
        relation = edge.get("relation_type", "parallel")
        color, opacity, width = edge_style.get(relation, ("#94a3b8", 0.25, 1.0))
        marker = ' marker-end="url(#arrow)"' if relation != "parallel" else ""
        parts.append(
            f'<line x1="{source["x"]:.1f}" y1="{source["y"]:.1f}" x2="{target["x"]:.1f}" y2="{target["y"]:.1f}" '
            f'stroke="{color}" stroke-width="{width}" stroke-opacity="{opacity}"{marker}/>'
        )
    parts.append("</g>")

    parts.append('<g id="nodes">')
    for node in sorted(nodes, key=lambda item: item.get("category") != "knowledge_layer"):
        pos = positions[node["id"]]
        color = CATEGORY_COLORS.get(node.get("category"), "#64748b")
        label = node.get("name", "")
        label_short = label if len(label) <= 8 else label[:8]
        stroke = "#f59e0b" if node.get("category") == "knowledge_layer" else "#ffffff"
        stroke_width = 3 if node.get("category") == "knowledge_layer" else 2
        parts.append(
            f'<g class="node" data-node-id="{esc(node["id"])}">'
            f'<circle cx="{pos["x"]:.1f}" cy="{pos["y"]:.1f}" r="{pos["r"]:.1f}" fill="{color}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" filter="url(#shadow)"/>'
            f'<text x="{pos["x"]:.1f}" y="{pos["y"] + pos["r"] + 16:.1f}" text-anchor="middle" font-size="12" '
            f'font-weight="700" fill="#172033">{esc(label_short)}</text>'
            "</g>"
        )
    parts.append("</g>")

    stats = ", ".join(f"{key}:{value}" for key, value in sorted(relation_counts.items()))
    parts.append(f'<text x="40" y="{HEIGHT - 32}" font-size="13" fill="#64748b">关系统计：{esc(stats)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def build_html(
    graph: dict,
    positions: dict[str, dict[str, float]],
    svg: str,
    category_counts: Counter,
    relation_counts: Counter,
    visual_refs: int,
    textbook_titles: list[str],
) -> str:
    graph_json = json.dumps(graph, ensure_ascii=False)
    positions_json = json.dumps(positions, ensure_ascii=False)
    category_rows = "".join(
        f"<span><b>{esc(CATEGORY_LABELS.get(category, category))}</b>{count}</span>"
        for category, count in sorted(category_counts.items())
    )
    relation_rows = "".join(
        f"<span><b>{esc(relation)}</b>{count}</span>"
        for relation, count in sorted(relation_counts.items())
    )
    textbooks = "、".join(textbook_titles)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>医学教材多级关键词知识图谱</title>
  <style>
    :root {{ color: #172033; background: #eef2f7; font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    .shell {{ min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }}
    header {{ padding: 18px 22px; background: #fff; border-bottom: 1px solid #d9e1ef; display: flex; justify-content: space-between; gap: 18px; align-items: end; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    p {{ margin: 0; color: #5f6f85; line-height: 1.55; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }}
    .stats span {{ border: 1px solid #d9e1ef; background: #f8fafc; border-radius: 999px; padding: 6px 10px; font-size: 13px; }}
    .stats b {{ margin-right: 5px; color: #172033; }}
    .main {{ display: grid; grid-template-columns: minmax(720px, 1fr) 390px; gap: 14px; padding: 14px; height: calc(100vh - 105px); }}
    .canvas {{ background: #fff; border: 1px solid #d9e1ef; border-radius: 8px; overflow: auto; }}
    .side {{ display: grid; gap: 12px; min-height: 0; grid-template-rows: auto auto 1fr; }}
    .panel {{ background: #fff; border: 1px solid #d9e1ef; border-radius: 8px; padding: 14px; }}
    .panel h2 {{ margin: 0 0 10px; font-size: 16px; }}
    input {{ width: 100%; border: 1px solid #c8d2e2; border-radius: 6px; padding: 10px; font: inherit; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 7px; }}
    .chips span {{ background: #eef4ff; color: #31547a; border-radius: 999px; padding: 5px 8px; font-size: 12px; font-weight: 700; }}
    .detail {{ overflow: auto; }}
    .detail h2 {{ font-size: 20px; }}
    .path {{ color: #1d4ed8; font-weight: 800; margin-bottom: 8px; }}
    .meta {{ display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0; }}
    .meta span {{ background: #f1f5f9; border-radius: 999px; padding: 5px 8px; font-size: 12px; }}
    .ref {{ border: 1px solid #e1e7f0; background: #f9fbfe; border-radius: 7px; padding: 9px; margin-top: 8px; }}
    .ref strong {{ display: block; }}
    .ref small {{ color: #64748b; }}
    .node circle {{ cursor: pointer; transition: transform 0.12s ease, opacity 0.12s ease; transform-box: fill-box; transform-origin: center; }}
    .node:hover circle {{ transform: scale(1.14); opacity: 0.9; }}
    .node.faded {{ opacity: 0.14; }}
    .node.active circle {{ stroke: #facc15; stroke-width: 6; }}
    @media (max-width: 1150px) {{ .main {{ grid-template-columns: 1fr; height: auto; }} header {{ display: block; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>医学教材多级关键词知识图谱</h1>
        <p>基于 outlines.json 凝练：层级关键词串联医学知识轴，术语节点合并跨教材重复知识点。</p>
      </div>
      <div class="stats">
        <span><b>节点</b>{len(graph.get("nodes", []))}</span>
        <span><b>关系</b>{len(graph.get("edges", []))}</span>
        <span><b>教材</b>{len(textbook_titles)}</span>
        <span><b>图表索引</b>{visual_refs}</span>
      </div>
    </header>
    <main class="main">
      <section class="canvas">{svg}</section>
      <aside class="side">
        <section class="panel">
          <h2>检索节点</h2>
          <input id="search" placeholder="输入关键词，如：感染、炎症、激素" />
        </section>
        <section class="panel">
          <h2>类别统计</h2>
          <div class="chips">{category_rows}</div>
          <h2 style="margin-top:14px;">关系统计</h2>
          <div class="chips">{relation_rows}</div>
        </section>
        <section class="panel detail" id="detail">
          <h2>点击节点查看详情</h2>
          <p>当前图谱覆盖教材：{esc(textbooks)}</p>
        </section>
      </aside>
    </main>
  </div>
  <script>
    const graph = {graph_json};
    const positions = {positions_json};
    const byId = new Map(graph.nodes.map(node => [node.id, node]));
    const detail = document.getElementById("detail");
    function escText(value) {{
      return String(value ?? "").replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
    }}
    function showNode(node) {{
      document.querySelectorAll(".node").forEach(item => item.classList.remove("active"));
      const selected = document.querySelector(`[data-node-id="${{node.id}}"]`);
      if (selected) selected.classList.add("active");
      const refs = (node.source_refs || []).slice(0, 4).map(ref => `
        <article class="ref">
          <strong>${{escText(ref.textbook_title)}}</strong>
          <small>${{escText(ref.chapter_title)}} · 页 ${{escText(ref.page_start ?? "-")}}</small>
          <p>${{escText(ref.snippet)}}</p>
        </article>`).join("");
      detail.innerHTML = `
        <h2>${{escText(node.name)}}</h2>
        <p class="path">${{escText((node.keyword_path || []).join(" / "))}}</p>
        <p>${{escText(node.definition)}}</p>
        <div class="meta">
          <span>${{escText(node.category === "knowledge_layer" ? "知识层级" : node.category)}}</span>
          <span>${{(node.textbooks || []).length}} 本教材</span>
          <span>${{Number(node.frequency || 0).toLocaleString()}} 次出现</span>
          <span>图表索引 ${{(node.visual_refs || []).length}}</span>
        </div>
        <div class="chips">${{(node.textbooks || []).map(title => `<span>${{escText(title)}}</span>`).join("")}}</div>
        <h2 style="margin-top:14px;">来源索引</h2>
        ${{refs || "<p>该层级节点用于组织图谱，无直接原文片段。</p>"}}
      `;
    }}
    document.querySelectorAll(".node").forEach(item => {{
      item.addEventListener("click", () => showNode(byId.get(item.dataset.nodeId)));
    }});
    document.getElementById("search").addEventListener("input", event => {{
      const keyword = event.target.value.trim();
      document.querySelectorAll(".node").forEach(item => {{
        const node = byId.get(item.dataset.nodeId);
        const haystack = [node.name, node.category, ...(node.keyword_path || []), ...(node.textbooks || [])].join(" ");
        item.classList.toggle("faded", Boolean(keyword) && !haystack.includes(keyword));
      }});
    }});
  </script>
</body>
</html>
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    main()
