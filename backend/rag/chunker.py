"""智能切片策略: 结构切片 + 语义切片 + 滑动窗口"""
import re
from typing import List


class DocumentChunker:
    """将 Markdown 文档切分为语义完整的 chunks"""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk(self, text: str, source: str = "") -> List[dict]:
        """
        三步切片:
          1. 按 Markdown 标题 (# / ## / ###) 切分 → 保留结构边界
          2. 对每个 section 做滑动窗口切片
          3. 太短的 chunk 跟下一个合并
        """
        sections = self._split_by_headers(text)
        chunks = []
        for section in sections:
            section_chunks = self._sliding_window(section)
            chunks.extend(section_chunks)

        chunks = self._merge_short(chunks)

        return [
            {"content": c, "source": source, "char_count": len(c)}
            for c in chunks
        ]

    def _split_by_headers(self, text: str) -> List[str]:
        """按 H1/H2/H3 标题切分"""
        # 在标题前分割，保留标题作为 section 开头
        parts = re.split(r"\n(?=#{1,3}\s)", text)
        return [p.strip() for p in parts if p.strip()]

    def _sliding_window(self, text: str) -> List[str]:
        """滑动窗口切片，确保上下文不丢失"""
        if len(text) <= self.chunk_size:
            return [text] if len(text) >= self.min_chunk_size else []

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            # 尝试在句号或换行处断开，避免切断句子
            if end < len(text):
                break_point = max(
                    text.rfind("。", start, end),
                    text.rfind("\n", start, end),
                    text.rfind(". ", start, end),
                )
                if break_point > start + self.min_chunk_size:
                    end = break_point + 1

            chunk = text[start:end].strip()
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)
            start = end - self.chunk_overlap

        return chunks

    def _merge_short(self, chunks: List[str]) -> List[str]:
        """太短的 chunk 向后合并"""
        merged = []
        buffer = ""
        for chunk in chunks:
            if len(buffer) + len(chunk) < self.chunk_size:
                buffer = (buffer + "\n" + chunk).strip() if buffer else chunk
            else:
                if buffer:
                    merged.append(buffer)
                buffer = chunk
        if buffer:
            merged.append(buffer)
        return merged
