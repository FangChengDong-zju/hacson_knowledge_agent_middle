# API 接口文档

## 健康检查

```text
GET /api/health
```

响应：

```json
{
  "status": "ok",
  "app": "Hacson Knowledge Agent",
  "textbook_dir": "E:/textbooks"
}
```

## 解析本地教材

```text
POST /api/textbooks/parse-local
```

从 `TEXTBOOK_DIR` 读取最多 7 本教材并解析为统一结构。

## 临时上传教材

```text
POST /api/textbooks/upload
```

`multipart/form-data` 上传 PDF / Markdown / TXT / DOCX。上传后教材会被纳入当前 `textbooks.json`，可继续重新整理层级和构建图谱。

## 构建教材层级

```text
POST /api/outlines/build
GET /api/outlines
```

将教材整理为 `Textbook -> Chapter -> Level1/Level2/Level3 Knowledge Item`。图谱构建优先消费 `detail_policy=graph_core` 的 outline 项，细节内容进入 `detail_index`。

## 构建图谱

```text
POST /api/graph/build
```

响应包含 `graph.nodes` 和 `graph.edges`。节点带 `keyword_path`、`textbooks`、`source_refs`、`visual_refs`，用于跨教材图谱和图表索引。

## 执行整合

```text
POST /api/integration/run
```

响应包含整合决策与压缩摘要。

## RAG 问答

```text
POST /api/rag/query
```

请求：

```json
{
  "question": "炎症的核心定义是什么？"
}
```

响应：

```json
{
  "answer": "根据当前教材索引...",
  "citations": [],
  "source_chunks": []
}
```
