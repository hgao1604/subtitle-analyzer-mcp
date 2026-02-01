#!/usr/bin/env python3
"""
Subtitle Analyzer MCP Server
基于 yt-dlp 的字幕分析 MCP 服务器
支持 YouTube 和 Bilibili 平台
"""

import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .subtitle_extractor import SubtitleExtractor
from .analyzer import SubtitleAnalyzer

# 创建服务器实例
server = Server("subtitle-analyzer")

# 全局实例
extractor = SubtitleExtractor()
analyzer = SubtitleAnalyzer()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的工具"""
    return [
        Tool(
            name="extract_subtitles",
            description="""从视频 URL 提取字幕。
支持平台：YouTube、Bilibili
返回：完整字幕文本，包含时间戳

认证配置（按优先级）：
1. cookies_file 参数
2. YT_DLP_COOKIES 环境变量
3. 浏览器 cookies（仅本地环境）

参数：
- url: 视频链接 (必填)
- lang: 首选字幕语言，如 'zh', 'en', 'ja' (可选，默认自动检测)
- format: 输出格式 'text' (纯文本) 或 'srt' (带时间戳) (可选，默认 'srt')
- cookies_file: cookies 文件路径，用于认证需要登录的视频 (可选)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "视频 URL (YouTube 或 Bilibili)"
                    },
                    "lang": {
                        "type": "string",
                        "description": "首选字幕语言代码，如 zh, en, ja",
                        "default": "zh"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["text", "srt"],
                        "description": "输出格式：text (纯文本) 或 srt (带时间戳)",
                        "default": "srt"
                    },
                    "cookies_file": {
                        "type": "string",
                        "description": "cookies 文件路径，用于认证需要登录的视频"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="search_timestamp",
            description="""在字幕中搜索关键词，返回匹配的时间戳位置。
用于快速定位视频中提到某个话题的时间点。

认证配置（按优先级）：
1. cookies_file 参数
2. YT_DLP_COOKIES 环境变量
3. 浏览器 cookies（仅本地环境）

参数：
- url: 视频链接 (必填)
- keywords: 要搜索的关键词列表 (必填)
- context_lines: 返回匹配位置前后的上下文行数 (可选，默认 2)
- cookies_file: cookies 文件路径，用于认证需要登录的视频 (可选)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "视频 URL"
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要搜索的关键词列表"
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "返回匹配位置前后的上下文行数",
                        "default": 2
                    },
                    "cookies_file": {
                        "type": "string",
                        "description": "cookies 文件路径，用于认证需要登录的视频"
                    }
                },
                "required": ["url", "keywords"]
            }
        ),
        Tool(
            name="get_video_info",
            description="""获取视频的基本信息，包括标题、时长、描述等。

认证配置（按优先级）：
1. cookies_file 参数
2. YT_DLP_COOKIES 环境变量
3. 浏览器 cookies（仅本地环境）

参数：
- url: 视频链接 (必填)
- cookies_file: cookies 文件路径，用于认证需要登录的视频 (可选)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "视频 URL"
                    },
                    "cookies_file": {
                        "type": "string",
                        "description": "cookies 文件路径，用于认证需要登录的视频"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="list_available_subtitles",
            description="""列出视频可用的所有字幕语言。
用于了解视频有哪些字幕可以提取。

认证配置（按优先级）：
1. cookies_file 参数
2. YT_DLP_COOKIES 环境变量
3. 浏览器 cookies（仅本地环境）

参数：
- url: 视频链接 (必填)
- cookies_file: cookies 文件路径，用于认证需要登录的视频 (可选)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "视频 URL"
                    },
                    "cookies_file": {
                        "type": "string",
                        "description": "cookies 文件路径，用于认证需要登录的视频"
                    }
                },
                "required": ["url"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """处理工具调用"""
    
    try:
        if name == "extract_subtitles":
            url = arguments["url"]
            lang = arguments.get("lang", "zh")
            fmt = arguments.get("format", "srt")
            cookies_file = arguments.get("cookies_file")

            result = await extractor.extract(url, lang, fmt, cookies_file)
            return [TextContent(type="text", text=result)]

        elif name == "search_timestamp":
            url = arguments["url"]
            keywords = arguments["keywords"]
            context_lines = arguments.get("context_lines", 2)
            cookies_file = arguments.get("cookies_file")

            # 先提取字幕
            subtitles = await extractor.extract(url, format="srt", cookies_file=cookies_file)
            # 搜索关键词
            results = analyzer.search_keywords(subtitles, keywords, context_lines)
            return [TextContent(type="text", text=results)]

        elif name == "get_video_info":
            url = arguments["url"]
            cookies_file = arguments.get("cookies_file")
            info = await extractor.get_video_info(url, cookies_file)
            return [TextContent(type="text", text=json.dumps(info, ensure_ascii=False, indent=2))]

        elif name == "list_available_subtitles":
            url = arguments["url"]
            cookies_file = arguments.get("cookies_file")
            subs = await extractor.list_subtitles(url, cookies_file)
            return [TextContent(type="text", text=json.dumps(subs, ensure_ascii=False, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"错误: {str(e)}")]


def main():
    """主入口"""
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    
    asyncio.run(run())


if __name__ == "__main__":
    main()
