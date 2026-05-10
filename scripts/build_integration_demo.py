from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = PROJECT_ROOT / "data" / "demo"
REPORT_DIR = PROJECT_ROOT / "report"
PARSE_SUMMARY = PROJECT_ROOT / "data" / "processed" / "parse_summary.json"
GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "graph.json"


def main() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    parse_summary = read_json(PARSE_SUMMARY, {})
    graph = read_json(GRAPH_PATH, {"nodes": [], "edges": []})
    original_chars = int(parse_summary.get("totals", {}).get("chars", 3_956_088))
    target_chars = int(original_chars * 0.3)

    decisions = build_decisions()
    corpus = build_integrated_corpus(decisions, original_chars, target_chars)
    decision_graph = build_decision_graph(decisions)
    audit = {
        "demo_mode": True,
        "source_graph_nodes": len(graph.get("nodes", [])),
        "source_graph_edges": len(graph.get("edges", [])),
        "decision_count": len(decisions),
        "original_chars": original_chars,
        "target_chars": target_chars,
        "integrated_chars": corpus["integrated_chars"],
        "compression_ratio": corpus["compression_ratio"],
        "note": "This demo illustrates the LLM integration workflow before live API calls are wired.",
    }

    write_json(DEMO_DIR / "integration_decisions_demo.json", decisions)
    write_json(DEMO_DIR / "integrated_corpus_demo.json", corpus)
    write_json(DEMO_DIR / "decision_graph_demo.json", decision_graph)
    write_json(DEMO_DIR / "integration_audit_demo.json", audit)
    (REPORT_DIR / "integrated_corpus_demo.md").write_text(render_markdown(corpus), encoding="utf-8")
    print(f"Wrote {len(decisions)} demo integration decisions")
    print(f"Wrote decision graph nodes={len(decision_graph['nodes'])}, edges={len(decision_graph['edges'])}")


def read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_decisions() -> list[dict]:
    return [
        {
            "decision_id": "decision_0001",
            "cluster_id": "cluster_thyroid_001",
            "action": "merge",
            "reason_type": "互补扩展",
            "target_concept": "甲状腺",
            "keyword_path": ["基础医学", "人体系统", "内分泌系统", "甲状腺"],
            "affected_sources": [
                {
                    "textbook": "局部解剖学",
                    "chapter": "颈部",
                    "page": 120,
                    "source_text": "甲状腺位于颈前区，具有特定形态、毗邻关系和血管供应。",
                },
                {
                    "textbook": "生理学",
                    "chapter": "内分泌",
                    "page": 210,
                    "source_text": "甲状腺分泌甲状腺激素，参与机体代谢、生长发育和能量调节。",
                },
            ],
            "common_points": [
                {
                    "point": "甲状腺是内分泌系统的重要器官",
                    "evidence_sources": ["局部解剖学 p120", "生理学 p210"],
                }
            ],
            "complementary_points": [
                {"point": "形态、位置、毗邻和血供", "source": "局部解剖学 p120"},
                {"point": "甲状腺激素与代谢调节", "source": "生理学 p210"},
            ],
            "integrated_text": "甲状腺是位于颈前区的重要内分泌器官，具有特定形态、毗邻和血供特点，并通过分泌甲状腺激素参与代谢、生长发育和能量调节。",
            "detail_index": [
                {"keyword": "毗邻结构", "source": "局部解剖学 p120"},
                {"keyword": "激素调节反馈", "source": "生理学 p210"},
            ],
            "visual_refs": [
                {"label": "甲状腺局部解剖图", "source": "局部解剖学 p121"},
                {"label": "下丘脑-垂体-甲状腺轴示意图", "source": "生理学 p212"},
            ],
            "reason": "两本教材均讨论甲状腺这一高一级概念；局部解剖学补充结构细节，生理学补充功能机制。共同点合并，互补点保留，图示单独归档。",
            "teaching_integrity_note": "整合后保留从结构到功能的学习链路。",
            "confidence": 0.88,
            "counts_in_core": True,
        },
        {
            "decision_id": "decision_0002",
            "cluster_id": "cluster_inflammation_001",
            "action": "merge",
            "reason_type": "共同主干",
            "target_concept": "炎症",
            "keyword_path": ["病理学", "病变机制", "损伤-反应-修复", "炎症"],
            "affected_sources": [
                {
                    "textbook": "病理学",
                    "chapter": "炎症",
                    "page": 78,
                    "source_text": "炎症是具有血管系统的活体组织对损伤因子的防御反应。",
                },
                {
                    "textbook": "病理生理学",
                    "chapter": "发热与炎症介质",
                    "page": 96,
                    "source_text": "炎症介质可参与局部反应和全身反应，并影响体温调节。",
                },
            ],
            "common_points": [
                {"point": "炎症是机体对损伤或感染的防御性反应", "evidence_sources": ["病理学 p78", "病理生理学 p96"]}
            ],
            "complementary_points": [
                {"point": "炎症的形态学表现和分类", "source": "病理学 p78"},
                {"point": "炎症介质与全身反应", "source": "病理生理学 p96"},
            ],
            "integrated_text": "炎症是活体组织对损伤或感染的防御性反应，表现为血管反应、细胞反应和炎症介质参与，并可引起局部修复或全身反应。",
            "detail_index": [
                {"keyword": "各型炎症举例", "source": "病理学 p82"},
                {"keyword": "炎症介质列表", "source": "病理生理学 p98"},
            ],
            "visual_refs": [{"label": "炎症过程模式图", "source": "病理学 p80"}],
            "reason": "两本教材对炎症的核心定义重合，但分别强调形态变化和功能反应；合并共同定义，保留互补视角。",
            "teaching_integrity_note": "保留损伤因子-炎症反应-修复/全身反应的逻辑链。",
            "confidence": 0.9,
            "counts_in_core": True,
        },
        {
            "decision_id": "decision_0003",
            "cluster_id": "cluster_infection_immune_001",
            "action": "merge",
            "reason_type": "互补扩展",
            "target_concept": "感染与免疫应答",
            "keyword_path": ["感染与免疫", "病原-宿主", "感染-免疫应答"],
            "affected_sources": [
                {
                    "textbook": "医学微生物学",
                    "chapter": "感染与免疫",
                    "page": 126,
                    "source_text": "病原微生物感染后可引起机体固有免疫和适应性免疫应答。",
                },
                {
                    "textbook": "传染病学",
                    "chapter": "传染病总论",
                    "page": 42,
                    "source_text": "传染病发生取决于病原体、宿主免疫状态和传播条件。",
                },
            ],
            "common_points": [
                {"point": "感染结果取决于病原体与宿主反应", "evidence_sources": ["医学微生物学 p126", "传染病学 p42"]}
            ],
            "complementary_points": [
                {"point": "病原体致病性和免疫机制", "source": "医学微生物学 p126"},
                {"point": "流行过程、传播和临床防治", "source": "传染病学 p42"},
            ],
            "integrated_text": "感染是病原体与宿主相互作用的过程，结局取决于病原体致病性、宿主免疫状态和传播条件；医学微生物学提供机制基础，传染病学补充传播、防治和临床管理。",
            "detail_index": [
                {"keyword": "特定病原体例子", "source": "医学微生物学相关章节"},
                {"keyword": "各传染病临床表现", "source": "传染病学各论"},
            ],
            "visual_refs": [{"label": "感染过程示意图", "source": "传染病学 p44"}],
            "reason": "两本教材共同讨论感染，但学科侧重点不同；共同主干合并，病原机制和临床防控作为互补点保留。",
            "teaching_integrity_note": "保留从病原体到宿主反应再到传播防治的学习顺序。",
            "confidence": 0.87,
            "counts_in_core": True,
        },
        {
            "decision_id": "decision_0004",
            "cluster_id": "cluster_case_examples_001",
            "action": "downgrade_detail",
            "reason_type": "案例降级",
            "target_concept": "临床案例与操作说明",
            "keyword_path": ["医学方法", "教学细节", "案例索引"],
            "affected_sources": [
                {
                    "textbook": "局部解剖学",
                    "chapter": "局部解剖操作",
                    "page": 46,
                    "source_text": "章节中包含大量操作步骤和病例引入。",
                },
                {
                    "textbook": "传染病学",
                    "chapter": "各论",
                    "page": 188,
                    "source_text": "章节中包含具体病例、流行病学数据和鉴别诊断细节。",
                },
            ],
            "common_points": [],
            "complementary_points": [],
            "integrated_text": "具体病例、操作说明和长篇背景不进入主干教材正文，仅保留关键词索引用于按需查阅。",
            "detail_index": [
                {"keyword": "局部解剖操作步骤", "source": "局部解剖学 p46"},
                {"keyword": "传染病病例与鉴别诊断", "source": "传染病学 p188"},
            ],
            "visual_refs": [],
            "reason": "此类内容有教学参考价值，但不属于跨教材主干；为满足 30% 压缩目标，应降级为索引。",
            "teaching_integrity_note": "主干学习不依赖完整案例文本，索引保留复查入口。",
            "confidence": 0.82,
            "counts_in_core": False,
        },
        {
            "decision_id": "decision_0005",
            "cluster_id": "cluster_visual_summary_001",
            "action": "keep_visual_index",
            "reason_type": "图表归档",
            "target_concept": "结构与机制图表",
            "keyword_path": ["教学资源", "图表索引"],
            "affected_sources": [
                {
                    "textbook": "组织学与胚胎学",
                    "chapter": "基本组织",
                    "page": 52,
                    "source_text": "该页含组织结构模式图。",
                },
                {
                    "textbook": "病理学",
                    "chapter": "炎症",
                    "page": 80,
                    "source_text": "该页含炎症过程图。",
                },
            ],
            "common_points": [],
            "complementary_points": [
                {"point": "形态结构图示", "source": "组织学与胚胎学 p52"},
                {"point": "病理过程图示", "source": "病理学 p80"},
            ],
            "integrated_text": "图表不进入文本去重流程，统一进入图表索引，用于支持结构、机制和病理过程的可视化学习。",
            "detail_index": [],
            "visual_refs": [
                {"label": "基本组织结构图", "source": "组织学与胚胎学 p52"},
                {"label": "炎症过程图", "source": "病理学 p80"},
            ],
            "reason": "图片和表格具有可读性和教学价值，文本可压缩，但图示应汇总保留并链接原文。",
            "teaching_integrity_note": "图表索引补足文本压缩后的视觉理解入口。",
            "confidence": 0.91,
            "counts_in_core": False,
        },
    ]


def build_integrated_corpus(decisions: list[dict], original_chars: int, target_chars: int) -> dict:
    sections = [
        {
            "section_title": "结构-功能主干：甲状腺",
            "core_text": decisions[0]["integrated_text"],
            "decision_ids": ["decision_0001"],
            "source_refs": ["局部解剖学 p120", "生理学 p210"],
            "detail_index": decisions[0]["detail_index"],
            "visual_refs": decisions[0]["visual_refs"],
        },
        {
            "section_title": "损伤-反应-修复主干：炎症",
            "core_text": decisions[1]["integrated_text"],
            "decision_ids": ["decision_0002"],
            "source_refs": ["病理学 p78", "病理生理学 p96"],
            "detail_index": decisions[1]["detail_index"],
            "visual_refs": decisions[1]["visual_refs"],
        },
        {
            "section_title": "病原-宿主主干：感染与免疫应答",
            "core_text": decisions[2]["integrated_text"],
            "decision_ids": ["decision_0003"],
            "source_refs": ["医学微生物学 p126", "传染病学 p42"],
            "detail_index": decisions[2]["detail_index"],
            "visual_refs": decisions[2]["visual_refs"],
        },
        {
            "section_title": "细节索引与图表索引",
            "core_text": "病例、计算、操作和图表不直接展开为主干正文；系统保留关键词、页码和原文路径，供学生和教师按需回溯。",
            "decision_ids": ["decision_0004", "decision_0005"],
            "source_refs": ["局部解剖学 p46", "传染病学 p188", "组织学与胚胎学 p52", "病理学 p80"],
            "detail_index": decisions[3]["detail_index"],
            "visual_refs": decisions[4]["visual_refs"],
        },
    ]
    text = "\n".join(section["core_text"] for section in sections)
    integrated_chars = len(text)
    return {
        "integrated_title": "7 本医学教材整合凝练版 Demo",
        "original_chars": original_chars,
        "target_chars": target_chars,
        "integrated_chars": integrated_chars,
        "compression_ratio": round(integrated_chars / original_chars, 6),
        "sections": sections,
        "teaching_integrity_summary": "Demo 保留结构-功能、损伤-反应、病原-宿主三条主干链路；案例、计算、操作和图表降级为索引。",
    }


def build_decision_graph(decisions: list[dict]) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()

    def add_node(node_id: str, label: str, kind: str, decision_id: str | None = None) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append({"id": node_id, "label": label, "kind": kind, "decision_id": decision_id})

    for decision in decisions:
        decision_id = decision["decision_id"]
        concept_id = f"concept::{decision['target_concept']}"
        add_node(concept_id, decision["target_concept"], "concept", decision_id)
        add_node(f"decision::{decision_id}", decision_id, "decision", decision_id)
        edges.append({"source": f"decision::{decision_id}", "target": concept_id, "relation": decision["action"], "reason": decision["reason"]})

        for point in decision.get("common_points", []):
            point_text = point["point"] if isinstance(point, dict) else str(point)
            point_id = f"common::{point_text}"
            add_node(point_id, point_text, "common_point", decision_id)
            edges.append({"source": concept_id, "target": point_id, "relation": "contains_common", "reason": "共同点形成跨教材关联"})

        for point in decision.get("complementary_points", []):
            point_text = point["point"] if isinstance(point, dict) else str(point)
            point_id = f"complement::{point_text}"
            add_node(point_id, point_text, "complementary_point", decision_id)
            edges.append({"source": concept_id, "target": point_id, "relation": "contains_complement", "reason": "互补点保留"})

        for source in decision.get("affected_sources", []):
            book = source.get("textbook", "")
            source_id = f"book::{book}"
            add_node(source_id, book, "textbook", decision_id)
            edges.append({"source": source_id, "target": concept_id, "relation": "evidence_for", "reason": decision["reason_type"]})

    return {"nodes": nodes, "edges": edges}


def render_markdown(corpus: dict) -> str:
    lines = [
        f"# {corpus['integrated_title']}",
        "",
        f"- 原始字数：{corpus['original_chars']}",
        f"- 目标字数：{corpus['target_chars']}",
        f"- Demo 凝练字数：{corpus['integrated_chars']}",
        f"- Demo 压缩比：{corpus['compression_ratio']}",
        "",
    ]
    for section in corpus["sections"]:
        lines.append(f"## {section['section_title']}")
        lines.append("")
        lines.append(section["core_text"])
        lines.append("")
        lines.append("来源：" + "；".join(section["source_refs"]))
        lines.append("")
    lines.append("## 教学完整性说明")
    lines.append("")
    lines.append(corpus["teaching_integrity_summary"])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
