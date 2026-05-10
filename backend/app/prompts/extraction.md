# Knowledge Extraction Prompt

从给定教材章节中抽取核心知识点和关系。

输出必须是 JSON，包含：
- nodes: id, name, definition, category, chapter, page, source_text
- edges: source, target, relation_type, description

关系类型只能使用：
- prerequisite
- parallel
- contains
- applies_to

