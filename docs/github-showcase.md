# FitAgent GitHub 展示指南

---

## 仓库描述（GitHub Description）

```
任务型健身 Agent 平台。支持 Intent Router / PER 工作流 / HITL / RAG / MCP 双通道。
FastAPI + LangGraph + Next.js。117 tests。Claude Desktop 兼容。
```

## 推荐 Tags

`agent` `langgraph` `mcp` `fastapi` `nextjs` `rag` `hitl` `python` `typescript` `fitness`

## About 侧栏

```
FitAgent — 任务型 Agent 平台

- Intent Router (LLM + keyword fallback)
- Plan-Execute-Observe-Replan
- Human-in-the-Loop
- RAG (TF-IDF + Cosine)
- MCP (Tools + Resources + Prompts)
- Agent Trace
- Claude Desktop Integration
```

## Pinned Repo 文案（用于个人主页）

```
FitAgent — 任务型健身 Agent 平台

自建 Intent Router + PER 工作流 + HITL 确认 + RAG 知识库 + MCP 双通道架构。
手写 JSON-RPC 2.0 stdio MCP 协议实现，兼容 Claude Desktop。
FastAPI + LangGraph + Next.js | 117 tests | 12 份文档。
```

## 推荐截图列表

| 截图 | 内容 |
|------|------|
| 1. architecture.png | `docs/architecture/overall-architecture.md` 的 Mermaid 图 |
| 2. chat-ui.png | Web Chat 界面（创建计划后的回复） |
| 3. hitl-modal.png | HITL 确认弹窗 |
| 4. calendar.png | FullCalendar 月视图 + 统计卡片 |
| 5. mcp-demo.png | Claude Desktop 调用 FitAgent tool 的截图 |
| 6. trace.png | Agent Trace 数据库查询结果 |
| 7. test-pass.png | pytest 117 passed 截图 |
| 8. architecture-per.png | PER 状态机图 |

## 推荐 Demo GIF

| GIF | 内容 |
|-----|------|
| 1. web-chat-flow.gif | 注册 → 创建计划 → HITL 确认 → 完整回复 |
| 2. mcp-claude.gif | Claude Desktop 调用 FitAgent tool |
| 3. hitl-cancel.gif | 弹窗 → 取消 → 旧计划保持不变 |

## README 首屏建议

打开 README 后，访客应在前两屏看到：
1. 一句话定位（Agent 平台，非健身 App）
2. Mermaid 架构图
3. Quick Start 命令
4. 核心设计表格

不需要翻很久才能理解项目是什么。

## 面试时如何展示 GitHub

1. **打开仓库首页** — 先让面试官看 README 架构图
2. **滚动到 MCP 部分** — 强调双通道设计
3. **打开 docs/architecture/** — 展示 5 张 Mermaid 图
4. **打开 tests/** — 展示测试覆盖
5. **打开 CLAUDE.md** — 展示项目规范（加分项）
6. **如果有 Demo 视频** — 在 README 顶部嵌入链接

## 仓库设置检查

- [ ] Description 已填写
- [ ] Topics 已添加
- [ ] About 侧栏有项目链接
- [ ] README 在首屏显示架构图
- [ ] License 文件存在
- [ ] 没有 .env 文件泄露 API Key
- [ ] 没有 node_modules / __pycache__ 提交
- [ ] .gitignore 覆盖 Python + Node
