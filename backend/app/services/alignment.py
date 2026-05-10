from __future__ import annotations

from collections import defaultdict

from ..models import IntegrationDecision, KnowledgeGraph, KnowledgeNode


def align_graph(graph: KnowledgeGraph) -> list[IntegrationDecision]:
    groups: dict[str, list[KnowledgeNode]] = defaultdict(list)
    for node in graph.nodes:
        groups[_normalize(node.name)].append(node)

    decisions: list[IntegrationDecision] = []
    counter = 1
    for key, nodes in groups.items():
        if not key:
            continue
        if len({node.textbook_id for node in nodes}) >= 2:
            decisions.append(
                IntegrationDecision(
                    decision_id=f"merge_{counter:03d}",
                    action="merge",
                    affected_nodes=[node.id for node in nodes],
                    result_node=f"merged_{key}_{counter:03d}",
                    reason="多个教材中出现同名或高度相似知识点，合并为主干节点，保留所有来源索引。",
                    confidence=0.86,
                )
            )
            counter += 1
        else:
            node = nodes[0]
            decisions.append(
                IntegrationDecision(
                    decision_id=f"keep_{counter:03d}",
                    action="keep",
                    affected_nodes=[node.id],
                    result_node=node.id,
                    reason="该知识点暂未发现跨教材重复，保留为唯一或补充内容。",
                    confidence=0.72,
                )
            )
            counter += 1
    return decisions


def _normalize(name: str) -> str:
    return "".join(ch for ch in name.lower().strip() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")[:24]

