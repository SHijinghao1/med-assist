"""LangGraph Supervisor: 总控编排"""
from typing import Literal
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.router import route_intent
from agent.experts.diagnosis import run_diagnosis_agent
from agent.experts.repair import run_repair_agent
from agent.experts.parts import run_parts_agent
from agent.reflection import reflect_and_refine
from agent.human_loop import needs_human_approval, request_approval
from safety.input_validators import validate_input
from safety.output_validators import validate_output
from rag.semantic_cache import semantic_cache
from rag.retriever import HybridRetriever
from utils.logging import log


def build_supervisor_graph(
    db_session_factory,
    retriever: HybridRetriever,
    llm_call,
):
    """构建 LangGraph 工作流"""

    async def input_guard_node(state: AgentState) -> AgentState:
        query = state["messages"][-1].content if state["messages"] else ""
        result = await validate_input(query)
        state["input_guard_passed"] = result["passed"]
        if not result["passed"]:
            state["final_response"] = f"❌ 请求被拦截: {result.get('reason', '')}"
        return state

    async def semantic_cache_node(state: AgentState) -> AgentState:
        query = state["messages"][-1].content if state["messages"] else ""
        cached = await semantic_cache.lookup(query)
        if cached:
            state["cache_hit"] = True
            state["final_response"] = cached + "\n\n*(来自缓存)*"
            log.info("supervisor.cache_hit")
        return state

    async def router_node(state: AgentState) -> AgentState:
        query = state["messages"][-1].content if state["messages"] else ""
        intent = route_intent(query)
        state["active_expert"] = intent
        return state

    def _get_on_token(config):
        """从 graph config 中提取 token 回调"""
        if config and "configurable" in config:
            q = config["configurable"].get("token_queue")
            if q:
                async def on_token(t): await q.put(t)
                return on_token
        return None

    async def diagnosis_node(state: AgentState, config=None) -> AgentState:
        on_token = _get_on_token(config)
        async with db_session_factory() as db:
            state = await run_diagnosis_agent(state, db, retriever, llm_call, on_token)
        return state

    async def repair_node(state: AgentState, config=None) -> AgentState:
        on_token = _get_on_token(config)
        async with db_session_factory() as db:
            state = await run_repair_agent(state, db, retriever, llm_call, on_token)
        return state

    async def parts_node(state: AgentState, config=None) -> AgentState:
        on_token = _get_on_token(config)
        async with db_session_factory() as db:
            state = await run_parts_agent(state, db, llm_call, on_token)
        return state

    async def reflection_node(state: AgentState, config=None) -> AgentState:
        # reflection 不走流式，避免 JSON 残渣泄漏到前端
        state = await reflect_and_refine(state, llm_call, on_token=None)
        return state

    async def hitl_check_node(state: AgentState) -> AgentState:
        if needs_human_approval(state):
            state = await request_approval(state)
        return state

    async def output_guard_node(state: AgentState) -> AgentState:
        result = await validate_output(state.get("final_response", ""))
        state["output_guard_result"] = result
        if not result["passed"]:
            state["final_response"] = result["response"]
        return state

    async def cache_store_node(state: AgentState) -> AgentState:
        if not state.get("cache_hit") and state.get("final_response"):
            query = state["messages"][-1].content if state["messages"] else ""
            await semantic_cache.store(query, state["final_response"])
        return state

    # ── 路由函数 ──
    def route_after_guard(state: AgentState) -> str:
        if not state.get("input_guard_passed", True):
            return END
        return "cache_check"

    def route_after_cache(state: AgentState) -> str:
        if state.get("cache_hit"):
            return END
        return "router"

    def route_after_router(state: AgentState) -> str:
        expert = state.get("active_expert", "diagnosis")
        if expert not in ("diagnosis", "repair", "parts"):
            return "diagnosis"
        return expert

    def route_after_hitl(state: AgentState) -> str:
        if state.get("pending_approval"):
            return END  # HITL 中断，等待用户确认
        return "reflection"

    # ── 构建 Graph ──
    graph = StateGraph(AgentState)

    graph.add_node("input_guard", input_guard_node)
    graph.add_node("cache_check", semantic_cache_node)
    graph.add_node("router", router_node)
    graph.add_node("diagnosis", diagnosis_node)
    graph.add_node("repair", repair_node)
    graph.add_node("parts", parts_node)
    graph.add_node("hitl_check", hitl_check_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("output_guard", output_guard_node)
    graph.add_node("cache_store", cache_store_node)

    graph.set_entry_point("input_guard")

    graph.add_conditional_edges("input_guard", route_after_guard)
    graph.add_conditional_edges("cache_check", route_after_cache)
    graph.add_conditional_edges("router", route_after_router)

    graph.add_edge("diagnosis", "hitl_check")
    graph.add_edge("repair", "hitl_check")
    graph.add_edge("parts", "hitl_check")

    graph.add_conditional_edges("hitl_check", route_after_hitl)
    graph.add_edge("reflection", "output_guard")
    graph.add_edge("output_guard", "cache_store")
    graph.add_edge("cache_store", END)

    return graph.compile()
