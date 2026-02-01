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

## 认证配置

YouTube 和 Bilibili 的部分视频需要登录才能访问。由于 MCP 服务器运行在后台进程中，无法直接访问浏览器 cookies，因此需要预先导出 cookies 文件。

### 认证优先级

系统按以下优先级查找认证信息：

1. **cookies_file 参数** - 工具调用时直接指定
2. **YT_DLP_COOKIES 环境变量** - 推荐用于 MCP 环境
3. **浏览器 cookies** - 仅本地开发环境可用

### 导出 Cookies 文件

```bash
# 从 Chrome 导出 cookies（需要先登录 YouTube/Bilibili）
yt-dlp --cookies-from-browser chrome --cookies ~/.yt-cookies.txt \
  --skip-download "https://www.youtube.com"

# 设置文件权限（保护敏感信息）
chmod 600 ~/.yt-cookies.txt
```

> ⚠️ **注意**: Cookies 会过期（通常 1-2 周），需要定期重新导出。

### 配置方式

#### 方式 1: 环境变量（推荐）

```bash
# 在 shell 配置文件中添加 (~/.zshrc 或 ~/.bashrc)
export YT_DLP_COOKIES=~/.yt-cookies.txt
```

#### 方式 2: Claude Desktop 配置

```json
{
  "mcpServers": {
    "subtitle-analyzer": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/subtitle-analyzer-mcp",
      "env": {
        "YT_DLP_COOKIES": "/Users/yourname/.yt-cookies.txt"
      }
    }
  }
}
```

#### 方式 3: Claude Code 配置

```bash
# 注册时通过 env 命令注入环境变量
claude mcp add subtitle-analyzer -- \
  env YT_DLP_COOKIES=/path/to/.yt-cookies.txt \
  python -m src.server --cwd /path/to/subtitle-analyzer-mcp
```

#### 方式 4: 工具调用时指定

在调用工具时直接传入 `cookies_file` 参数：

```json
{
  "url": "https://www.youtube.com/watch?v=xxxxx",
  "cookies_file": "/path/to/.yt-cookies.txt"
}
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
| `extract_subtitles` | 提取字幕 | url, lang?, format?, cookies_file? |
| `search_timestamp` | 搜索关键词时间戳 | url, keywords, context_lines?, cookies_file? |
| `get_video_info` | 获取视频信息 | url, cookies_file? |
| `list_available_subtitles` | 列出可用字幕 | url, cookies_file? |

> 带 `?` 的参数为可选参数

## 常见问题

### Q: MCP 环境下提示认证失败或无法访问？

A: MCP 服务器运行在后台进程，无法直接访问浏览器 cookies。解决方法：

1. 导出 cookies 文件：
   ```bash
   yt-dlp --cookies-from-browser chrome --cookies ~/.yt-cookies.txt \
     --skip-download "https://www.youtube.com"
   ```
2. 配置 `YT_DLP_COOKIES` 环境变量（见[认证配置](#认证配置)章节）

### Q: Bilibili 视频无法提取字幕？

A: Bilibili 部分视频需要登录才能访问字幕。请参考[认证配置](#认证配置)章节设置 cookies。

### Q: 提示"无法提取字幕"？

A: 可能原因：
1. 视频本身没有字幕 - 使用 `list_available_subtitles` 工具检查
2. 需要登录认证 - 配置 cookies 文件
3. 网络连接问题
4. Cookies 已过期 - 重新导出 cookies 文件

### Q: 自动字幕质量不好？

A: 自动生成的字幕（ASR）质量取决于平台算法。建议：
1. 优先使用手动上传的字幕
2. 使用 `list_available_subtitles` 查看可用选项

### Q: Cookies 多久需要更新一次？

A: 通常 1-2 周后 cookies 会过期，届时需要重新执行导出命令。如果突然出现认证失败，请先尝试重新导出 cookies。

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
