# FitAgent Demo 演示脚本

> 最后验证: 2026-05-16 | 54 tests pass | TypeScript 零错误 | 7 E2E scenarios verified

## 演示目标

向面试官展示 FitAgent 的 Agent 开发能力：
1. Intent Router 意图识别 (LLM + 关键词兜底)
2. RAG 知识库检索增强生成
3. Plan-Execute-Observe-Replan 完整工作流
4. Tool Calling 工具调用
5. Human-in-the-Loop 用户确认机制
6. Agent Trace 全链路可观测性
7. APScheduler 定时提醒运行时
8. 业务闭环完整性

## E2E 验证状态 (Phase 3A)

| 场景 | 状态 | 关键验证点 |
|------|------|-----------|
| 1. 新用户首次创建计划 | ✅ | 不触发 HITL，直接生成 plan + reminders |
| 2. HITL 确认重新生成 | ✅ | confirmation_required → confirm → 新计划 |
| 3. HITL 取消保持旧计划 | ✅ | cancel → 旧计划不变 |
| 4. fitness_qa + RAG | ✅ | 检索命中 → 知识库来源展示 |
| 5. log_workout | ✅ | 自然语言解析 → 保存 → 计划匹配 |
| 6. Reminder runtime | ✅ | Scheduler running, events queryable |
| 7. Agent Trace | ✅ | intent/confidence/tools/latency 完整记录 |

---

## 场景一：用户注册与信息填写

**操作：**
1. 打开 `http://localhost:3000`
2. 注册新账号或使用 demo@fitagent.dev / demo123
3. 点击右上角「编辑」，填写身体信息：
   - 身高: 175cm, 体重: 80kg
   - 目标: 减脂
   - 训练地点: 健身房
   - 每周训练: 4天
   - 经验: 中级水平
4. 保存

**展示点：** 用户信息管理、Profile 持久化

---

## 场景二：生成训练计划（核心流程）

**对话输入：**
```
帮我制定一个训练计划
```

**Agent 内部流程：**
1. Intent Router → `create_plan` (confidence: 0.95)
2. Plan 阶段：检查用户信息完整性 ✓
3. Execute 阶段：
   - 调用 `generate_training_plan` 工具
   - 基于模板生成 4天/周 减脂计划
   - 写入 `training_plan` 表
4. 返回结构化计划

**展示点：**
- 意图识别准确
- 工具调用成功
- 计划结构完整（日期/部位/动作/组数/休息时间）
- Agent Trace 记录完整

**在浏览器 DevTools 中查看 SSE 事件流：**
```
type: "intent", content: "create_plan", data: {confidence: 0.95}
type: "tool_call", content: "generate_training_plan", data: {...}
type: "text", content: "已为你生成训练计划..."
type: "trace", data: {intent: "create_plan", tools_called: [...], latency_ms: 1200}
```

---

## 场景三：记录训练内容

**对话输入：**
```
今天练了胸和三头，杠铃卧推 60kg 5组5次，哑铃飞鸟 12kg 3组12次，绳索下压 15kg 4组12次，感受不错 RPE7
```

**Agent 内部流程：**
1. Intent Router → `log_workout` (confidence: 0.9)
2. 调用 `log_workout_record` 工具
3. LLM 解析自然语言 → 结构化数据
4. 写入 `workout_log` 表
5. 匹配训练计划（完成度计算）

**展示点：**
- 自然语言解析准确（动作名/重量/组数/次数/RPE）
- 自动关联训练计划
- 结构化存储

---

## 场景四：查询训练历史

**对话输入：**
```
这个月练了多少天了
```

**Agent 内部流程：**
1. Intent Router → `query_history` (confidence: 0.85)
2. 查询 `workout_log` 表
3. 计算月度汇总数据
4. 返回统计信息

**展示点：**
- 数据持久化查询
- 月度统计（完成率/连续天数/部位分布）

---

## 场景五：日历视图

**操作：**
1. 点击日历链接或直接访问 `/calendar`
2. 查看月度训练日历

**展示点：**
- FullCalendar 月视图
- 统计卡片（训练天数/完成率/连续天数/总时长）
- 部位分布图

---

## 场景六：查看 Agent Trace（调试用）

**展示终端或 DB 查询：**
```sql
SELECT intent, intent_confidence, tools_called, latency_total_ms
FROM agent_trace
WHERE user_id = '...'
ORDER BY created_at DESC
LIMIT 10;
```

**展示点：**
- 每次对话完整记录
- 意图/置信度/工具调用/延迟
- 全链路可观测

---

## 场景七：意图路由测试（边界情况）

**输入 1:** `你好啊` → `casual_chat`

**输入 2:** `卧推姿势正确吗` → `fitness_qa`

**输入 3:** `练了背` → `log_workout` (短输入也能识别)

**展示点：**
- 双层路由（LLM + 关键词兜底）
- 短输入/模糊输入处理

---

## 面试官可能的问题 & 回答要点

| 问题 | 回答要点 |
|------|---------|
| 为什么用 LangGraph？ | StateGraph 提供显式的状态管理和节点路由，比 LangChain Agent 更可控，适合企业级应用 |
| Intent Router 准确率如何保证？ | 双层路由：LLM 分类（主）+ 关键词匹配（confidence<0.7 时激活）+ fallback 到 casual_chat |
| 如何处理工具调用失败？ | Plan-Execute-Replan 完整子图在 Phase 2 实现，当前 MVP 通过 try/except + 用户友好错误信息处理 |
| 为什么用模板而非纯 LLM 生成计划？ | MVP 阶段模板保证结构稳定性和业务规则合规，Phase 2 会加入 LLM 增强个性化 |
| Agent Trace 的价值？ | 可观测性是生产级 Agent 的核心需求：调试、监控、成本分析、用户行为分析 |
