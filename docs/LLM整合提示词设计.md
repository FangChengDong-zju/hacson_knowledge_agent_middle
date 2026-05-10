# LLM 整合提示词设计

本文定义“教材整合凝练”阶段的 LLM 工作方式。注意：本项目不内嵌用户 API Key。用户应在前端或 `.env` 中自行输入 OpenAI-compatible API 配置，系统只提供提示词、结构化输入和校验流程。

当前建议配置：

```text
LLM_BASE_URL=https://chaoye.xyz
LLM_MODEL=gpt-5.4
LLM_WIRE_API=chat
OpenAI-compatible=true
```

## 0. 提示词来源与优先级

真实调用 LLM 时，提示词来自两部分：

1. Agent 自带提示词：默认整合模式、压缩原则、输出 JSON schema、来源追溯规则。
2. 教师写入要求：本轮课程目标、备课偏好、必须保留或必须拆分的概念、压缩侧重点。

优先级原则：

```text
教师写入要求 > Agent 默认整合策略
```

也就是说，当教师没有提出明确要求时，系统使用默认整合模式；当教师提出明确要求时，LLM 必须优先满足教师要求。例如：
- 默认策略会把案例降级为索引，但教师要求“这个病例必须保留进主干”时，应保留进主干。
- 默认策略会合并高度相关概念，但教师要求“抗原和免疫原要拆开”时，应拆分为并列节点。
- 默认策略会压缩操作步骤，但教师要求“这部分用于实验课，操作步骤必须保留”时，应降低压缩强度。

需要保留的硬约束：
- 输出仍必须是结构化 JSON，方便系统审计和绘图。
- 每条整合决策仍必须给出理由、来源和置信度。
- 不能编造教材来源；如果教师要求与来源证据冲突，需要在 `conflict_notes` 中说明。
- 如果教师要求覆盖了默认策略，需要在 `teacher_override_note` 中说明覆盖关系。

当前 Streamlit 体验页已经在“教师反馈整合”Tab 中生成本轮合成 prompt，结构为：

```text
教师要求
-> Agent 默认整合策略
-> 输出格式与来源追溯硬约束
-> 当前决策摘要和教师 override
```

## 1. 核心判断

最终图谱不应直接从原文术语生成，而应从“整合决策记录”生成。

原因：
- 赛题要求系统对每一项整合决策给出理由。
- 图谱节点应代表教材整合后的关键共同点、互补点和教学主干，而不是裸词频。
- 评审时需要看到“为什么合并、为什么保留、为什么删除或降级”。

因此主流程调整为：

```text
教材上传/本地读取
-> 教材解析
-> 单书层级整理
-> 单书主干凝练
-> 跨书候选簇发现
-> LLM 生成逐条整合决策
-> 输出 30% 凝练版教材
-> 根据整合决策生成最终图谱
```

## 2. 两类整合任务

### 2.1 单本书内部整合

目标：把每本教材内部内容先整理成教学主干。

保留：
- 核心概念定义。
- 分类框架。
- 机制链路。
- 因果关系。
- 学习顺序。
- 必要公式或判断标准。

降级：
- 具体病例。
- 重复说明。
- 大段背景。
- 操作性描述。
- 计算过程。
- 扩展阅读。

降级内容不直接删除，而是进入：

```text
detail_index = 一句关键词 + 教材/章节/页码/原文片段索引
```

图片、表格、流程图不参与文本去重，应进入：

```text
visual_refs = 教材/章节/页码/图表说明/原文路径
```

### 2.2 多本书之间整合

目标：把不同教材中相同或相关的部分合并，并保留互补细节。

典型情况：

```text
《局部解剖学》提到：甲状腺 = 细节 A + 细节 B
《生理学》提到：甲状腺 = 细节 A + 细节 C
```

整合后：

```text
核心节点：甲状腺
共同细节：A
互补细节：B + C
最终主干：甲状腺 = A + B + C 的凝练表述
关联点：
  - “甲状腺”是两本书的高一级关联点。
  - “细节 A”是两本书共同提到的低一级关联点。
  - “细节 B/C”是各教材提供的互补补充。
```

这类整合必须输出：
- 共同点是什么。
- 互补点是什么。
- 哪些内容被合并。
- 哪些内容被保留为细节索引。
- 哪些图表被归档为图表索引。
- 为什么这样处理。

## 3. 整合决策类型

LLM 输出的每条决策必须属于以下 action 之一：

```text
merge              合并重复或高度等价内容
keep               保留独有但重要内容
remove             删除明显冗余内容，但保留来源索引
split              拆分被误合并的不同概念
downgrade_detail   将案例/说明/计算/背景降级为细节索引
keep_visual_index  保留图片/表格/流程图索引
```

reason_type 必须属于以下之一：

```text
文本重复
共同主干
互补扩展
层级包含
案例降级
计算降级
背景降级
图表归档
表述冲突
概念误合并
教学顺序
```

## 4. 整合记录 Schema

每条整合决策统一输出为 JSON。

```json
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
      "source_text": "..."
    },
    {
      "textbook": "生理学",
      "chapter": "内分泌",
      "page": 210,
      "source_text": "..."
    }
  ],
  "common_points": [
    {
      "point": "细节 A",
      "evidence_sources": ["局部解剖学 p120", "生理学 p210"]
    }
  ],
  "complementary_points": [
    {
      "point": "细节 B",
      "source": "局部解剖学 p120"
    },
    {
      "point": "细节 C",
      "source": "生理学 p210"
    }
  ],
  "integrated_text": "甲状腺是位于颈前区的重要内分泌器官，具有特定解剖位置和血供特点，并通过分泌甲状腺激素参与代谢调节。",
  "detail_index": [
    {
      "keyword": "毗邻结构",
      "source": "局部解剖学 p120"
    }
  ],
  "visual_refs": [
    {
      "label": "甲状腺局部解剖图",
      "source": "局部解剖学 p121"
    }
  ],
  "reason": "两本教材均围绕甲状腺展开，局部解剖学提供形态和毗邻信息，生理学提供激素调节信息；共同内容合并，互补内容保留，案例和图示进入索引。",
  "teaching_integrity_note": "整合后仍保留从结构到功能的学习链路。",
  "confidence": 0.86
}
```

## 5. System Prompt

```text
你是医学教材整合智能体，任务是将多本医学教材整合为教学主干版本，并为每一项整合决策给出理由。

必须遵守：
1. 主干优先：保留定义、分类框架、机制链路、因果关系、学习顺序、必要判断标准。
2. 细节降级：病例、重复说明、长背景、计算过程、操作细节只保留一句关键词和来源索引。
3. 跨书整合：如果多本教材讨论同一概念，必须区分共同点和互补点。
4. 共同点合并：多本教材重复出现的共同点只保留一次，并记录所有来源。
5. 互补点保留：不同教材提供的非重复补充信息应合并进入主干或细节索引。
6. 图片表格：图片、表格、流程图不参与文本去重，应保留为 visual_refs。
7. 不得无依据扩写：所有结论必须来自给定 source_refs。
8. 每条整合决策必须给出 action、reason_type、reason、affected_sources。
9. 输出必须是合法 JSON，不要输出 Markdown，不要输出解释性正文。
```

## 6. 单书主干凝练 Prompt

```text
请对以下单本医学教材章节内容进行主干凝练。

目标：
1. 提取本章节的教学主干。
2. 将案例、背景、计算、操作细节降级为 detail_index。
3. 将图片、表格、流程图线索保留为 visual_refs。
4. 保持教学逻辑完整。

教材：
{textbook_title}

章节：
{chapter_title}

页码：
{page_start}-{page_end}

原文内容：
{chapter_content}

请输出 JSON：
{
  "chapter_id": "...",
  "core_outline": [
    {
      "concept": "...",
      "keyword_path": ["...", "..."],
      "core_text": "...",
      "source_refs": ["..."],
      "detail_index": ["..."],
      "visual_refs": ["..."]
    }
  ],
  "removed_or_downgraded": [
    {
      "type": "案例降级 | 计算降级 | 背景降级 | 图表归档",
      "keyword": "...",
      "reason": "...",
      "source_ref": "..."
    }
  ],
  "teaching_integrity_note": "..."
}
```

## 7. 跨书候选簇整合 Prompt

```text
请对以下来自多本医学教材的候选内容进行整合。

你需要判断：
1. 它们是否讨论同一个高一级概念。
2. 哪些内容是多本教材共同提到的共同点。
3. 哪些内容是不同教材提供的互补点。
4. 哪些内容应合并、保留、删除、拆分或降级为索引。
5. 哪些图表应保留为 visual_refs。

候选簇 ID：
{cluster_id}

候选主题：
{cluster_title}

候选关键词路径：
{keyword_path}

候选来源：
{source_items}

请输出 JSON：
{
  "cluster_id": "...",
  "target_concept": "...",
  "decisions": [
    {
      "decision_id": "...",
      "action": "merge | keep | remove | split | downgrade_detail | keep_visual_index",
      "reason_type": "文本重复 | 共同主干 | 互补扩展 | 层级包含 | 案例降级 | 计算降级 | 背景降级 | 图表归档 | 表述冲突 | 概念误合并 | 教学顺序",
      "affected_sources": ["..."],
      "common_points": ["..."],
      "complementary_points": ["..."],
      "integrated_text": "...",
      "detail_index": ["..."],
      "visual_refs": ["..."],
      "reason": "...",
      "teaching_integrity_note": "...",
      "confidence": 0.0
    }
  ],
  "final_core_text": "...",
  "compression_note": "..."
}
```

## 8. 30% 凝练版汇总 Prompt

```text
请根据以下整合决策记录，生成最终凝练版教材内容。

要求：
1. 总篇幅应控制在原始内容的 30% 以内。
2. 只展开教学主干。
3. 细节、案例、计算、图片表格只保留索引。
4. 不得丢失必要学习链路。
5. 每一段内容必须能追溯到一条或多条 decision_id。

输入：
{integration_decisions}

原始总字数：
{original_chars}

目标最大字数：
{target_chars}

请输出 JSON：
{
  "integrated_title": "...",
  "original_chars": 0,
  "target_chars": 0,
  "integrated_chars": 0,
  "compression_ratio": 0.0,
  "sections": [
    {
      "section_title": "...",
      "core_text": "...",
      "decision_ids": ["..."],
      "source_refs": ["..."],
      "detail_index": ["..."],
      "visual_refs": ["..."]
    }
  ],
  "teaching_integrity_summary": "..."
}
```

## 9. 最终图谱生成规则

最终图谱从 `integration_decisions.json` 生成，不直接从原文生成。

节点来源：
- `target_concept`
- `common_points`
- 重要 `complementary_points`
- 高一级 `keyword_path`

边来源：
- 同一 decision 内：`target_concept contains common_points/complementary_points`
- 多本教材共同点：共同点连接到所有来源教材。
- 互补点：互补点连接到对应来源教材和目标概念。
- 教学顺序：由 LLM 标注或规则生成 `prerequisite`。
- 应用关系：机制到疾病、结构到功能生成 `applies_to`。

节点详情必须展示：
- 整合理由。
- 涉及教材。
- 共同点。
- 互补点。
- 被降级细节索引。
- 图表索引。
- 决策置信度。

## 10. 产品 UI 要求

整合页面必须让用户看到：
- 当前整合进度。
- 每条整合决策。
- action 和 reason_type。
- LLM 给出的 reason。
- 原始来源。
- 整合后文本。
- 细节索引。
- 图表索引。
- 是否计入 30% 主干内容。

图谱页面必须让用户看到：
- 节点来自哪条整合决策。
- 为什么这些教材被关联。
- 哪些内容是共同点。
- 哪些内容是互补点。
- 对应 source_refs 和 visual_refs。

## 11. 校验策略

LLM 输出后必须做程序校验：
- JSON 是否合法。
- action 是否在枚举内。
- reason_type 是否在枚举内。
- 每条 decision 是否有 reason。
- 每条 decision 是否有 affected_sources。
- integrated_text 是否为空。
- visual_refs 是否保留图表线索。
- 汇总字数是否超过 30%。

如果校验失败：
- 自动要求 LLM 修复 JSON。
- 或回退到规则整合，标记 `confidence` 较低。
