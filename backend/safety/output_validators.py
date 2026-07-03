"""输出安全校验: PII 脱敏 + 高危操作检测"""
import re
from utils.logging import log

DANGEROUS_ACTIONS = [
    "电机强制复位", "电流过载测试", "传感器校准",
    "固件升级", "制动器释放", "参数初始化",
]

# 简单的 PII 模式
PII_PATTERNS = [
    (re.compile(r"1[3-9]\d{9}"), "[手机号已隐藏]"),
    (re.compile(r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]"), "[身份证号已隐藏]"),
]


async def validate_output(response: str) -> dict:
    """输出校验: PII 脱敏 + 高危操作标记"""
    issues = []
    cleaned = response

    # 1. PII 脱敏
    for pattern, replacement in PII_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub(replacement, cleaned)
            issues.append("PII detected and redacted")

    # 2. 高危操作检测
    for action in DANGEROUS_ACTIONS:
        if action in response:
            issues.append({
                "type": "dangerous_action",
                "action": action,
                "require_hitl": True,
            })

    passed = len([i for i in issues if isinstance(i, dict)]) == 0

    if issues:
        log.info("safety.output_issues", issues=issues)

    return {"passed": passed, "issues": issues, "response": cleaned}
