"""启动时自动将 data/manuals/ 目录下的文档摄入 Chroma"""
import os
from pathlib import Path
from rag.chunker import DocumentChunker
from rag.embedder import embedder
from utils.logging import log


async def ingest_all_manuals(chroma_collection, data_dir: str = None) -> int:
    """摄入所有操作手册到 Chroma 向量库"""
    if chroma_collection is None:
        log.warning("ingestion.chroma_unavailable")
        return 0

    if data_dir is None:
        from config import BASE_DIR
        data_dir = str(BASE_DIR / "data" / "manuals")

    manuals_path = Path(data_dir)
    if not manuals_path.exists():
        log.warning("ingestion.no_manuals_dir", path=str(manuals_path))
        return 0

    chunker = DocumentChunker(chunk_size=512, chunk_overlap=64)
    total = 0

    for md_file in manuals_path.glob("*.md"):
        # 跳过已摄入的文件
        existing = chroma_collection.get(where={"source": md_file.name})
        if existing and existing.get("ids") and len(existing["ids"]) > 0:
            log.info("ingestion.skip_existing", file=md_file.name, chunks=len(existing["ids"]))
            total += len(existing["ids"])
            continue

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                text = f.read()

            chunks = chunker.chunk(text, source=md_file.name)
            if not chunks:
                continue

            contents = [c["content"] for c in chunks]

            # 尝试 embedding，不可用时跳过
            try:
                embeddings = await embedder.embed(contents)
            except Exception:
                log.warning("ingestion.embed_unavailable", file=md_file.name)
                # 存文本但不存向量（Chroma 降级：无 embedding 也能存）
                chroma_collection.add(
                    ids=[f"{md_file.stem}_{i}" for i in range(len(chunks))],
                    documents=contents,
                    metadatas=[{"source": md_file.name, "char_count": c["char_count"]} for c in chunks],
                )
                total += len(chunks)
                continue

            chroma_collection.add(
                ids=[f"{md_file.stem}_{i}" for i in range(len(chunks))],
                embeddings=embeddings,
                documents=contents,
                metadatas=[{"source": md_file.name, "char_count": c["char_count"]} for c in chunks],
            )

            total += len(chunks)
            log.info("ingestion.ingested", file=md_file.name, chunks=len(chunks))

        except Exception as e:
            log.error("ingestion.error", file=md_file.name, error=str(e))

    return total
