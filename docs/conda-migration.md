# FitAgent Conda 环境迁移说明

## 为什么从 .venv 改为 Conda

FitAgent 是 AI Agent 项目。后续可能接入：
- text-embedding-3-small 或本地 embedding 模型
- numpy / scikit-learn / transformers
- 更复杂的 RAG 管道与向量检索

这些库涉及底层 C 扩展和 CUDA 依赖。Conda 管理这些比 pip + venv 更稳定。当前系统已安装 Anaconda，直接利用现有工具链。

## 当前推荐方案

| 优先级 | 方案 | 适用场景 |
|--------|------|---------|
| **1 (推荐)** | Conda (`fitagent` env, Python 3.11) | 有 Anaconda/Miniconda 时 |
| 2 (备用) | .venv (`python -m venv .venv`, Python 3.10+) | 无 Conda 时 |

## 从旧环境迁移

### 如果你之前在 base 环境中运行

```bash
# 1. 创建隔离环境
conda env create -f environment.yml

# 2. 激活
conda activate fitagent

# 3. 重装依赖
cd backend
pip install -r requirements.txt

# 4. 验证
python scripts/check-env.py
```

base 环境中的旧包不会自动删除，但也不会影响新环境。如果需要清理 base：
```bash
conda activate base
# 手动 pip uninstall 不需要的包，或重建 base
```

### 如果你之前创建了 .venv

.venv 可以保留作为备用（已在 .gitignore 中）。Conda 环境完全独立，互不影响。

## 常见 Conda 问题

### conda 命令找不到

确认 Anaconda Prompt 或 conda 已加入 PATH。在 PowerShell 中：
```bash
conda init powershell
# 重启 PowerShell
```

### 创建环境很慢

conda 需要解析依赖关系，可能比 pip 慢。耐心等待。失败时：
```bash
conda clean --all
conda env create -f environment.yml
```

### pip 与 conda 混用原则

- conda 装 Python 版本 + 基础包（fastapi, sqlalchemy, numpy 等）
- pip 装 conda 没有的包（langgraph, openai 等）
- 先 conda install，后 pip install
- 不要用 pip 升级 conda 管理的包

### PowerShell 执行策略

如果报错 "无法加载文件...禁止运行脚本"：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### VSCode 识别 Conda 环境

`Ctrl+Shift+P` → `Python: Select Interpreter` → 选择 `fitagent` 环境。
