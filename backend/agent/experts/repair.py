"""维修指导专家 Agent"""
from agent.state import AgentState
from tools import execute_tool
from rag.retriever import HybridRetriever
from utils.logging import log

REPAIR_SYSTEM_PROMPT = """你是医疗设备维修指导专家。根据诊断结果，你必须:
1. 从操作手册检索相关部件的拆卸/更换步骤（逐条引用手册章节）
2. 列出所需工具和备件（调用 query_spare_parts 确认库存）
3. 标记高危步骤（需断电/需两人操作/需校准）
4. 输出图文步骤指南"""


async def run_repair_agent(
    state: AgentState,
    db,
    retriever: HybridRetriever,
    llm_call,
    on_token=None,
) -> AgentState:
    """维修指导流程"""
    diagnosis = state.get("final_response", "")
    fault_code_hit = state.get("fault_code_hit")

    log.info("agent.repair.start")

    # 查询所需备件
    parts_needed = []
    if fault_code_hit and fault_code_hit.get("related_parts"):
        for part_no in fault_code_hit["related_parts"].split(","):
            part_no = part_no.strip()
            result = await execute_tool(db, "query_spare_parts", {"part_no": part_no})
            if result.get("success"):
                parts = result["data"].get("parts", [])
                parts_needed.extend(parts)

    # 检索拆卸步骤
    repair_query = f"拆卸 更换 {fault_code_hit.get('component', '') if fault_code_hit else ''} 步骤"
    semantic_docs = await retriever.search_semantic(repair_query, top_k=5)
    state["semantic_docs"] = state.get("semantic_docs", []) + [d.get("content", "") for d in semantic_docs]

    # LLM 生成维修指导
    context = f"诊断结果: {diagnosis}\n备件库存: {parts_needed}\n操作手册: {state['semantic_docs']}"
    prompt = f"{REPAIR_SYSTEM_PROMPT}\n\n{context}\n\n请给出维修指导:"

    response = await llm_call(prompt, on_token)

    state["final_response"] = response
    state["active_expert"] = "repair"

    log.info("agent.repair.complete")
    return state
