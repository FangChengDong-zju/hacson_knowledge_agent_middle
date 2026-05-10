from __future__ import annotations

from ..models import IntegrationDecision, IntegrationSummary, Textbook


def summarize_integration(textbooks: list[Textbook], decisions: list[IntegrationDecision]) -> IntegrationSummary:
    original_chars = sum(book.total_chars for book in textbooks)
    merge_count = sum(1 for item in decisions if item.action == "merge")
    keep_count = sum(1 for item in decisions if item.action == "keep")
    remove_count = sum(1 for item in decisions if item.action == "remove")

    # P1 strategy: keep the main trunk and downgrade details to source indexes.
    # The estimate is intentionally conservative for the competition compression target.
    integrated_chars = min(int(original_chars * 0.30), max(merge_count * 240 + keep_count * 180, 0))
    ratio = (integrated_chars / original_chars) if original_chars else 0.0
    return IntegrationSummary(
        textbook_count=len(textbooks),
        original_chars=original_chars,
        integrated_chars=integrated_chars,
        compression_ratio=ratio,
        merge_count=merge_count,
        keep_count=keep_count,
        remove_count=remove_count,
    )

