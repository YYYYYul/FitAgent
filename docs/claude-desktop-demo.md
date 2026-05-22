# FitAgent Claude Desktop MCP Demo 脚本

> MCP 协议验证: 9/9 passed | pytest: 104+ passed

## 前置准备

1. 配置 `claude_desktop_config.json`（参考 `docs/claude-desktop-config.example.json`）
2. 确保 `backend/fitagent.db` 有测试数据（至少一个用户 + 训练记录）
3. 重启 Claude Desktop

## 验证 MCP 连接

在 Claude Desktop 中打开 Developer Tools → MCP，应看到：
- fitagent (connected)
- 4 tools, 4 resources, 5 prompts

---

## Scenario 1: 调用 generate_training_plan tool

**用户输入:**
```
帮我生成一个减脂训练计划。我的信息：身高175，体重80，
在健身房训练，每周4天，中级水平。
```

**Claude 行为:**
1. 识别需要生成训练计划
2. 调用 `tools/call generate_training_plan`
3. 参数: `{goal:"fat_loss", height_cm:175, weight_kg:80, training_location:"gym", weekly_days:4, experience_level:"intermediate"}`
4. 接收 weekly_schedule JSON
5. 格式化为可读的 Markdown 计划表

**展示亮点:**
- Claude 自动从自然语言中提取 tool 参数
- 计划结构完整（每天的部位/动作/组数/休息时间）
- 与 Web Chat 端数据共享（同一 DB）

---

## Scenario 2: 调用 search_fitness_knowledge tool

**用户输入:**
```
新手一周应该练几次？每次多长时间？
```

**Claude 行为:**
1. 调用 `tools/call search_fitness_knowledge`
2. 参数: `{query:"新手一周应该练几次 每次多长时间", top_k:3}`
3. 接收 3 条知识库检索结果（含 title/content/category/score）
4. 基于检索结果生成回答，并引用来源

**预期输出:**
```
根据 FitAgent 知识库：

1. 新手第一个月的目标 — 建议从每周3次全身训练开始，每次45-60分钟
2. 训练频率的底线 — 即使再忙，每周至少保证2次训练
3. 不同水平的训练频率 — 新手建议每周训练3次

建议你从每周3次开始，逐步适应后增加到4-5次。
```

**展示亮点:**
- MCP Tool 调用 RAG 检索
- Claude 基于检索结果生成回答
- 知识来源可追溯（title + score）

---

## Scenario 3: 读取 fitness://active-plan resource

**用户输入:**
```
我现在是什么训练计划？帮我看看。
```

**Claude 行为:**
1. 调用 `resources/read fitness://active-plan?user_id=X`
2. 接收当前 active plan 的 JSON
3. 用自然语言总结计划内容

**预期输出:**
```
你当前的训练计划是：
- 目标：减脂
- 每周4天训练（周一/二/四/六）
- 地点：健身房
- 水平：中级
- 周一：上肢+有氧（胸/背/肩）
- 周二：下肢+有氧（腿）
- ...
```

**展示亮点:**
- Resource 是只读数据访问
- Claude 不需要知道 DB schema
- 与 Web Dashboard 数据一致

---

## Scenario 4: 使用 weekly-review prompt

**用户输入:**
```
帮我复盘这周的训练。
```

**Claude 行为:**
1. 调用 `prompts/get weekly-review`
2. 按照 workflow:
   a. `resources/read fitness://history/latest?user_id=X&limit=7`
   b. `resources/read fitness://active-plan?user_id=X`
3. 对比计划 vs 实际
4. 输出完成率、部位覆盖、建议

**预期输出:**
```
# 周度训练复盘

## 完成情况
- 计划训练: 4 天
- 实际完成: 3 天
- 完成率: 75%

## 部位覆盖
- 胸: 1次
- 背: 1次
- 腿: 1次
- （肩部未训练）

## 建议
- 下周注意补上肩部训练
- 连续训练3天，保持势头！
```

**展示亮点:**
- Prompt 驱动的多步骤 workflow
- Resource 组合分析
- 结构化 Markdown 输出

---

## Scenario 5: 查询 fitness://reminders/status resource

**用户输入:**
```
我的训练提醒还正常吗？
```

**Claude 行为:**
1. 调用 `resources/read fitness://reminders/status?user_id=X`
2. 接收: `{active_jobs:4, scheduler_running:true, ...}`
3. 用自然语言告知状态

**预期输出:**
```
你的训练提醒一切正常：
- 4个活跃提醒任务
- 调度器运行中
- 最近没有触发失败的记录
```

**展示亮点:**
- 基础设施状态查询
- Claude 可以诊断系统健康
- MCP 不只是业务数据，还能查运行时状态

---

## 面试话术建议

```
"FitAgent 不是传统的单体 AI 应用。
我设计了两条访问通道：
- Web Chat（用户在浏览器对话，走 HTTP SSE）
- MCP Protocol（外部 Agent 调用，走 JSON-RPC stdio）

它们共享同一个 Agent Runtime —— 同一套 Tool Layer、RAG、数据库。

这意味着：我在 Web Chat 创建的训练计划，Claude Desktop 通过 MCP 立即可见。
这展示了真正的 Agent Platform 架构思维，而不是简单的 API wrapper。"
```
