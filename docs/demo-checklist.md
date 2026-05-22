# FitAgent Demo Checklist

面试前逐项检查，避免翻车。

---

## 一、环境检查

### 1.1 后端启动

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

验证：`curl http://localhost:8001/health` 返回 `{"status":"ok"}`

### 1.2 前端启动

```bash
cd frontend
npm run dev
```

验证：浏览器打开 `http://localhost:3000`，显示登录页

### 1.3 数据库

验证：`curl http://localhost:8001/rag/stats` 返回 `{"indexed":true,"document_count":39}`

### 1.4 APScheduler

验证：`curl http://localhost:8001/api/v1/reminders/status` 返回 `{"scheduler_running":true}`

---

## 二、测试数据准备

### 2.1 Demo 用户

注册一个 demo 用户并填写完整 profile：

```bash
# 注册
curl -X POST http://localhost:8001/api/v1/user/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@fitagent.dev","password":"demo123","display_name":"Demo"}'

# 获取返回的 user_id，然后填写资料
curl -X PATCH http://localhost:8001/api/v1/user/{USER_ID} \
  -H "Content-Type: application/json" \
  -d '{"height_cm":175,"weight_kg":80,"goal":"fat_loss","training_location":"gym","weekly_days":4,"experience_level":"intermediate","preferred_time":"19:00"}'
```

### 2.2 可选：预创建训练计划

在 Demo 前先创建一条训练计划，用于展示 HITL 确认流程：

```
在 Web Chat 中发送："帮我制定一个减脂训练计划"
```

### 2.3 可选：预记录训练

```
"今天练了胸，卧推60kg 5x5，飞鸟12kg 3x12"
```

---

## 三、LLM API Key（可选）

如果配置了 `LLM_API_KEY`，回复会走真实 LLM。如果没配置，系统以模板模式运行，功能不受影响但回复质量下降。

**Demo 建议**：面试时配置 API Key，展示真实 AI 能力。

---

## 四、Claude Desktop MCP 检查

### 4.1 配置

1. 复制 `docs/claude-desktop-config.example.json`
2. 修改 `cwd` 和 `PYTHONPATH` 为实际路径
3. 放到 Claude Desktop config 目录
4. 重启 Claude Desktop

### 4.2 验证

在 Claude Desktop → Developer → MCP 中，应显示：
- fitagent (connected)
- 4 tools, 4 resources, 5 prompts

### 4.3 快速测试

在 Claude Desktop 中输入：
```
list the available tools from fitagent
```

如果 Claude 能列出 4 个 tool，说明集成成功。

---

## 五、Demo 顺序

### 快速版（5 分钟）

1. **Web Chat — 创建计划**（1 min）
   - 登录 → 发送"帮我制定训练计划"
   - 展示生成的周计划 + 提醒

2. **Web Chat — HITL 确认**（1 min）
   - 发送"重新生成一个训练计划"
   - 弹窗展示 → 确认
   - 新计划生成

3. **Web Chat — RAG 问答**（1 min）
   - 发送"新手一周练几次比较合适"
   - 展示知识库检索结果

4. **Claude Desktop — MCP**（1 min）
   - 输入"create a workout plan for me"
   - Claude 调用 generate_training_plan

5. **架构图讲解**（1 min）
   - 展示整体架构图
   - 强调双通道、PER、MCP 三个亮点

### 深度版（15 分钟）

在上述基础上补充：

6. **Agent Trace 展示**（2 min）
   - 查询 agent_trace 表
   - 展示 intent / confidence / tools / latency

7. **PER 深度讲解**（3 min）
   - per-workflow.md 的状态机图
   - Plan → Execute → Observe → Replan 四阶段

8. **MCP 协议层讲解**（3 min）
   - 手写 JSON-RPC 2.0 stdio
   - Adapter 模式
   - Tool vs Resource vs Prompt 区别

9. **HITL 时序图讲解**（2 min）
   - SSE 事件流
   - ConfirmationStore 内存存储
   - 为什么确认在 Execute 之前

---

## 六、常见翻车点

| 问题 | 原因 | 解决 |
|------|------|------|
| Web Chat 无法连接 | 后端未启动或端口错误 | `curl localhost:8001/health` |
| 注册失败 | DB 迁移未执行 | `alembic upgrade head` |
| RAG 无结果 | KB 未初始化 | `curl localhost:8001/rag/stats` |
| fitness_qa 被分到 casual_chat | 关键词未命中 | 改用"新手怎么练"、"减脂应该做什么" |
| Claude Desktop 看不到 fitagent | config 路径错误 | 检查 cwd 是绝对路径 |
| MCP tool 调用失败 | user_id 不存在 | 设置 MCP_DEMO_USER_ID |
| 前端白屏 | Node.js 版本过低 | 降级 Next.js 或升级 Node.js |
| 端口被占用 | 上次进程未关闭 | `pkill -f uvicorn` / `pkill -f "next dev"` |

---

## 七、翻车时的 fallback

| 场景 | Fallback |
|------|----------|
| 后端挂了 | 使用架构图 + 代码讲解代替 Live Demo |
| LLM API Key 过期 | 展示模板 fallback 逻辑（反而是个亮点） |
| Claude Desktop 不兼容 | 使用 `python scripts/test_mcp_stdio.py` 展示 MCP 协议验证通过 |
| 前端编译失败 | 使用 curl 命令演示 API 能力 |
| 数据库损坏 | 删除 fitagent.db，重新 `alembic upgrade head` 并注册新用户 |
