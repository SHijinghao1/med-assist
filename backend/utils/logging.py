"""structlog 结构化日志配置 + trace_id 自动注入"""
import structlog
from structlog.types import Processor


def add_trace_id(logger, method_name, event_dict):
    """从 contextvars 自动取 trace_id——不需要每次手动传"""
    from structlog.contextvars import get_contextvars
    ctx = get_contextvars()
    if "trace_id" in ctx:
        event_dict["trace_id"] = ctx["trace_id"]
    return event_dict


def drop_debug_on_prod(logger, method_name, event_dict):
    """生产环境静默丢弃 debug 级别"""
    import os
    if os.getenv("ENV") == "production" and method_name == "debug":
        raise structlog.DropEvent
    return event_dict


def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_trace_id,
            drop_debug_on_prod,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer()
            if __import__("os").getenv("LOG_FORMAT") == "console"
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger()
