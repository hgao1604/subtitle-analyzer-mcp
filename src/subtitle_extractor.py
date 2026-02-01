"""
字幕提取模块
- YouTube: 使用 youtube-transcript-api（无需认证）
- Bilibili: 使用 yt-dlp
"""

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    RequestBlocked,
)


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

    # 语言代码映射（用户输入 -> youtube-transcript-api 格式）
    LANG_MAP = {
        "zh": ["zh-Hans", "zh-CN", "zh-TW", "zh-Hant", "zh"],
        "zh-Hans": ["zh-Hans", "zh-CN", "zh"],
        "zh-Hant": ["zh-Hant", "zh-TW"],
        "en": ["en", "en-US", "en-GB"],
        "ja": ["ja"],
    }

    def __init__(self):
        self._yt_api = YouTubeTranscriptApi()

    def detect_platform(self, url: str) -> Optional[str]:
        """检测视频平台"""
        for platform, patterns in self.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, url, re.IGNORECASE):
                    return platform
        return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """从 YouTube URL 提取视频 ID"""
        for pattern in self.PLATFORM_PATTERNS["youtube"]:
            match = re.match(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _build_auth_args(self, cookies_file: Optional[str] = None) -> list[str]:
        """构建 yt-dlp 认证参数（仅 Bilibili 使用）"""
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

    def _transcript_to_srt(self, transcript: list) -> str:
        """将 youtube-transcript-api 的结果转换为 SRT 格式"""
        srt_lines = []
        for i, entry in enumerate(transcript, 1):
            start = entry.start
            duration = entry.duration
            end = start + duration

            start_time = self._seconds_to_srt_time(start)
            end_time = self._seconds_to_srt_time(end)

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_time} --> {end_time}")
            srt_lines.append(entry.text)
            srt_lines.append("")

        return "\n".join(srt_lines)

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _transcript_to_text(self, transcript: list) -> str:
        """将 youtube-transcript-api 的结果转换为纯文本"""
        return "\n".join(entry.text for entry in transcript)

    async def _extract_youtube(self, url: str, lang: str, format: str) -> str:
        """使用 youtube-transcript-api 提取 YouTube 字幕"""
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError(f"无法从 URL 提取视频 ID: {url}")

        # 获取语言优先级列表
        lang_list = self.LANG_MAP.get(lang, [lang])

        # 在线程池中运行同步 API
        loop = asyncio.get_event_loop()
        try:
            transcript = await loop.run_in_executor(
                None,
                lambda: self._yt_api.fetch(video_id, languages=lang_list)
            )
        except NoTranscriptFound:
            # 尝试获取任意可用字幕
            transcript_list = await loop.run_in_executor(
                None,
                lambda: self._yt_api.list(video_id)
            )
            # 优先手动字幕，其次自动生成
            available = list(transcript_list)
            if not available:
                raise ValueError("该视频没有可用字幕")

            # 找到第一个可用的字幕
            transcript = await loop.run_in_executor(
                None,
                lambda: available[0].fetch()
            )

        if format == "text":
            return self._transcript_to_text(transcript)
        return self._transcript_to_srt(transcript)

    async def _extract_with_ytdlp(
        self, url: str, lang: str, format: str, cookies_file: Optional[str]
    ) -> str:
        """使用 yt-dlp 提取字幕（YouTube 备用方案）"""
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

            # YouTube 也可能需要认证
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

    async def _extract_bilibili(
        self, url: str, lang: str, format: str, cookies_file: Optional[str]
    ) -> str:
        """使用 yt-dlp 提取 Bilibili 字幕"""
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

            # 构建环境变量
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
            cookies_file: cookies 文件路径（仅 Bilibili 需要）

        Returns:
            字幕文本
        """
        platform = self.detect_platform(url)
        if not platform:
            raise ValueError(f"不支持的视频平台，URL: {url}")

        if platform == "youtube":
            try:
                return await self._extract_youtube(url, lang, format)
            except (TranscriptsDisabled, VideoUnavailable) as e:
                raise ValueError(f"无法提取字幕: {e}")
            except (RequestBlocked, Exception) as e:
                # IP 被封或其他错误，降级到 yt-dlp
                return await self._extract_with_ytdlp(url, lang, format, cookies_file)
        else:  # bilibili
            return await self._extract_bilibili(url, lang, format, cookies_file)

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

        if platform == "bilibili":
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
        platform = self.detect_platform(url)

        if platform == "youtube":
            return await self._list_youtube_subtitles(url)
        else:
            return await self._list_bilibili_subtitles(url, cookies_file)

    async def _list_youtube_subtitles(self, url: str) -> dict:
        """列出 YouTube 可用字幕"""
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError(f"无法从 URL 提取视频 ID: {url}")

        loop = asyncio.get_event_loop()
        try:
            transcript_list = await loop.run_in_executor(
                None,
                lambda: self._yt_api.list(video_id)
            )
        except (TranscriptsDisabled, VideoUnavailable) as e:
            raise ValueError(f"无法获取字幕列表: {e}")

        subtitles = {"manual": [], "automatic": []}

        for transcript in transcript_list:
            entry = {
                "code": transcript.language_code,
                "info": f"{transcript.language} ({transcript.language_code})"
            }
            if transcript.is_generated:
                subtitles["automatic"].append(entry)
            else:
                subtitles["manual"].append(entry)

        return subtitles

    async def _list_bilibili_subtitles(
        self, url: str, cookies_file: Optional[str]
    ) -> dict:
        """列出 Bilibili 可用字幕"""
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
