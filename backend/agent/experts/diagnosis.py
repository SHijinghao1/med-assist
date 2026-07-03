"""故障诊断专家 Agent"""
from agent.state import AgentState
from tools import execute_tool
from rag.retriever import HybridRetriever
from utils.logging import log

DIAGNOSIS_SYSTEM_PROMPT = """你是医疗设备故障诊断专家。用户描述设备异常后，你必须:

1. 若提到故障码 → 先调 search_fault_code (SQL 精确匹配)
2. 调用 query_device_status 获取设备实时状态
3. 调用 search_maintenance_logs 查找相似历史故障
4. 如需操作手册细节 → 使用 RAG 检索
5. 综合分析后输出: 最可能原因(排序) + 排查步骤 + 需准备的备件工单

不要猜测，每一步都要有数据支撑。查不到就说查不到。"""


async def run_diagnosis_agent(
    state: AgentState,
    db,
    retriever: HybridRetriever,
    llm_call,
    on_token=None,
) -> AgentState:
    """执行故障诊断流程"""
    user_query = state["messages"][-1].content if state["messages"] else ""

    log.info("agent.diagnosis.start", query=user_query[:80])

    findings: dict = {}

    # Step 1: 检查是否有故障码 → SQL 精确匹配
    import re
    fault_codes = re.findall(r'[Ee]\d{3,4}', user_query)
    for code in fault_codes[:2]:
        result = await execute_tool(db, "search_fault_code", {"code": code.upper()})
        if result.get("success") and result["data"].get("found"):
            findings["search_fault_code"] = result["data"]
            state["fault_code_hit"] = result["data"]["data"]

    # Step 2: 查询设备状态
    device_id = _extract_device_id(user_query) or "SB-00123"
    device_type = "surgical_bed" if device_id.startswith("SB") else "c_arm"
    status = await execute_tool(db, "query_device_status", {
        "device_type": device_type, "device_id": device_id
    })
    if status.get("success"):
        findings["query_device_status"] = status["data"]

    # Step 3: 搜索维修记录
    logs = await execute_tool(db, "search_maintenance_logs", {
        "query": user_query, "date_range_days": 180
    })
    if logs.get("success"):
        findings["search_maintenance_logs"] = logs["data"]

    # Step 4: RAG 检索操作手册
    semantic_docs = await retriever.search_semantic(user_query, top_k=5)
    state["semantic_docs"] = [d.get("content", "") for d in semantic_docs]

    # Step 5: LLM 综合分析
    context = _format_findings(findings, state["semantic_docs"])
    prompt = f"{DIAGNOSIS_SYSTEM_PROMPT}\n\n用户问题: {user_query}\n\n收集到的数据:\n{context}\n\n请给出诊断结果:"

    response = await llm_call(prompt, on_token)

    state["tool_results"] = findings
    state["final_response"] = response
    state["active_expert"] = "diagnosis"

    log.info("agent.diagnosis.complete", response_len=len(response))
    return state


def _extract_device_id(text: str) -> str | None:
    import re
    match = re.search(r'(SB|CA)-\d{3,5}', text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def _format_findings(findings: dict, docs: list) -> str:
    lines = []
    if "search_fault_code" in findings:
        fc_data = findings["search_fault_code"]
        fc = fc_data.get("data", fc_data)
        lines.append(f"【故障码】{fc['code']} - {fc['description']} (严重度: {fc['severity']})")
        lines.append(f"  根因: {fc['root_cause']}")
        lines.append(f"  建议动作: {fc['action_steps']}")
    if "query_device_status" in findings:
        lines.append(f"【设备状态】{findings['query_device_status']}")
    if "search_maintenance_logs" in findings:
        ml = findings["search_maintenance_logs"]
        lines.append(f"【历史维修记录】共 {ml['count']} 条")
    if docs:
        lines.append(f"【操作手册】检索到 {len(docs)} 个相关章节")
    return "\n".join(lines)
