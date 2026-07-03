"""Embedding 模型封装 (BGE-M3) — 离线优先，网络不可用时自动降级"""
import asyncio
from typing import List


class Embedder:
    """Embedding 模型封装。不可用时语义搜索和语义缓存自动降级。"""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "bge-m3"
        self._model = None
        self._init_done = False

    async def _check_online(self) -> bool:
        """快速检查 HuggingFace 是否可达"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as c:
                r = await c.head("https://huggingface.co", follow_redirects=True)
                return r.status_code < 500
        except Exception:
            return False

    async def _lazy_init(self):
        if self._init_done:
            return

        self._init_done = True

        # 1. 检查网络
        online = await self._check_online()

        try:
            from sentence_transformers import SentenceTransformer
            model_id = "BAAI/bge-m3" if self.model_name == "bge-m3" else self.model_name

            if online:
                self._model = SentenceTransformer(model_id)
            else:
                # 离线：尝试本地缓存，不触发任何网络请求
                import os
                old_val = os.environ.get("HF_HUB_OFFLINE")
                os.environ["HF_HUB_OFFLINE"] = "1"
                try:
                    self._model = SentenceTransformer(model_id, local_files_only=True)
                finally:
                    if old_val is not None:
                        os.environ["HF_HUB_OFFLINE"] = old_val
                    else:
                        del os.environ["HF_HUB_OFFLINE"]
        except Exception:
            self._model = False

    async def embed(self, texts: List[str]) -> List[List[float]]:
        await self._lazy_init()
        if self._model is False or self._model is None:
            raise RuntimeError("Embedding unavailable")

        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        )
        return embeddings.tolist()

    async def embed_query(self, query: str) -> List[float]:
        results = await self.embed([query])
        return results[0]

    @property
    def dimension(self) -> int:
        return 1024 if self.model_name == "bge-m3" else 768


embedder = Embedder()
