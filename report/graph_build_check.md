# Graph Build Check

Generated at: 2026-05-10 11:16:47 +08:00

## Outputs

| Item | Path |
|---|---|
| Demo graph | E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\graph_demo.json |
| Runtime graph | E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\processed\graph.json |
| Summary | E:\codex test\Preparation for Hacson\hacson_knowledge_agent\data\demo\graph_summary.json |

## Metrics

| Metric | Value |
|---|---:|
| Source outlines | 7 |
| Nodes | 89 |
| Edges | 365 |
| Visual refs | 150 |

## Categories

| Category | Nodes |
|---|---:|
| knowledge_layer | 26 |
| 病理过程 | 14 |
| 病理生理 | 1 |
| 传染病 | 3 |
| 方法与评价 | 3 |
| 感染免疫 | 10 |
| 基础结构 | 9 |
| 疾病总论 | 1 |
| 器官系统 | 10 |
| 生理机制 | 11 |
| 生理指标 | 1 |

## Keyword Paths

| Keyword path | Nodes |
|---|---:|
| 病理生理学 | 1 |
| 病理生理学 > 功能失衡 | 1 |
| 病理生理学 > 功能失衡 > 稳态破坏 | 2 |
| 病理学 | 1 |
| 病理学 > 病变机制 | 1 |
| 病理学 > 病变机制 > 损伤-反应-修复 | 15 |
| 感染与免疫 | 1 |
| 感染与免疫 > 病原-宿主 | 1 |
| 感染与免疫 > 病原-宿主 > 感染-免疫应答 | 11 |
| 基础医学 | 1 |
| 基础医学 > 功能调节 | 1 |
| 基础医学 > 功能调节 > 机制-过程 | 12 |
| 基础医学 > 功能调节 > 指标-参数 | 2 |
| 基础医学 > 人体系统 | 1 |
| 基础医学 > 人体系统 > 器官-系统 | 11 |
| 基础医学 > 形态结构 | 1 |
| 基础医学 > 形态结构 > 细胞-组织-器官 | 10 |
| 临床前医学 | 1 |
| 临床前医学 > 疾病概念 | 1 |
| 临床前医学 > 疾病概念 > 分类-演变 | 2 |
| 临床医学 | 1 |
| 临床医学 > 感染性疾病 | 1 |
| 临床医学 > 感染性疾病 > 传播-诊断-防治 | 4 |
| 医学方法 | 1 |
| 医学方法 > 诊疗与评价 | 1 |
| 医学方法 > 诊疗与评价 > 诊断-治疗-预防 | 4 |

## Scoring Evidence

- B2: graph JSON is generated from textbook outlines, not raw noisy full text.
- B3/C: graph nodes carry category and keyword_path fields for multi-level medical browsing.
- B4: repeated core terms across textbooks are merged by core_term and supported by source_refs.
- Image strategy: visual_refs preserve page-level figure/table hints outside text deduplication.
