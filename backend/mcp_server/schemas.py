"""MCP Tool Schema 定义 — 复用 iobs-mcp-server 设计方法论"""
from tools.base import (
    DeviceType, BedJoint, CArmJoint,
    DiagnosticsCommand, WorkOrderPriority,
)

TOOLS = [
    {
        "name": "query_device_status",
        "description": "查询指定设备的实时运行状态，包括各关节位置、电机电流、温度、故障码等。用于故障诊断前的数据收集。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_type": {
                    "type": "string",
                    "enum": [e.value for e in DeviceType],
                    "description": "设备类型",
                },
                "device_id": {
                    "type": "string",
                    "description": "设备序列号，格式: SB-XXXXX (手术床) 或 CA-XXXXX (C臂)",
                },
            },
            "required": ["device_type", "device_id"],
        },
    },
    {
        "name": "search_fault_code",
        "description": "根据故障码精确查询（SQL），返回故障描述、严重程度、建议处理动作。比 RAG 更快更准。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "故障码，如 E1023"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "search_maintenance_logs",
        "description": "搜索历史维修记录，输入关键词返回相似故障的处理记录和维修方案。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词或故障描述"},
                "device_type": {"type": "string", "enum": [e.value for e in DeviceType]},
                "date_range_days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 90},
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_spare_parts",
        "description": "查询备件库存。输入部件名称或料号，返回当前库存量、预计补货时间、替代型号。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_name": {"type": "string", "description": "部件名称（模糊匹配），如 '背板电机'"},
                "part_no": {"type": "string", "description": "精确料号，如 'MTR-BK-001'"},
            },
        },
    },
    {
        "name": "run_diagnostics",
        "description": "⚠️ 高危操作：对设备执行诊断命令。执行前必须经人工确认。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string"},
                "command": {"type": "string", "enum": [e.value for e in DiagnosticsCommand]},
                "joint_name": {"type": "string", "description": "目标关节"},
            },
            "required": ["device_id", "command"],
        },
        "dangerous": True,
    },
    {
        "name": "create_work_order",
        "description": "创建维修工单。需要提供设备ID、故障描述、优先级。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string"},
                "fault_description": {"type": "string"},
                "priority": {"type": "string", "enum": [e.value for e in WorkOrderPriority]},
                "assigned_to": {"type": "string", "description": "指派的维修工程师"},
            },
            "required": ["device_id", "fault_description", "priority"],
        },
    },
    # ── IOBS 硬件控制工具（合并自 iobs-mcp-server）──
    {
        "name": "get_device_state",
        "description": "获取手术室所有设备当前状态：手术床10个关节 + C臂4个关节 + 运行模式 + 急停状态",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_joints",
        "description": "列出所有可控制的关节名称、中文标签、单位和物理限制范围，以及可用的手术体位预设",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "move_bed_joint",
        "description": "移动手术床的指定关节到目标值或按增量调整。关节如: bed_height_joint(高度500-1000mm), bed_tilt_joint(倾斜-22~22°), bed_panel_back_joint(背板-70~70°)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "joint": {"type": "string", "description": "关节名称"},
                "target_value": {"type": "number", "description": "目标绝对值"},
                "delta": {"type": "number", "description": "相对变化量"},
            },
            "required": ["joint"],
        },
    },
    {
        "name": "move_carm_joint",
        "description": "移动C臂的指定关节。关节如: arm_height_joint(高度300-400mm), arm_tilt_joint(旋转-185~185°), c_ring_rotation_joint(前后旋转-30~30°)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "joint": {"type": "string", "description": "关节名称"},
                "target_value": {"type": "number", "description": "目标绝对值"},
                "delta": {"type": "number", "description": "相对变化量"},
            },
            "required": ["joint"],
        },
    },
    {
        "name": "apply_bed_preset",
        "description": "应用预定义的手术体位。如: flat(平卧位), trendelenburg(头低脚高位), beach_chair(沙滩椅位), lithotomy(截石位), lateral_left(左侧卧), lateral_right(右侧卧)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "preset_id": {"type": "string", "enum": ["flat","trendelenburg","reverse_trendelenburg","beach_chair","lithotomy","lateral_left","lateral_right"], "description": "体位预设ID"},
            },
            "required": ["preset_id"],
        },
    },
    {
        "name": "set_carm_mode",
        "description": "设置C臂工作模式: 1=同步模式(跟随手术床), -1=镜像模式, 0=脱离模式(独立控制)",
        "inputSchema": {
            "type": "object",
            "properties": {"mode": {"type": "integer", "enum": [1, -1, 0]}},
            "required": ["mode"],
        },
    },
    {
        "name": "emergency_stop",
        "description": "紧急停止所有设备。触发后所有设备不可操作，需调用 reset_emergency 恢复。仅在紧急情况下使用。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "reset_emergency",
        "description": "解除紧急停止状态，恢复设备正常操作。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]
