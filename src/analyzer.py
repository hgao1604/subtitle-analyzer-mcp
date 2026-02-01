"""
字幕分析模块
提供关键词搜索、时间戳定位等功能
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SubtitleEntry:
    """字幕条目"""
    index: int
    start_time: str
    end_time: str
    text: str
    start_seconds: float = 0.0


class SubtitleAnalyzer:
    """字幕分析器"""

    def _detect_format(self, content: str) -> str:
        """检测字幕格式"""
        if content.strip().startswith("WEBVTT"):
            return "vtt"
        return "srt"

    def parse(self, content: str) -> list[SubtitleEntry]:
        """自动检测格式并解析字幕"""
        fmt = self._detect_format(content)
        if fmt == "vtt":
            return self.parse_vtt(content)
        return self.parse_srt(content)

    def parse_vtt(self, vtt_content: str) -> list[SubtitleEntry]:
        """解析 VTT 格式字幕"""
        entries = []
        lines = vtt_content.split("\n")

        # 跳过 WEBVTT 头部
        i = 0
        while i < len(lines) and not re.match(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->", lines[i]):
            i += 1

        index = 1
        while i < len(lines):
            line = lines[i].strip()

            # 匹配时间戳行
            time_match = re.match(
                r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})",
                line
            )
            if time_match:
                start_time = time_match.group(1)
                end_time = time_match.group(2)

                # 收集文本行（直到空行或下一个时间戳）
                i += 1
                text_lines = []
                while i < len(lines):
                    text_line = lines[i].strip()
                    if not text_line or re.match(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->", text_line):
                        break
                    # 清理 HTML/VTT 标签
                    clean_line = re.sub(r"<[^>]+>", "", text_line)
                    if clean_line:
                        text_lines.append(clean_line)
                    i += 1

                if text_lines:
                    entry = SubtitleEntry(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        text=" ".join(text_lines),
                        start_seconds=self._time_to_seconds(start_time)
                    )
                    entries.append(entry)
                    index += 1
            else:
                i += 1

        return entries

    def parse_srt(self, srt_content: str) -> list[SubtitleEntry]:
        """解析 SRT 格式字幕"""
        entries = []
        blocks = re.split(r"\n\s*\n", srt_content.strip())

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) < 2:
                continue

            # 尝试解析序号（兼容无序号情况）
            time_line_idx = 0
            try:
                index = int(lines[0])
                time_line_idx = 1
            except ValueError:
                index = len(entries) + 1

            if time_line_idx >= len(lines):
                continue

            # 解析时间戳
            time_match = re.match(
                r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
                lines[time_line_idx]
            )
            if not time_match:
                continue

            start_time = time_match.group(1).replace(",", ".")
            end_time = time_match.group(2).replace(",", ".")

            # 合并文本行
            text = " ".join(lines[time_line_idx + 1:])
            # 清理 HTML 标签
            text = re.sub(r"<[^>]+>", "", text)

            if not text.strip():
                continue

            entry = SubtitleEntry(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text,
                start_seconds=self._time_to_seconds(start_time)
            )
            entries.append(entry)

        return entries
    
    def _time_to_seconds(self, time_str: str) -> float:
        """将时间字符串转换为秒数"""
        # 格式: HH:MM:SS.mmm
        match = re.match(r"(\d{2}):(\d{2}):(\d{2})[,\.](\d{3})", time_str)
        if not match:
            return 0.0
        
        hours, minutes, seconds, ms = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(ms) / 1000
    
    def _seconds_to_time(self, seconds: float) -> str:
        """将秒数转换为时间字符串"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
    
    def search_keywords(
        self, 
        srt_content: str, 
        keywords: list[str], 
        context_lines: int = 2
    ) -> str:
        """
        在字幕中搜索关键词
        
        Args:
            srt_content: SRT 格式字幕内容
            keywords: 关键词列表
            context_lines: 上下文行数
        
        Returns:
            格式化的搜索结果
        """
        entries = self.parse(srt_content)
        
        if not entries:
            return "无法解析字幕内容"
        
        results = []
        
        for keyword in keywords:
            keyword_results = []
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            
            for i, entry in enumerate(entries):
                if pattern.search(entry.text):
                    # 获取上下文
                    start_idx = max(0, i - context_lines)
                    end_idx = min(len(entries), i + context_lines + 1)
                    
                    context = []
                    for j in range(start_idx, end_idx):
                        marker = ">>>" if j == i else "   "
                        context.append(
                            f"{marker} [{entries[j].start_time}] {entries[j].text}"
                        )
                    
                    keyword_results.append({
                        "timestamp": entry.start_time,
                        "seconds": entry.start_seconds,
                        "text": entry.text,
                        "context": "\n".join(context)
                    })
            
            results.append({
                "keyword": keyword,
                "matches": keyword_results,
                "count": len(keyword_results)
            })
        
        return self._format_search_results(results)
    
    def _format_search_results(self, results: list[dict]) -> str:
        """格式化搜索结果"""
        output = []
        output.append("=" * 60)
        output.append("🔍 字幕关键词搜索结果")
        output.append("=" * 60)
        
        total_matches = 0
        
        for result in results:
            keyword = result["keyword"]
            matches = result["matches"]
            count = result["count"]
            total_matches += count
            
            output.append(f"\n📌 关键词: \"{keyword}\" (找到 {count} 处)")
            output.append("-" * 40)
            
            if not matches:
                output.append("   未找到匹配内容")
                continue
            
            for i, match in enumerate(matches, 1):
                output.append(f"\n  [{i}] 时间戳: {match['timestamp']} ({match['seconds']:.1f}秒)")
                output.append(f"      匹配文本: {match['text']}")
                output.append(f"\n      上下文:")
                for line in match['context'].split('\n'):
                    output.append(f"      {line}")
        
        output.append("\n" + "=" * 60)
        output.append(f"总计: 搜索 {len(results)} 个关键词，找到 {total_matches} 处匹配")
        output.append("=" * 60)
        
        return "\n".join(output)
    
    def get_summary_segments(
        self, 
        srt_content: str, 
        segment_duration: int = 300
    ) -> list[dict]:
        """
        将字幕按时间段分割，便于逐段摘要
        
        Args:
            srt_content: SRT 格式字幕内容
            segment_duration: 每段时长（秒），默认5分钟
        
        Returns:
            分段列表，每段包含时间范围和文本
        """
        entries = self.parse(srt_content)
        
        if not entries:
            return []
        
        segments = []
        current_segment = {
            "start_time": entries[0].start_time,
            "start_seconds": 0,
            "texts": []
        }
        
        for entry in entries:
            segment_start = (int(entry.start_seconds) // segment_duration) * segment_duration
            
            if segment_start != current_segment["start_seconds"]:
                # 完成当前段
                if current_segment["texts"]:
                    current_segment["text"] = " ".join(current_segment["texts"])
                    current_segment["end_time"] = self._seconds_to_time(
                        current_segment["start_seconds"] + segment_duration
                    )
                    del current_segment["texts"]
                    segments.append(current_segment)
                
                # 开始新段
                current_segment = {
                    "start_time": self._seconds_to_time(segment_start),
                    "start_seconds": segment_start,
                    "texts": []
                }
            
            current_segment["texts"].append(entry.text)
        
        # 添加最后一段
        if current_segment["texts"]:
            current_segment["text"] = " ".join(current_segment["texts"])
            current_segment["end_time"] = entries[-1].end_time
            del current_segment["texts"]
            segments.append(current_segment)
        
        return segments
    
    def extract_chapters(self, srt_content: str, threshold: float = 30.0) -> list[dict]:
        """
        尝试通过字幕间隙检测章节分割点
        
        Args:
            srt_content: SRT 格式字幕内容
            threshold: 间隙阈值（秒），超过此值认为是新章节
        
        Returns:
            章节列表
        """
        entries = self.parse(srt_content)
        
        if len(entries) < 2:
            return []
        
        chapters = []
        chapter_start = entries[0]
        
        for i in range(1, len(entries)):
            prev_end = self._time_to_seconds(entries[i-1].end_time)
            curr_start = entries[i].start_seconds
            gap = curr_start - prev_end
            
            if gap > threshold:
                # 发现章节分割点
                chapters.append({
                    "start_time": chapter_start.start_time,
                    "end_time": entries[i-1].end_time,
                    "first_line": chapter_start.text[:100]
                })
                chapter_start = entries[i]
        
        # 添加最后一章
        chapters.append({
            "start_time": chapter_start.start_time,
            "end_time": entries[-1].end_time,
            "first_line": chapter_start.text[:100]
        })
        
        return chapters
