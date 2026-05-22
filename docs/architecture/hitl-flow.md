# Human-in-the-Loop 确认机制

## 时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant FE as 前端
    participant BE as 后端
    participant PER as PER Orchestrator
    participant STORE as ConfirmationStore

    U->>FE: "重新生成训练计划"
    FE->>BE: POST /chat/stream
    BE->>PER: per_orchestrator_node(state)
    PER->>PER: Plan Node: 检查 active_plan
    Note over PER: active_plan 存在 → requires_confirmation=True

    PER-->>BE: {requires_confirmation, confirmation_context}
    BE->>STORE: save_pending(session_id, state)
    BE-->>FE: SSE: confirmation_required

    FE->>FE: 显示 ConfirmationModal
    FE->>FE: 禁用 ChatInput

    U->>FE: 点击"确认"

    FE->>BE: POST /chat/confirm {session_id, confirmed:true}
    BE->>STORE: get_pending(session_id)
    STORE-->>BE: 保存的 state
    BE->>PER: per_orchestrator_node(state, confirmed=True)

    PER->>PER: Execute → Observe
    PER-->>BE: final_response + tools_called

    BE-->>FE: SSE: tool_call → text → done
    FE->>FE: 关闭弹窗, 恢复 ChatInput
```

## 设计决策

### 为什么确认在 Execute 之前

Plan 之后已经知道要做什么，但还没执行。用户取消时不需要回滚——DB 没有任何写入。如果确认在 Execute 之后，取消需要回滚已写入的数据。

### 为什么用内存存储

确认状态是暂时的（300s 超时），不需要持久化。如果服务重启，用户重新发起请求即可。加 DB 表是过度设计。

### 为什么用 SSE 推送

前端不轮询，由服务端通过 `type: "confirmation_required"` SSE 事件主动推送。更低的延迟和服务器负载。

## ConfirmationStore API

```python
save_pending(session_id, user_id, state, target, context)
get_pending(session_id) → dict | None  # 自动清理过期
delete_pending(session_id) → bool
```

## 确认目标

| Target | 触发条件 | 影响 |
|--------|---------|------|
| plan_regeneration | create_plan + 已有 active_plan | 覆盖当前计划 |
| workout_deletion | (待实现) | 不可逆删除 |
| reminder_change | (待实现) | 影响持续性调度 |

## Agent Trace

每次确认事件记录:
- confirmation_target: 确认什么
- confirmation_result: required / confirmed / cancelled / timeout
- confirmation_waited_ms: 用户响应时间
