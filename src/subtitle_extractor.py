"""
字幕提取模块
使用 yt-dlp 从 YouTube 和 Bilibili 提取字幕
"""

import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Optional


class SubtitleExtractor:
    """字幕提取器"""
    
    # 支持的平台正则
    PLATFORM_PATTERNS = {
        "youtube": [
            r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
            r"(?:https?://)?(?:www\.)?youtu\.be/[\w-]+",
            r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+"
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
    
    async def extract(
        self, 
        url: str, 
        lang: str = "zh", 
        format: str = "srt"
    ) -> str:
        """
        提取字幕
        
        Args:
            url: 视频 URL
            lang: 首选语言代码
            format: 输出格式 ('text' 或 'srt')
        
        Returns:
            字幕文本
        """
        platform = self.detect_platform(url)
        if not platform:
            raise ValueError(f"不支持的视频平台，URL: {url}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = str(Path(tmpdir) / "subtitle")
            
            # 构建 yt-dlp 命令
            cmd = [
                "yt-dlp",
                "--skip-download",  # 不下载视频
                "--write-subs",     # 下载字幕
                "--write-auto-subs",  # 也下载自动生成的字幕
                "--sub-langs", f"{lang},zh,zh-Hans,zh-CN,en,ja",  # 字幕语言优先级
                "--sub-format", "srt/vtt/best",
                "--convert-subs", "srt",
                "-o", output_template,
                url
            ]
            
            # Bilibili 特殊处理
            if platform == "bilibili":
                cmd.extend([
                    "--cookies-from-browser", "chrome",  # 可选：使用浏览器 cookies
                ])
            
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # 查找生成的字幕文件
            tmppath = Path(tmpdir)
            srt_files = list(tmppath.glob("*.srt"))
            
            if not srt_files:
                # 尝试查找其他格式
                vtt_files = list(tmppath.glob("*.vtt"))
                if vtt_files:
                    srt_files = vtt_files
                else:
                    error_msg = stderr.decode() if stderr else "未知错误"
                    raise ValueError(f"无法提取字幕。可能原因：\n1. 视频没有字幕\n2. 网络问题\n3. 需要登录\n\n详细信息: {error_msg}")
            
            # 读取字幕内容
            subtitle_content = srt_files[0].read_text(encoding="utf-8")
            
            if format == "text":
                return self._srt_to_text(subtitle_content)
            return subtitle_content
    
    def _srt_to_text(self, srt_content: str) -> str:
        """将 SRT 格式转换为纯文本"""
        lines = []
        current_text = []
        
        for line in srt_content.split("\n"):
            line = line.strip()
            # 跳过序号和时间戳
            if re.match(r"^\d+$", line):
                if current_text:
                    lines.append(" ".join(current_text))
                    current_text = []
            elif re.match(r"^\d{2}:\d{2}:\d{2}", line):
                continue
            elif line:
                # 移除 HTML 标签
                clean_line = re.sub(r"<[^>]+>", "", line)
                current_text.append(clean_line)
        
        if current_text:
            lines.append(" ".join(current_text))
        
        return "\n".join(lines)
    
    async def get_video_info(self, url: str) -> dict:
        """获取视频信息"""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"获取视频信息失败: {stderr.decode()}")
        
        data = json.loads(stdout.decode())
        
        # 提取关键信息
        return {
            "title": data.get("title", "未知"),
            "duration": data.get("duration", 0),
            "duration_string": data.get("duration_string", "00:00"),
            "uploader": data.get("uploader", "未知"),
            "upload_date": data.get("upload_date", "未知"),
            "view_count": data.get("view_count", 0),
            "description": data.get("description", "")[:500],  # 截取前500字
            "platform": self.detect_platform(url),
            "webpage_url": data.get("webpage_url", url)
        }
    
    async def list_subtitles(self, url: str) -> dict:
        """列出可用字幕"""
        cmd = [
            "yt-dlp",
            "--list-subs",
            "--no-download",
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode()
        
        # 解析输出
        subtitles = {
            "manual": [],      # 手动上传的字幕
            "automatic": []    # 自动生成的字幕
        }
        
        current_section = None
        for line in output.split("\n"):
            if "Available subtitles" in line:
                current_section = "manual"
            elif "Available automatic captions" in line:
                current_section = "automatic"
            elif current_section and line.strip():
                # 提取语言代码
                match = re.match(r"^(\w+(?:-\w+)?)\s+", line.strip())
                if match:
                    lang_code = match.group(1)
                    if lang_code not in ["Language", "vtt", "ttml", "srv3", "srv2", "srv1", "json3"]:
                        subtitles[current_section].append({
                            "code": lang_code,
                            "info": line.strip()
                        })
        
        return subtitles
