"""Tool 注册表: 统一调用接口"""
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from tools.fault_code import search_fault_code
from tools.device_status import query_device_status
from tools.maintenance import search_maintenance_logs
from tools.spare_parts import query_spare_parts
from tools.diagnostics import run_diagnostics
from tools.work_order import create_work_order
from tools.surgical_device import (
    get_device_state, list_joints, move_bed_joint, move_carm_joint,
    apply_bed_preset, set_carm_mode, emergency_stop, reset_emergency,
)

# Tool 注册表 — 知识检索 + 硬件控制
TOOL_REGISTRY: dict[str, dict] = {
    # 知识检索工具
    "search_fault_code": {"func": search_fault_code, "description": "根据故障码精确查询（SQL）", "dangerous": False},
    "query_device_status": {"func": query_device_status, "description": "查询设备实时运行状态和传感器数据", "dangerous": False},
    "search_maintenance_logs": {"func": search_maintenance_logs, "description": "搜索历史维修记录", "dangerous": False},
    "query_spare_parts": {"func": query_spare_parts, "description": "查询备件库存", "dangerous": False},
    "run_diagnostics": {"func": run_diagnostics, "description": "⚠️ 高危：执行设备诊断命令", "dangerous": True},
    "create_work_order": {"func": create_work_order, "description": "创建维修工单", "dangerous": False},
    # 硬件控制工具（IOBS）
    "get_device_state": {"func": get_device_state, "description": "获取手术室设备完整状态", "dangerous": False},
    "list_joints": {"func": list_joints, "description": "列出所有可控关节和体位预设", "dangerous": False},
    "move_bed_joint": {"func": move_bed_joint, "description": "移动手术床指定关节", "dangerous": False},
    "move_carm_joint": {"func": move_carm_joint, "description": "移动C臂指定关节", "dangerous": False},
    "apply_bed_preset": {"func": apply_bed_preset, "description": "应用手术体位预设", "dangerous": False},
    "set_carm_mode": {"func": set_carm_mode, "description": "设置C臂工作模式", "dangerous": False},
    "emergency_stop": {"func": emergency_stop, "description": "🚨 紧急停止所有设备", "dangerous": True},
    "reset_emergency": {"func": reset_emergency, "description": "解除紧急停止状态", "dangerous": False},
}


async def execute_tool(db: AsyncSession | None, tool_name: str, args: dict) -> dict:
    """统一工具调用入口——知识工具需db，硬件工具不需要"""
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"未知工具: {tool_name}"}

    tool = TOOL_REGISTRY[tool_name]
    try:
        # 硬件控制工具不需要 db
        if tool_name in ("get_device_state", "list_joints", "move_bed_joint", "move_carm_joint",
                         "apply_bed_preset", "set_carm_mode", "emergency_stop", "reset_emergency"):
            result = await tool["func"](args)
        else:
            if db is None:
                return {"error": "此工具需要数据库连接"}
            result = await tool["func"](db, args)
        return {"success": True, "tool": tool_name, "dangerous": tool["dangerous"], "data": result}
    except Exception as e:
        return {"success": False, "tool": tool_name, "error": str(e)}
