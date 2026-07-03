"""GPTCache 语义缓存: Embedding 相似度做缓存键"""
from typing import Optional
from config import SEMANTIC_CACHE_THRESHOLD, SEMANTIC_CACHE_TTL
from rag.embedder import embedder
from rag.cache import redis_cache
from utils.logging import log


class SemanticCache:
    """语义缓存——相似问题命中缓存"""

    def __init__(
        self,
        threshold: float = SEMANTIC_CACHE_THRESHOLD,
        ttl: int = SEMANTIC_CACHE_TTL,
    ):
        self.threshold = threshold
        self.ttl = ttl
        self._enabled = True

    async def lookup(self, query: str, device_type: str = "") -> Optional[str]:
        """查询语义缓存（Embedding 不可用时返回 None）"""
        if not self._enabled:
            return None

        try:
            query_embedding = await embedder.embed_query(query)
        except Exception:
            self._enabled = False  # 永久禁用，避免反复失败
            return None

        # 从 Redis 获取缓存的 Embedding 列表
        cache_keys = await redis_cache.get_json("semantic:keys")
        if not cache_keys:
            return None

        best_score = 0.0
        best_answer = None

        for entry in cache_keys:
            if device_type and entry.get("device_type") != device_type:
                continue

            cached_embedding = entry.get("embedding")
            if not cached_embedding:
                continue

            # 余弦相似度
            score = self._cosine_similarity(query_embedding, cached_embedding)
            if score >= self.threshold and score > best_score:
                best_score = score
                answer = await redis_cache.get(f"semantic:answer:{entry['key']}")
                if answer:
                    best_answer = answer

        if best_answer:
            log.info("semantic_cache.hit", query=query[:60], score=round(best_score, 3))
        return best_answer

    async def store(self, query: str, answer: str, device_type: str = ""):
        """存储到语义缓存（Embedding 不可用时静默跳过）"""
        if not self._enabled:
            return

        try:
            query_embedding = await embedder.embed_query(query)
        except Exception:
            self._enabled = False
            return

        cache_key = str(hash(query) & 0x7FFFFFFF)
        await redis_cache.set(f"semantic:answer:{cache_key}", answer, self.ttl)

        # 更新 keys 索引
        keys = await redis_cache.get_json("semantic:keys") or []
        keys.append({
            "key": cache_key,
            "embedding": query_embedding,
            "device_type": device_type,
        })
        # 只保留最近 500 条
        if len(keys) > 500:
            keys = keys[-500:]
        await redis_cache.set_json("semantic:keys", keys, self.ttl)

        log.info("semantic_cache.store", query=query[:60])

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


semantic_cache = SemanticCache()
