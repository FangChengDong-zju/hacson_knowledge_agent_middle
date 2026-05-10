# Hacson Knowledge Agent

学科知识整合智能体：面向多本医学教材，完成教材来源管理、教材解析、知识图谱构建、跨教材整合压缩、带引用 RAG 问答和教师二次反馈迭代。

## 在线体验

- GitHub 仓库：[https://github.com/FangChengDong-zju/hacson_knowledge_agent_middle](https://github.com/FangChengDong-zju/hacson_knowledge_agent_middle)
- 公网部署：[https://hacson-knowledge-agent.streamlit.app](https://hacson-knowledge-agent.streamlit.app)
- 技术报告：[docs/技术报告.md](docs/技术报告.md)
- 评分点对照：[docs/评分点对照表.md](docs/评分点对照表.md)

云端部署无法访问本机 `E:/textbooks`，因此页面会提示本地路径不存在。评审可以使用页面中的上传入口，或查看仓库内的小型 demo 数据、整合报告和图谱证据。本地运行时会读取已解析的 7 本教材缓存。

## 一句话流程

```text
用户先提供教材来源
-> 可选填写个性化整合需求
-> Agent 生成整合文档与决策图谱
-> 用户基于文档和图谱继续反馈
-> Agent 更新整合决策、文档、图谱和审计记录
```

优先级规则：

```text
来源追溯硬约束 > 用户二次反馈 > 用户初始个性化需求 > Agent 默认整理模式
```

## 当前可演示功能

- 教材来源入口：支持指定本地路径或上传教材文件。
- 个性化整合需求：用户可输入课程目标、压缩偏好、必须保留或拆分的概念。
- 默认整理模式：用户不输入需求时，Agent 自动保留主干、合并重复、降级细节。
- 结构化整合决策：每条决策包含 action、reason、confidence、affected_sources。
- 30% 凝练版整合文档：主干内容压缩，细节进入索引。
- 决策图谱：从 `integration_decisions` 生成，而不是只展示裸关键词。
- 教师二次反馈：自然语言修改保留、拆分、合并、降级、图表索引等决策。
- RAG 问答：先查当前整合资料，再查教材原文 chunk，回答尽量带来源。
- 审计证据：提示词、JSON、报告、图谱和来源片段均可展开查看。

## 快速演示步骤

1. 打开公网部署链接：

   [https://hacson-knowledge-agent.streamlit.app](https://hacson-knowledge-agent.streamlit.app)

2. 在左侧选择：

   ```text
   教材整合：生成文档与图谱
   ```

3. 在“1. 教材来源”中选择：

   ```text
   指定本地路径
   ```

   云端会提示 `E:/textbooks` 不存在，这是正常现象；本地演示时该路径可用。

   若评审需要快速验证云端上传流程，可点击页面中的“下载 1 分钟演示教材素材”，再把下载的 MD 文件上传回页面。

4. 在底部输入框输入整合需求，例如：

   ```text
   面向临床见习学生，感染相关内容保留共同主干，病例细节降级为索引。
   ```

5. 点击或输入“生成整合文档与图谱”相关指令后，系统会准备真实整合 prompt。若填写 API Key，会调用 OpenAI-compatible LLM；未填写时仅预览输入，不编造结果。

6. 展开页面下方结果区：

   - 整合流程与指标
   - 整合结果：图谱
   - 整合结果：文档
   - 整合依据：决策记录
   - 整合依据：提示词与评审证据

7. 切换到：

   ```text
   资料问答：基于整合结果查询
   ```

   可测试带来源问答流程。

## 本地运行

推荐用 Streamlit 体验版作为主入口。

```powershell
cd hacson_knowledge_agent
.\run_streamlit_demo.ps1
```

访问：

```text
http://127.0.0.1:8502
```

如果不使用脚本，也可以手动安装依赖后运行：

```powershell
cd hacson_knowledge_agent
pip install -r requirements.txt
streamlit run streamlit_app.py --server.port 8502
```

LLM 配置在页面左侧输入：

```text
Base URL: https://chaoye.xyz
Model: gpt-5.4
API Key: 用户运行时手动输入
OpenAI-compatible API: 勾选
```

项目不会把 API Key 写入代码或文档。

## 仓库结构

```text
backend/                 FastAPI 后端骨架：解析、图谱、整合、RAG、反馈、报告
frontend/                React + Vite 前端骨架：图谱、问答、上传、决策面板
streamlit_app.py         当前公网演示主入口
run_streamlit_demo.ps1   本地 Streamlit 启动脚本
requirements.txt         Streamlit Cloud 部署依赖
backend/requirements.txt FastAPI 后端依赖
docs/                    需求、系统设计、Agent 架构、API、提示词设计
report/                  整合报告、图谱快照、解析闭环报告
scripts/                 教材解析、图谱构建、报告生成、验证脚本
data/demo/               小型 demo 决策、凝练教材、决策图谱和审计摘要
```

## 评分点与证据位置

| 评分点 | 说明 | 证据位置 |
|---|---|---|
| A1 README 可复现 | 启动、部署、配置、数据说明 | `README.md` |
| A2 需求分析 | 粒度、重复判定、压缩比、RAG 分块依据 | `docs/需求分析.md` |
| A3 系统设计/API | 架构、数据流、接口 | `docs/系统设计.md`, `docs/API接口文档.md` |
| A4 整合报告 | 7 本教材整合概览、压缩、案例、完整性 | `report/整合报告.md` |
| B1 多格式解析 | PDF/MD/TXT/DOCX 解析服务与脚本 | `backend/app/services/parser.py`, `report/local_textbook_loop_check.md` |
| B2 图谱构建 | 知识点抽取、节点边、来源索引 | `backend/app/services/extractor.py`, `scripts/build_graph_from_outlines.ps1` |
| B3 图谱交互 | 图谱展示、来源、缩放/拖拽候选图谱 | `streamlit_app.py`, `report/knowledge_graph_demo.html` |
| B4 跨教材整合 | merge/keep/remove/split/downgrade 决策 | `docs/LLM整合提示词设计.md`, `data/demo/integration_decisions_demo.json` |
| B5 RAG 问答 | 先查整合资料，再查教材 chunk，答案带引用 | `streamlit_app.py`, `backend/app/services/rag.py` |
| B6 教师反馈 | 多轮对话修改决策并更新图谱/文档 | `streamlit_app.py`, `backend/app/services/feedback.py` |
| C 图谱可视化 | 决策图谱与图谱快照 | `data/demo/decision_graph_demo.json`, `report/knowledge_graph_snapshot.svg` |
| D Agent 架构 | Orchestrator、模块职责、优先级、局限 | `docs/Agent架构说明.md` |
| E 工程规范 | 前后端分层、依赖、配置、脚本 | `backend/`, `frontend/`, `scripts/`, `.env.example` |

## 关键文档

- `docs/Agent架构说明.md`：核心评分文档，解释为什么采用模块化单 Orchestrator Agent。
- `docs/LLM整合提示词设计.md`：定义整合提示词、JSON schema、教师要求优先级和防幻觉约束。
- `docs/整合闭环证据.md`：逐步列出教材来源、整合决策、文档、图谱、二次反馈和问答的证据链。
- `docs/评分点对照表.md`：按官方 A-F 评分维度列出当前覆盖情况、证据位置和剩余边界。
- `docs/中期自查整改记录.md`：记录收到赛方中期自查后完成的部署、上传、证据链和文档整改。
- `docs/最终提交说明.md`：汇总最终提交链接、材料清单、演示路线和提交前检查项。
- `docs/系统设计.md`：系统架构、数据流和技术选型。
- `docs/API接口文档.md`：后端接口说明。
- `docs/赛题速查_学科知识整合智能体.md`：赛题要求、评分点和进度看板。
- `docs/项目上下文快照.md`：后续继续开发时优先读取，避免上下文丢失。
- `report/整合报告.md`：正式整合报告。

## 本地教材与数据安全

赛方教材位于本机：

```text
E:/textbooks
```

教材 PDF 和真实解析缓存不提交到 GitHub。

`.gitignore` 已排除：

```text
*.pdf
data/textbooks/*
data/processed/*.json
data/live/
data/demo/outlines_demo.json
data/demo/graph_demo.json
.env
.venv/
node_modules/
__pycache__/
```

仓库仅保留小型 demo 数据、报告和可复现脚本。`data/processed/textbooks.json` 是本地运行生成的数据，不进入公共仓库。

当前本地验证结果：

```text
7 本医学教材
2567 页
105 个章节/知识段
约 3,956,088 原始字符
约 1,883,215 存储字符
closed_loop_ready = true
```

证据：

```text
report/local_textbook_loop_check.md
report/整合报告.md
```

## 后端启动

后端目前作为正式架构骨架保留，Streamlit 是当前演示主线。

```powershell
cd hacson_knowledge_agent/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

健康检查：

```text
GET http://localhost:8000/api/health
```

## 前端启动

React/Vite 前端是正式前端骨架，当前中期演示优先使用 Streamlit。

```powershell
cd hacson_knowledge_agent/frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

## 生成报告

手动刷新正式整合报告：

```powershell
cd hacson_knowledge_agent
python .\scripts\build_final_report.py
```

输出：

```text
report/整合报告.md
```

运行 `.\run_streamlit_demo.ps1` 时也会自动刷新 demo 整合数据和正式整合报告。

## 当前边界

- 云端无法访问本机 `E:/textbooks`，需要上传文件或使用 demo 数据展示流程。
- 完整 7 本教材全量 LLM 分批整合尚未生产化；当前以真实主题批次链路验证 LLM JSON、来源追溯和图谱更新。
- RAG 目前以关键词检索和结构化片段为主，后续可接向量索引、BM25、rerank 和 benchmark。
- React/FastAPI 架构已搭建，中期演示以 Streamlit 保证部署和演示稳定。

## 后续开发入口

继续开发前优先读取：

```text
docs/项目上下文快照.md
```

评分点和执行优先级见：

```text
docs/赛题速查_学科知识整合智能体.md
```
