"""文档摄入管道: PDF → Markdown → 切片 → Embedding → Chroma"""
import os
import json
from pathlib import Path
from typing import List

from rag.chunker import DocumentChunker
from rag.embedder import embedder
from utils.logging import log


class IngestionPipeline:
    """文档摄入管道"""

    def __init__(self, chroma_collection, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chroma = chroma_collection
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    async def ingest_pdf(self, file_path: str) -> int:
        """摄入单个 PDF 文件"""
        text = await self._parse_pdf(file_path)
        return await self._ingest_text(text, source=os.path.basename(file_path))

    async def ingest_json_fault_codes(self, file_path: str):
        """摄入故障码 JSON（不进 Chroma，走 SQL）——留给 db seed 处理"""
        pass  # 故障码通过 models.fault_code 直接写入 SQL

    async def ingest_json_spare_parts(self, file_path: str):
        """摄入备件清单"""
        pass  # 通过 models.spare_part 写入

    async def _parse_pdf(self, file_path: str) -> str:
        """PDF → Markdown 文本"""
        try:
            import fitz  # pymupdf
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            log.info("ingestion.pdf_parsed", file=file_path, pages=len(doc))
            return text
        except ImportError:
            log.warning("ingestion.pymupdf_missing", hint="pip install pymupdf")
            # Fallback: 直接读文本文件
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

    async def _ingest_text(self, text: str, source: str = "") -> int:
        """文本 → 切片 → Embedding → Chroma"""
        chunks = self.chunker.chunk(text, source=source)
        if not chunks:
            log.warning("ingestion.no_chunks", source=source)
            return 0

        # 批量 Embedding
        contents = [c["content"] for c in chunks]
        embeddings = await embedder.embed(contents)

        # 写入 Chroma
        ids = [f"{source}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": c["source"], "char_count": c["char_count"]} for c in chunks]

        self.chroma.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas,
        )

        log.info("ingestion.complete", source=source, chunks=len(chunks))
        return len(chunks)
