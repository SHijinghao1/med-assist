"""备件查询专家 Agent"""
from agent.state import AgentState
from tools import execute_tool
from utils.logging import log

PARTS_SYSTEM_PROMPT = """你是备件管理助手。根据维修需求:
1. 调用 query_spare_parts 查询库存
2. 缺货时建议替代型号
3. 调用 create_work_order 创建备件申领工单"""


async def run_parts_agent(
    state: AgentState,
    db,
    llm_call,
    on_token=None,
) -> AgentState:
    """备件查询流程"""
    user_query = state["messages"][-1].content if state["messages"] else ""
    fault_code_hit = state.get("fault_code_hit")

    log.info("agent.parts.start")

    # 查询备件
    parts_result = None
    if fault_code_hit and fault_code_hit.get("related_parts"):
        part_no = fault_code_hit["related_parts"].split(",")[0].strip()
        result = await execute_tool(db, "query_spare_parts", {"part_no": part_no})
        if result.get("success"):
            parts_result = result["data"]
    else:
        result = await execute_tool(db, "query_spare_parts", {"part_name": user_query})
        if result.get("success"):
            parts_result = result["data"]

    # LLM 分析
    context = f"备件查询结果: {parts_result}"
    prompt = f"{PARTS_SYSTEM_PROMPT}\n\n查询: {user_query}\n{context}\n\n请分析备件情况:"

    response = await llm_call(prompt)

    state["tool_results"]["spare_parts"] = parts_result
    state["final_response"] = response
    state["active_expert"] = "parts"

    log.info("agent.parts.complete")
    return state
