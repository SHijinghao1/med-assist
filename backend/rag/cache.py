"""Redis 缓存层"""
import json
from typing import Optional
from config import REDIS_URL


class RedisCache:
    """Redis 热点查询缓存"""

    def __init__(self):
        self._redis = None

    async def _lazy_init(self):
        if self._redis is not None:
            return
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(REDIS_URL, decode_responses=True)
            await self._redis.ping()
        except Exception:
            self._redis = None  # Redis 不可用时静默降级

    async def get(self, key: str) -> Optional[str]:
        await self._lazy_init()
        if self._redis is None:
            return None
        try:
            return await self._redis.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: str, ttl: int = 3600):
        await self._lazy_init()
        if self._redis is None:
            return
        try:
            await self._redis.setex(key, ttl, value)
        except Exception:
            pass

    async def get_json(self, key: str) -> Optional[dict]:
        raw = await self.get(key)
        if raw:
            return json.loads(raw)
        return None

    async def set_json(self, key: str, value: dict, ttl: int = 3600):
        await self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    async def cache_key(self, prefix: str, query: str) -> str:
        """生成缓存键"""
        return f"{prefix}:{hash(query) & 0x7FFFFFFF}"


# 全局单例
redis_cache = RedisCache()
