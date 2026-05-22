# FitAgent 手动设置指南

本文档覆盖所有需要手动操作的步骤。每个步骤按统一格式组织。

---

## 0. Conda 环境（推荐）

### 为什么需要

FitAgent 是 AI Agent 项目，依赖 LangGraph、RAG、embedding 等库。Conda 比 .venv 更适合：
- 管理 Python 版本本身（而不仅仅是包）
- 处理 numpy / scipy 等底层 C 扩展兼容性
- 与系统已有 Anaconda 工具链集成
- 后续接入 embedding / transformers 更顺畅

### 跳过会怎样

依赖安装到 base 环境，与 Spyder / Jupyter / 其他项目的包版本冲突（特别是 pydantic）。

### 创建环境

```bash
cd FitAgent
conda env create -f environment.yml
```

### 激活环境

```bash
conda activate fitagent
```

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 验证

```bash
conda info --envs | grep fitagent
# 应看到 fitagent 环境

python -c "import sys; print(sys.version)"
# 应输出 Python 3.11.x

python scripts/check-env.py
# [4b] 应显示 "Conda env 'fitagent' active"
```

### 退出环境

```bash
conda deactivate
```

### 删除重建

```bash
conda deactivate
conda env remove -n fitagent
conda env create -f environment.yml
```

### 备用方案 (.venv)

如果没有 Conda：
```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows
pip install -r backend/requirements.txt
```

---

## 1. Python 依赖

### 为什么需要

后端依赖 FastAPI、LangGraph、SQLAlchemy 等包。

### 跳过会怎样

后端启动报 `ModuleNotFoundError`。

### 操作步骤

```bash
cd backend
pip install -r requirements.txt
```

### 验证

```bash
python -c "from app.main import app; print('OK')"
```

### 常见问题

- **pydantic 版本冲突**: 不要安装 `mcp` SDK，MCP Server 是手写协议实现
- **aiosqlite 找不到**: `pip install aiosqlite -i https://pypi.org/simple/`

---

## 2. 数据库迁移

### 为什么需要

创建 SQLite 数据库文件和 7 张表。

### 跳过会怎样

任何数据访问都报 `OperationalError: no such table`。

### 操作步骤

```bash
cd backend
alembic upgrade head
```

### 验证

```bash
curl http://localhost:8001/rag/stats
# 应返回 {"indexed":true,"document_count":39}
```

---

## 3. LLM API Key（可选）

### 为什么需要

无 API Key 时系统以模板模式运行。Intent Router 用关键词匹配，casual_chat 用模板回复，fitness_qa 直接展示检索内容。

### 跳过会怎样

系统可正常运行，但回复是模板化而非 AI 生成。

### 操作步骤

1. 获取 DeepSeek API Key (https://platform.deepseek.com)
2. 编辑 `backend/.env`:
   ```
   LLM_API_KEY=sk-your-key
   LLM_BASE_URL=https://api.deepseek.com/v1
   LLM_MODEL=deepseek-chat
   ```

### 验证

发一条聊天消息，回复应是自然语言而非模板。

---

## 4. 后端启动

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

验证: `curl http://localhost:8001/health` 返回 `{"status":"ok"}`

常见问题: 端口占用 → 换端口 `--port 8002`；ModuleNotFoundError → 确认在 backend/ 目录下执行

---

## 5. 前端启动

```bash
cd frontend
npm install
npm run dev
```

验证: 浏览器打开 `http://localhost:3000`，显示登录页

常见问题: Node.js 版本 < 20 → 降级 Next.js `npm install next@15.1.0`；端口占用 → `npm run dev -- -p 3001`

---

## 6. MCP Demo 用户

MCP Resources 和 Tools 需要有效的 user_id。

### 操作步骤

1. 通过 Web Chat 或 API 注册用户
2. 将返回的 user_id 写入 `.env`: `MCP_DEMO_USER_ID=xxx`

### 验证

`curl http://localhost:8001/api/v1/user/{USER_ID}` 返回用户信息

---

## 7. Claude Desktop 集成

### 操作步骤

1. 复制 `docs/claude-desktop-config.example.json`
2. 修改 `cwd` 和 `PYTHONPATH` 为实际路径
3. 放到 Claude Desktop config 目录
4. 重启 Claude Desktop

### 验证

Claude Desktop → Developer → MCP → 显示 fitagent (connected), 4 tools, 4 resources, 5 prompts

---

## 8. RAG 知识库

随 FastAPI 启动自动初始化。手动初始化：

```bash
cd backend
python -c "from app.core.rag.knowledge_base import init_knowledge_base; init_knowledge_base()"
```

验证: `curl http://localhost:8001/rag/stats`

---

## 9. APScheduler

随 FastAPI 启动自动启动。从 DB 恢复所有 active reminder jobs。

验证: `curl http://localhost:8001/api/v1/reminders/status` 返回 `{"scheduler_running":true}`

---

## 10. 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./fitagent.db` | 数据库连接串 |
| `LLM_API_KEY` | `""` | LLM API Key (空=模板模式) |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM API 地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `JWT_SECRET` | `change-me-in-production` | JWT 签名密钥 |
| `MCP_DEMO_USER_ID` | `""` | MCP 默认用户 |
