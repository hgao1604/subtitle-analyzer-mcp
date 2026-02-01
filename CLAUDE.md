# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Subtitle Analyzer MCP is a Model Context Protocol (MCP) server for extracting, analyzing, and searching subtitles from YouTube and Bilibili videos using `yt-dlp`. It enables Claude and other AI assistants to interact with video content programmatically.

## Build & Run Commands

```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run the MCP server
python -m src.server

# Run tests
pytest
```

## Architecture

```
src/
├── server.py            # MCP server entry point, exposes 4 tools
├── subtitle_extractor.py # yt-dlp wrapper, platform detection (YouTube/Bilibili)
└── analyzer.py          # SRT parsing, keyword search, timestamp utilities
```

### Key Components

- **SubtitleExtractor** (`subtitle_extractor.py`): Handles video platform detection, subtitle extraction via yt-dlp subprocess calls, format conversion, and video metadata retrieval
- **SubtitleAnalyzer** (`analyzer.py`): Parses SRT/VTT formats, provides keyword search with timestamps, chapter detection via gap analysis, and segment generation
- **MCP Server** (`server.py`): Async stdio-based server exposing 4 tools: `extract_subtitles`, `search_timestamp`, `get_video_info`, `list_available_subtitles`

### Design Patterns

- All I/O operations use async/await
- Platform abstraction via `detect_platform()` with regex-based URL matching
- `SubtitleEntry` dataclass for structured subtitle data
- Language fallback chain when preferred language unavailable

## External Dependencies

- **yt-dlp**: Required system binary for video/subtitle operations
- **Chrome**: Optional, needed for cookie extraction in local development

## Authentication

MCP servers run in background processes without access to browser cookies. Authentication uses a fallback chain:

1. `cookies_file` parameter (per-tool call)
2. `YT_DLP_COOKIES` environment variable (recommended for MCP)
3. `--cookies-from-browser chrome` (local development only)

Export cookies: `yt-dlp --cookies-from-browser chrome --cookies ~/.yt-cookies.txt --skip-download "https://youtube.com"`

## Platform Support

- YouTube: youtube.com, youtu.be, youtube.com/shorts
- Bilibili: bilibili.com/video, b23.tv

## MCP Registration

```bash
# Register with Claude Code (basic)
claude mcp add subtitle-analyzer -- python -m src.server --cwd /path/to/subtitle-analyzer-mcp

# Register with cookies authentication
claude mcp add subtitle-analyzer -- \
  env YT_DLP_COOKIES=/path/to/.yt-cookies.txt \
  python -m src.server --cwd /path/to/subtitle-analyzer-mcp
```
