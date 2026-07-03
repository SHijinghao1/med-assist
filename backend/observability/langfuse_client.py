"""LangFuse 全链路可观测客户端"""
import os
import functools
from config import LANGFUSE_ENABLED, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
from utils.logging import log

_langfuse = None


def get_langfuse():
    """懒加载 LangFuse 客户端"""
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    if not LANGFUSE_ENABLED:
        _langfuse = False
        return None

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        log.info("langfuse.connected", host=LANGFUSE_HOST)
        return _langfuse
    except ImportError:
        log.warning("langfuse.not_installed")
        _langfuse = False
        return None
    except Exception as e:
        log.warning("langfuse.init_failed", error=str(e))
        _langfuse = False
        return None


def trace(name: str, **metadata):
    """装饰器：为函数调用创建 LangFuse trace span"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            lf = get_langfuse()
            if not lf:
                return await func(*args, **kwargs)

            trace = lf.trace(name=name, metadata=metadata)
            try:
                result = await func(*args, **kwargs)
                trace.update(output={"status": "ok"})
                return result
            except Exception as e:
                trace.update(output={"status": "error", "error": str(e)})
                raise
        return wrapper
    return decorator
