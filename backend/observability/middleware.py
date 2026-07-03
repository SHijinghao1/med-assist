"""FastAPI 中间件: trace_id 注入 + structlog 上下文绑定"""
import uuid
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = structlog.get_logger()


class TraceMiddleware(BaseHTTPMiddleware):
    """每个 HTTP 请求生成 trace_id, 注入 structlog context"""

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        start = time.monotonic()

        # 注入 structlog contextvars —— 跨 async/await 边界不丢失
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        request.state.trace_id = trace_id

        response = await call_next(request)

        elapsed_ms = (time.monotonic() - start) * 1000
        response.headers["X-Trace-ID"] = trace_id

        log.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
        )

        # 清理 context
        structlog.contextvars.unbind_contextvars("trace_id")

        return response
