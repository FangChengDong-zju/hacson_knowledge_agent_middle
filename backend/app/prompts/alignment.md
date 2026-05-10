# Alignment Prompt

判断多个知识点是否描述同一概念。

输出字段：
- equivalent: boolean
- canonical_name: string
- reason: string
- confidence: number

原则：
- 同义词、英文名、缩写可合并。
- 上下位概念不要误合并。
- 教学上需要分开讲解的概念不要合并。

