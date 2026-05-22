# FitAgent 部署指南

## 本地开发

```bash
# 0. 环境（仅首次）
conda env create -f environment.yml
conda activate fitagent

# 1. 后端
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

# 前端
cd frontend
npm install
npm run dev
```

访问: http://localhost:3000

## Docker 部署

```bash
# 启动 PostgreSQL + Redis
docker-compose up -d

# 切换 .env 为 PostgreSQL
# DATABASE_URL=postgresql+asyncpg://fitagent:fitagent@localhost:5432/fitagent

cd backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Claude Desktop MCP 配置

```json
{
  "mcpServers": {
    "fitagent": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/path/to/FitAgent/backend",
      "env": {
        "PYTHONPATH": "/path/to/FitAgent/backend",
        "MCP_DEMO_USER_ID": "your-user-id"
      }
    }
  }
}
```

配置文件位置:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

## 环境变量

| 变量 | 开发 (SQLite) | 生产 (PostgreSQL) |
|------|-------------|-------------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./fitagent.db` | `postgresql+asyncpg://user:pass@host/db` |
| `LLM_API_KEY` | `sk-...` (或空) | `sk-...` |
| `DEBUG` | `false` | `false` |
| `JWT_SECRET` | `change-me-in-production` | 随机 64 字符 |

## 生产环境建议

1. **数据库**: SQLite → PostgreSQL + pgvector (RAG 向量检索)
2. **调度**: APScheduler → Celery + Redis (多 worker)
3. **认证**: 当前 JWT 可用，生产加 OAuth2
4. **限流**: FastAPI middleware
5. **监控**: Agent Trace 表已有数据，加 Grafana dashboard
6. **容器化**: Dockerfile 已提供
