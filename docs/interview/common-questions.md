# FitAgent — 面试常见问题

## Agent 架构

### Q: Agent 和 ChatBot 的区别？

ChatBot 是单轮无状态对话。Agent 有四层关键区别：
1. Intent Router：理解意图，路由到不同处理流程
2. Tool Calling：不只是回复文本，而是执行动作
3. Plan-Execute-Replan：不是一次性输出，而是规划→执行→观察→重规划
4. Long-term Memory：跨会话持久化用户状态

### Q: 为什么用 LangGraph 而不是 LangChain Agent？

LangChain AgentExecutor 是黑盒。LangGraph StateGraph 提供显式状态管理、节点级可观测性、条件路由和循环边——PER 子图需要这些能力。

### Q: Intent Router 准确率怎么保证？

双层路由：LLM 分类（结构化 JSON + confidence）+ 关键词兜底（19 个中文健身关键词，confidence < 0.7 时激活）+ 最终 fallback 到 casual_chat。即使 LLM 不可用，系统仍能运行。

---

## MCP

### Q: 为什么做 MCP？用什么 SDK？

MCP 是 Anthropic 的 Agent-to-Agent 通信标准。做 MCP 展示了你的系统不只是给人类用的，也是给其他 Agent 用的。

**没用 SDK。** SDK 的 pydantic 版本要求与项目冲突。手写 JSON-RPC 2.0 over stdio 约 300 行。这比用 SDK 更能证明对协议层的理解。

### Q: Web Chat 和 MCP 的数据一致性？

共享同一个数据库。Web Chat 创建的计划和 Claude Desktop 查询的是同一张 training_plan 表。不存在同步问题——只有一个数据源。

### Q: Tool / Resource / Prompt 的区别？

- Tool：执行动作（创建计划）——有副作用
- Resource：读取状态（当前计划）——只读
- Prompt：工作流模板（告诉 Claude 如何组合 Tool 和 Resource）

---

## RAG

### Q: RAG 为什么只用于 fitness_qa？

有意的设计选择。RAG 有检索延迟，不应该加到所有意图上。casual_chat 不需要知识库，create_plan 用模板生成，log_workout 做 LLM 解析。

### Q: 为什么用 TF-IDF 而不是向量数据库？

39 条文档规模下 TF-IDF + Cosine 精度足够，且零外部依赖。检索接口签名不变，后续可切换 pgvector。

---

## PER

### Q: Replan 的边界是什么？

4 种动作：request_input / retry_once / simple_fix / graceful_fail。MAX_REPLANS=1。**不自动做**：提高训练强度、修改用户长期偏好、连续多次重试。

### Q: 为什么 HITL 在 Plan 之后、Execute 之前？

这是正确的插入点。Plan 后已知要做什么但还没做。取消不需要回滚——DB 无写入。确认在 Execute 之后的话取消需要回滚。

---

## 可观测性

### Q: Agent Trace 记录什么？

intent + confidence + plan_steps + tools_called + replan_reason + final_response + latency_ms。每次对话一条记录。生产环境中这是调试、监控、成本分析的基础。

---

## 生产就绪

### Q: 这个项目能上生产吗？

当前是 Demo/MVP 级别。上生产需要：SQLite → PostgreSQL + pgvector、APScheduler → Celery + Redis、加 rate limiting、容器化部署。但 Demo 项目的目标不是"能上生产"，而是"展示能指导生产决策的架构能力"。
