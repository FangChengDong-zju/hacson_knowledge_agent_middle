from __future__ import annotations

from ..models import FeedbackResponse, IntegrationDecision


def apply_teacher_feedback(
    message: str,
    decisions: list[IntegrationDecision],
    decision_id: str | None = None,
) -> FeedbackResponse:
    target = _find_target(decisions, decision_id)
    if target is None:
        return FeedbackResponse(reply="我还没有找到要修改的整合决策，请先选择一条决策。")

    lowered = message.lower()
    if "保留" in message or "keep" in lowered:
        target.action = "keep"
        target.teacher_override = True
        target.reason = f"教师反馈要求保留：{message}"
        return FeedbackResponse(reply="已根据教师反馈将该决策调整为保留，并标记为人工覆盖。", updated_decision=target)
    if "删除" in message or "remove" in lowered:
        target.action = "remove"
        target.teacher_override = True
        target.reason = f"教师反馈要求删除或降级：{message}"
        return FeedbackResponse(reply="已根据教师反馈将该决策调整为删除/降级索引，并标记为人工覆盖。", updated_decision=target)
    if "分开" in message or "拆" in message:
        target.action = "keep"
        target.teacher_override = True
        target.reason = f"教师反馈认为概念不应合并：{message}"
        return FeedbackResponse(reply="已将合并决策拆开处理，相关节点改为分别保留。", updated_decision=target)

    return FeedbackResponse(reply=f"这条决策的当前理由是：{target.reason}", updated_decision=target)


def _find_target(decisions: list[IntegrationDecision], decision_id: str | None) -> IntegrationDecision | None:
    if decision_id:
        for decision in decisions:
            if decision.decision_id == decision_id:
                return decision
    return decisions[0] if decisions else None

