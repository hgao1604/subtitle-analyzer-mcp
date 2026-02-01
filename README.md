# Subtitle Analyzer MCP

基于 yt-dlp 的字幕分析 MCP 服务器，支持 YouTube 和 Bilibili 平台。

## 功能特性

- 🎬 **字幕提取** - 从视频提取字幕（支持手动字幕和自动生成字幕）
- 🔍 **时间戳搜索** - 搜索关键词并定位到具体时间点
- 📋 **视频信息** - 获取视频标题、时长、描述等元信息
- 🌍 **多语言支持** - 支持中文、英文、日文等多种语言字幕

## 安装

### 前置要求

1. Python 3.10+
2. yt-dlp（系统级安装）

```bash
# 安装 yt-dlp
pip install yt-dlp
# 或者使用 brew (macOS)
brew install yt-dlp
```

### 安装 MCP

```bash
# 克隆或下载项目
cd subtitle-analyzer-mcp

# 安装依赖
pip install -e .
```

## 配置

### Claude Desktop

编辑配置文件：
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "subtitle-analyzer": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/subtitle-analyzer-mcp"
    }
  }
}
```

或者使用 uv（推荐）：

```json
{
  "mcpServers": {
    "subtitle-analyzer": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/subtitle-analyzer-mcp", "python", "-m", "src.server"]
    }
  }
}
```

### Claude Code

```bash
# 添加 MCP 服务器
claude mcp add subtitle-analyzer -- python -m src.server --cwd /path/to/subtitle-analyzer-mcp
```

## 使用示例

### 1. 提取字幕

```
请提取这个视频的字幕：https://www.youtube.com/watch?v=xxxxx
```

### 2. 搜索时间戳

```
在这个视频中搜索"机器学习"出现的位置：https://www.bilibili.com/video/BVxxxxx
```

### 3. 获取视频信息

```
获取这个视频的基本信息：https://www.youtube.com/watch?v=xxxxx
```

### 4. 内容摘要（配合 Claude 使用）

```
提取这个视频的字幕并生成摘要：https://www.youtube.com/watch?v=xxxxx
```

## 工具列表

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `extract_subtitles` | 提取字幕 | url, lang, format |
| `search_timestamp` | 搜索关键词时间戳 | url, keywords, context_lines |
| `get_video_info` | 获取视频信息 | url |
| `list_available_subtitles` | 列出可用字幕 | url |

## 常见问题

### Q: Bilibili 视频无法提取字幕？

A: Bilibili 部分视频需要登录才能访问字幕。可以尝试：
1. 使用 `--cookies-from-browser chrome` 参数（已内置）
2. 导出 cookies 文件并配置

### Q: 提示"无法提取字幕"？

A: 可能原因：
1. 视频本身没有字幕
2. 使用 `list_available_subtitles` 工具检查可用字幕
3. 网络连接问题

### Q: 自动字幕质量不好？

A: 自动生成的字幕（ASR）质量取决于平台算法。建议：
1. 优先使用手动上传的字幕
2. 使用 `list_available_subtitles` 查看可用选项

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 本地测试服务器
python -m src.server
```

## License

MIT License
