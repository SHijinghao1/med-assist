"""Human-in-the-Loop 中断/恢复"""
from agent.state import AgentState
from utils.logging import log

DANGEROUS_ACTIONS = [
    "motor_reset", "current_test", "sensor_calibration", "self_test",
    "电机强制复位", "电流过载测试", "传感器校准", "设备自检",
]


def needs_human_approval(state: AgentState) -> bool:
    """只有当 run_diagnostics 真正被执行时才触发 HITL"""
    tool_results = state.get("tool_results", {})
    return "run_diagnostics" in tool_results


async def request_approval(state: AgentState) -> AgentState:
    """触发 HITL 中断"""
    state["pending_approval"] = "diagnostics"
    log.info("hitl.interrupt", pending=state["pending_approval"])
    return state


async def handle_approval(state: AgentState, approved: bool) -> AgentState:
    """处理用户确认结果"""
    state["approval_granted"] = approved
    state["pending_approval"] = None

    if approved:
        log.info("hitl.approved")
        state["messages"].append(
            type("AIMessage", (), {"content": "✅ 用户已确认高危操作，继续执行..."})()
        )
    else:
        log.info("hitl.denied")
        state["final_response"] = "⚠️ 用户取消了高危操作，已终止执行。建议线下人工处理。"
        state["approval_granted"] = False

    return state
