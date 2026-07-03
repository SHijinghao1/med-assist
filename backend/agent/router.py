"""Supervisor 意图路由"""
from utils.logging import log

ROUTING_RULES = {
    "diagnosis": {
        "keywords": ["报错", "故障", "不工作", "异常", "错误码", "报警", "不动了",
                     "E10", "E20", "E30", "怎么排查", "什么原因", "怎么了"],
        "description": "设备故障诊断与排查",
    },
    "repair": {
        "keywords": ["怎么修", "更换", "拆", "维修步骤", "校准", "调试", "修理", "换"],
        "description": "维修操作指导",
    },
    "parts": {
        "keywords": ["备件", "配件", "库存", "型号", "订货", "替换件", "有没有货", "价格"],
        "description": "备件查询与订购",
    },
}


def route_intent(user_query: str) -> str:
    """简单的关键词路由——复杂路由由 Supervisor LLM 处理"""
    query_lower = user_query.lower()

    scores = {}
    for expert, rules in ROUTING_RULES.items():
        score = 0
        for kw in rules["keywords"]:
            if kw.lower() in query_lower:
                score += 1
        if score > 0:
            scores[expert] = score

    if not scores:
        log.info("router.default", query=user_query[:50])
        return "diagnosis"  # 默认诊断

    best = max(scores, key=scores.get)
    log.info("router.route", query=user_query[:50], intent=best, scores=scores)
    return best
