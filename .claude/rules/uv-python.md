# UV Python 工具使用规范

## 什么是 uv

uv 是一个快速的 Python 包管理器和项目管理工具，替代 pip、pip-tools、virtualenv 等。

## 常用命令

### 依赖管理

```bash
# 同步依赖（读取 pyproject.toml，安装到 .venv）
uv sync

# 添加依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>

# 移除依赖
uv remove <package>

# 更新依赖
uv lock --upgrade
uv sync
```

### 运行命令

```bash
# 在项目虚拟环境中运行命令
uv run <command>

# 运行 Python 脚本
uv run python script.py

# 运行模块
uv run python -m <module>

# 指定目录运行
uv run --directory /path/to/project python -m <module>
```

### 项目初始化

```bash
# 初始化新项目
uv init

# 从现有 requirements.txt 迁移
uv pip compile requirements.txt -o requirements.lock
```

## 最佳实践

1. **优先使用 uv run** - 不需要手动激活虚拟环境
2. **uv sync 后再运行** - 确保依赖是最新的
3. **提交 uv.lock** - 锁定依赖版本，保证可重现性

## 与其他工具对比

| 操作 | pip/venv | uv |
|-----|----------|-----|
| 创建虚拟环境 | `python -m venv .venv` | `uv venv` (自动) |
| 安装依赖 | `pip install -e .` | `uv sync` |
| 运行脚本 | `source .venv/bin/activate && python` | `uv run python` |
| 添加依赖 | 编辑 requirements.txt + pip install | `uv add <pkg>` |

## MCP 服务器配置示例

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/project", "python", "-m", "src.server"]
    }
  }
}
```
