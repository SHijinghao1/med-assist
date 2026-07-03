"""LangGraph Agent State 定义"""
from typing import TypedDict, List, Optional, Annotated, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    active_expert: Optional[str]

    # 检索结果
    fault_code_hit: Optional[dict]
    bm25_docs: List[dict]
    semantic_docs: List[dict]

    # 工具结果
    tool_results: dict

    # Guardrails
    input_guard_passed: bool
    output_guard_result: Optional[dict]

    # HITL
    pending_approval: Optional[str]
    approval_granted: bool

    # Self-Reflection
    reflection_scores: Optional[dict]
    reflection_verdict: Optional[str]

    # 缓存/降级
    cache_hit: bool
    fallback_level: int

    # 输出
    final_response: Optional[str]
