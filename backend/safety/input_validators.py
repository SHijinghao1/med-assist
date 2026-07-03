"""输入安全校验"""
from utils.logging import log

VALID_TOPICS = {
    "故障排查": ["报错", "故障", "不工作", "异常", "报警", "不动了", "错误码"],
    "维修指导": ["怎么修", "更换", "拆", "维修", "校准", "调试"],
    "备件查询": ["备件", "配件", "库存", "型号", "订货"],
    "操作说明": ["怎么用", "操作", "功能", "设置"],
}
IRRELEVANT = ["天气", "新闻", "股票", "游戏", "点外卖", "写代码", "翻译"]
BLOCKED = ["攻击", "入侵", "破解", "绕过", "exploit", "hack"]


async def validate_input(text: str) -> dict:
    """输入校验: 话题范围 + 恶意内容"""
    # 1. 硬拦截关键词 (<1ms)
    for keyword in BLOCKED:
        if keyword in text:
            log.warning("safety.input_blocked", reason=f"blocked_keyword:{keyword}")
            return {"passed": False, "reason": f"输入包含禁止内容"}

    # 2. 快速话题判断
    for topic, keywords in VALID_TOPICS.items():
        for kw in keywords:
            if kw in text:
                return {"passed": True, "topic": topic}

    # 3. 明显不相关
    for keyword in IRRELEVANT:
        if keyword in text:
            return {"passed": True, "warning": "话题可能不相关"}

    return {"passed": True}
