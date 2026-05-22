# FitAgent — 5 分钟面试讲稿

## 结构

- 0:00-0:45 — 项目定位
- 0:45-2:00 — 架构走读
- 2:00-3:30 — 三个核心亮点
- 3:30-4:30 — Live Demo
- 4:30-5:00 — 总结

---

## 0:00-0:45 — 项目定位

> "我做的是一个任务型 Agent 平台，叫 FitAgent。
>
> 它不是健身 App——它是一个 Agent Platform。
> 同一个 Agent Runtime 支持两种客户端：Web Chat 和 Claude Desktop (MCP)。
>
> 技术栈：FastAPI + LangGraph + Next.js + MCP。前后端都是我自己设计的。"

---

## 0:45-2:00 — 架构走读

> "核心架构分几层：
>
> **Intent Router**：双层路由。LLM 主分类 + 关键词兜底。confidence < 0.7 自动降级。
>
> **Plan-Execute-Observe-Replan**：任务型意图的完整工作流。
> Plan 校验信息 → Execute 调工具 → Observe 5 项验证 → Replan 四种处理。
>
> **Human-in-the-Loop**：覆盖已有计划这类高风险操作，会暂停执行，
> SSE 推送确认请求到前端。用户确认后才继续。取消则 DB 无写入。
>
> **Agent Trace**：每次对话的 intent / confidence / tools / latency 全量记录。"

---

## 2:00-3:30 — 三个核心亮点

> **1. MCP 协议集成**
> 4 个 tools、4 个 resources、5 个 prompts。手写 JSON-RPC 2.0 over stdio（SDK 有依赖冲突）。
> Claude Desktop 可以直接调用 FitAgent 生成计划、查询数据。
> Web Chat 和 Claude Desktop 共享同一个数据库。
>
> **2. RAG + 四层降级**
> 39 条精选知识，TF-IDF + Cosine 检索。
> LLM 不可用、检索无结果、两者都不可用——每种情况都有对应降级路径。
>
> **3. APScheduler 提醒运行时**
> 提醒不只是 DB 记录，会注册到 APScheduler cron job。
> 启动时从 DB 恢复所有 active jobs，重启不丢失。

---

## 3:30-4:30 — Live Demo

> 1. Web Chat: 注册 → 创建计划（看 PER 流程）
> 2. Web Chat: 再次创建 → 弹窗确认（看 HITL）
> 3. Web Chat: 健身问答（看 RAG + 来源）
> 4. Claude Desktop: 调用 generate_training_plan（看 MCP）
> 5. 查询 agent_trace 表（看可观测性）

---

## 4:30-5:00 — 总结

> "三点：
>
> 1. 我不是只调 LangChain API。Intent Router → PER → HITL → Trace 都是自己设计实现的
> 2. 我理解协议层。MCP 是理解 spec 后手写的，不是 SDK 套上去的
> 3. 项目有完整文档、117 tests、12 份文档——是按交付标准做的
>
> 如果你招会调 Agent 框架的人，这个项目展示了调用能力。
> 如果你招会设计 Agent 系统的人，这个项目展示了设计能力。"
