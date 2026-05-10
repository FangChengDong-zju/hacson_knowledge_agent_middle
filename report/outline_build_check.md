# Outline Build Check

Generated at: 2026-05-10 11:12:59 +08:00

## Outputs

| Item | Path |
|---|---|
| Demo outlines | E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\outlines_demo.json |
| Runtime outlines | E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\outlines.json |
| Summary | E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\outline_summary.json |

## Metrics

| Metric | Value |
|---|---:|
| Textbooks | 7 |
| Outline items | 2391 |
| Graph-core items | 2255 |
| Detail-index items | 136 |
| Visual refs | 283 |

## Book Outline Counts

| ID | Textbook | Items |
|---|---|---:|
| book_001 | 局部解剖学 | 287 |
| book_002 | 组织学与胚胎学 | 302 |
| book_003 | 生理学 | 418 |
| book_004 | 医学微生物学 | 372 |
| book_005 | 病理学 | 377 |
| book_006 | 传染病学 | 368 |
| book_007 | 病理生理学 | 267 |

## Why This Layer Exists

- Step 1 is pure data processing: textbook -> chapter -> level1/level2 knowledge outline.
- Step 2 graph generation consumes only graph_core outline items, while detail_index items stay searchable.
- Figure/table hints are preserved as visual_refs instead of being collapsed into text deduplication.
