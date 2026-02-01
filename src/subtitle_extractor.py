"""
字幕提取模块
- YouTube: 使用 yt-dlp
- Bilibili: 使用 yt-dlp
"""

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional


class SubtitleExtractor:
    """字幕提取器"""

    # 支持的平台正则
    PLATFORM_PATTERNS = {
        "youtube": [
            r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([\w-]+)",
            r"(?:https?://)?(?:www\.)?youtu\.be/([\w-]+)",
            r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]+)"
        ],
        "bilibili": [
            r"(?:https?://)?(?:www\.)?bilibili\.com/video/(?:av\d+|BV[\w]+)",
            r"(?:https?://)?(?:www\.)?b23\.tv/[\w]+"
        ]
    }

    def detect_platform(self, url: str) -> Optional[str]:
        """检测视频平台"""
        for platform, patterns in self.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, url, re.IGNORECASE):
                    return platform
        return None

    def _build_auth_args(self, cookies_file: Optional[str] = None) -> list[str]:
        """构建 yt-dlp 认证参数"""
        if cookies_file:
            expanded_path = os.path.expanduser(cookies_file)
            if Path(expanded_path).exists():
                return ["--cookies", expanded_path]

        env_cookies = os.environ.get("YT_DLP_COOKIES")
        if env_cookies:
            expanded_path = os.path.expanduser(env_cookies)
            if Path(expanded_path).exists():
                return ["--cookies", expanded_path]

        return ["--cookies-from-browser", "chrome"]

    def _vtt_to_text(self, vtt_content: str) -> str:
        """将 VTT/SRT 格式转换为纯文本"""
        lines = []
        for line in vtt_content.split("\n"):
            line = line.strip()
            # 跳过时间戳、序号、WEBVTT 头
            if not line or re.match(r"^\d+$", line):
                continue
            if re.match(r"^\d{2}:\d{2}:\d{2}", line):
                continue
            if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # 移除 HTML 标签
            clean_line = re.sub(r"<[^>]+>", "", line)
            if clean_line:
                lines.append(clean_line)
        return "\n".join(lines)

    async def _extract_with_ytdlp(
        self, url: str, lang: str, format: str, cookies_file: Optional[str]
    ) -> str:
        """使用 yt-dlp 提取字幕"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = str(Path(tmpdir) / "subtitle")

            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", f"{lang},zh,zh-Hans,zh-CN,en,ja",
                "--sub-format", "vtt/srt/best",
                "-o", output_template,
                url
            ]

            cmd.extend(self._build_auth_args(cookies_file))

            env = os.environ.copy()
            env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '/usr/bin:/bin')}"

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()

            tmppath = Path(tmpdir)
            subtitle_files = list(tmppath.glob("*.vtt")) or list(tmppath.glob("*.srt"))

            if not subtitle_files:
                error_msg = stderr.decode() if stderr else "未知错误"
                raise ValueError(f"无法提取字幕: {error_msg}")

            subtitle_content = subtitle_files[0].read_text(encoding="utf-8")

            if format == "text":
                return self._vtt_to_text(subtitle_content)
            return subtitle_content

    async def extract(
        self,
        url: str,
        lang: str = "zh",
        format: str = "srt",
        cookies_file: Optional[str] = None
    ) -> str:
        """
        提取字幕

        Args:
            url: 视频 URL
            lang: 首选语言代码
            format: 输出格式 ('text' 或 'srt')
            cookies_file: cookies 文件路径

        Returns:
            字幕文本
        """
        platform = self.detect_platform(url)
        if not platform:
            raise ValueError(f"不支持的视频平台，URL: {url}")

        return await self._extract_with_ytdlp(url, lang, format, cookies_file)

    async def get_video_info(
        self, url: str, cookies_file: Optional[str] = None
    ) -> dict:
        """获取视频信息"""
        platform = self.detect_platform(url)

        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            url
        ]

        cmd.extend(self._build_auth_args(cookies_file))

        env = os.environ.copy()
        env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '/usr/bin:/bin')}"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise ValueError(f"获取视频信息失败: {stderr.decode()}")

        data = json.loads(stdout.decode())

        return {
            "title": data.get("title", "未知"),
            "duration": data.get("duration", 0),
            "duration_string": data.get("duration_string", "00:00"),
            "uploader": data.get("uploader", "未知"),
            "upload_date": data.get("upload_date", "未知"),
            "view_count": data.get("view_count", 0),
            "description": data.get("description", "")[:500],
            "platform": platform,
            "webpage_url": data.get("webpage_url", url)
        }

    async def list_subtitles(
        self, url: str, cookies_file: Optional[str] = None
    ) -> dict:
        """列出可用字幕"""
        cmd = [
            "yt-dlp",
            "--list-subs",
            "--no-download",
            url
        ]

        cmd.extend(self._build_auth_args(cookies_file))

        env = os.environ.copy()
        env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '/usr/bin:/bin')}"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        stdout, stderr = await process.communicate()

        output = stdout.decode()

        subtitles = {"manual": [], "automatic": []}

        current_section = None
        for line in output.split("\n"):
            if "Available subtitles" in line:
                current_section = "manual"
            elif "Available automatic captions" in line:
                current_section = "automatic"
            elif current_section and line.strip():
                match = re.match(r"^(\w+(?:-\w+)?)\s+", line.strip())
                if match:
                    lang_code = match.group(1)
                    if lang_code not in ["Language", "vtt", "ttml", "srv3", "srv2", "srv1", "json3"]:
                        subtitles[current_section].append({
                            "code": lang_code,
                            "info": line.strip()
                        })

        return subtitles
