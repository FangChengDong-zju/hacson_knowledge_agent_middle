# Hacson Knowledge Agent

学科知识整合智能体：面向多本医学教材，完成教材解析、知识图谱构建、跨教材整合压缩、带引用 RAG 问答和教师反馈迭代。

## 项目结构

```text
backend/   FastAPI 后端：解析、抽取、整合、索引、问答、报告
frontend/  React + Vite 前端：图谱区、问答区、整合决策区
docs/      需求分析、系统设计、Agent 架构说明、API 文档
report/    整合报告
data/      本地运行数据，教材 PDF 不提交到 GitHub
```

## 后续开发入口

为避免上下文腐烂，后续继续开发前优先读取：

```text
docs/项目上下文快照.md
```

赛题要求、评分点和进度看板以 `docs/赛题速查_学科知识整合智能体.md` 为准。后续不再同步桌面副本，项目内文档是唯一事实来源。

## Streamlit 体验版

当前已提供类似 `health_agent_demo` 的网页体验版，用于展示：

- 用户自行输入 LLM API Key，不写入仓库。
- 教材上传/本地教材入口。
- LLM 整合提示词设计。
- 每条整合决策、理由、来源、共同点、互补点。
- 30% 凝练版教材。
- 由整合决策生成的最终图谱 demo。

启动：

```powershell
cd hacson_knowledge_agent
.\run_streamlit_demo.ps1
```

访问：

```text
http://127.0.0.1:8502
```

## 本地教材路径

比赛回测教材位于本机：

```text
E:/textbooks
```

项目通过 `.env` 中的 `TEXTBOOK_DIR` 读取教材，不复制 PDF 到仓库。

当前准备环境中已有一份预抽取缓存：

```text
health_agent_demo/data/textbook_chunks.jsonl
health_agent_demo/reports/textbook_index_stats.json
```

后端的 `POST /api/textbooks/parse-local` 会优先使用缓存完成本地教材解析闭环；如果缓存不存在，再回退到直接读取 `E:/textbooks` 下的 PDF/MD/TXT。

## 面向 AI 评审的提交原则

赛题条目多、评审时间短，项目默认面向“AI 初筛 + 人工复核”设计：

- 模块命名直接对应评分点：Parser、Graph Builder、Alignment、Compression、RAG、Feedback、Report。
- 文档显式列出需求、架构、API、Agent 设计、整合报告。
- README 和 `docs/Agent架构说明.md` 优先说明“做了什么、为什么这样做、证据在哪里”。
- 前端第一屏直接呈现三大块：图谱、问答、整合索引，方便评审快速定位功能。
- UI 保持专业、清晰、可扫读，后续会补充视觉细节用于冲刺高分。

## 后端启动

```powershell
cd hacson_knowledge_agent/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env
uvicorn app.main:app --reload --port 8000
```

健康检查：

```text
GET http://localhost:8000/api/health
```

## 无 Python 时的缓存启动

如果现场机器暂时没有可用 Python，可以先用 PowerShell 将准备阶段索引转换为新项目运行数据：

```powershell
cd hacson_knowledge_agent
.\scripts\bootstrap_cached_textbooks.ps1
```

生成：

```text
data/processed/textbooks.json
```

随后运行闭环验证脚本：

```powershell
.\scripts\verify_local_textbook_loop.ps1
```

当前验证结果：

```text
7 本本地医学教材已解析为 105 个章节/知识段。
总页数 2567，总可用字符数 3956088。
验证报告：report/local_textbook_loop_check.md
机器摘要：data/processed/parse_summary.json
```

后端启动后会直接读取这份已解析教材数据。

## 生成整合报告

赛题基础要求的报告格式是 Markdown 文件：

```text
report/整合报告.md
```

手动生成：

```powershell
cd hacson_knowledge_agent
& "C:\Users\29434\AppData\Local\Programs\Python\Python311\python.exe" .\scripts\build_final_report.py
```

运行 `.\run_streamlit_demo.ps1` 时也会自动刷新 demo 整合数据和正式整合报告。

## 前端启动

```powershell
cd hacson_knowledge_agent/frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

## 当前骨架能力

- 固定三大块：图谱、问答、整合索引。
- 后端 API 路由已分层。
- 数据结构已定义。
- 默认教材目录配置为 `E:/textbooks`。
- 图谱、RAG、整合、反馈、报告均有服务模块入口。
- 无 LLM Key 时预留规则 fallback，不让演示流程崩掉。

## 提交注意

不要提交教材 PDF。`.gitignore` 已排除：

```text
data/textbooks/*.pdf
*.pdf
```
