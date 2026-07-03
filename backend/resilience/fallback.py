"""LLM 降级链路: 主LLM → 备用LLM → 语义缓存 → 硬兜底"""
from resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from utils.logging import log


class FallbackChain:
    """四级降级链"""

    def __init__(self):
        self.levels = []
        self.current_level = -1

    def add_level(self, name: str, callable, breaker: CircuitBreaker | None = None):
        self.levels.append({"name": name, "call": callable, "breaker": breaker})
        return self

    async def execute(self, *args, **kwargs):
        for i, level in enumerate(self.levels):
            self.current_level = i
            try:
                if level["breaker"]:
                    result = await level["breaker"].call(
                        lambda: level["call"](*args, **kwargs)
                    )
                else:
                    result = await level["call"](*args, **kwargs)
                if i > 0:
                    log.info("fallback.level_used", level=i, name=level["name"])
                return result
            except CircuitOpenError:
                log.warning("fallback.circuit_open", level=i, name=level["name"])
                continue
            except Exception as e:
                log.error("fallback.error", level=i, name=level["name"], error=str(e))
                continue

        log.error("fallback.all_exhausted")
        return {
            "content": "系统暂时不可用，请稍后重试或联系人工运维。",
            "fallback": "hard",
        }
