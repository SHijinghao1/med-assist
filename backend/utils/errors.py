"""统一错误处理 + 重试策略"""


class AppError(Exception):
    """应用级异常基类"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status: int = 500):
        self.message = message
        self.code = code
        self.status = status
        super().__init__(message)


class ToolExecutionError(AppError):
    """Tool 执行失败"""
    def __init__(self, tool_name: str, detail: str):
        super().__init__(
            message=f"Tool '{tool_name}' 执行失败: {detail}",
            code="TOOL_ERROR",
            status=500,
        )


class LLMTimeoutError(AppError):
    """LLM API 超时"""
    def __init__(self, model: str, timeout_s: float):
        super().__init__(
            message=f"LLM '{model}' 超时 ({timeout_s}s)",
            code="LLM_TIMEOUT",
            status=504,
        )


class LLMAllUnavailableError(AppError):
    """所有 LLM 都不可用"""
    def __init__(self):
        super().__init__(
            message="所有 LLM 服务暂时不可用，请稍后重试",
            code="LLM_ALL_UNAVAILABLE",
            status=503,
        )


class ValidationError(AppError):
    """入参校验失败"""
    def __init__(self, detail: str):
        super().__init__(
            message=f"参数校验失败: {detail}",
            code="VALIDATION_ERROR",
            status=400,
        )


class GuardViolationError(AppError):
    """安全护栏拦截"""
    def __init__(self, detail: str):
        super().__init__(
            message=f"请求被安全策略拦截: {detail}",
            code="GUARD_VIOLATION",
            status=422,
        )
