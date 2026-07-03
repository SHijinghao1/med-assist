"""手术床 + C臂 硬件控制工具（合并自 IOBS MCP Server）"""
import copy
from typing import Optional

# ── 关节元数据（与 iobs-mcp-server 保持一致）──
BED_JOINTS: dict[str, dict] = {
    "bed_height_joint":           {"label": "床体高度", "unit": "mm", "min": 500, "max": 1000},
    "bed_tilt_joint":             {"label": "倾斜 (Trendelenburg)", "unit": "°", "min": -22, "max": 22},
    "bed_lateral_joint":          {"label": "侧倾", "unit": "°", "min": -15, "max": 15},
    "bed_front_back_joint":       {"label": "前后平移", "unit": "mm", "min": -200, "max": 200},
    "bed_panel_back_joint":       {"label": "背板角度", "unit": "°", "min": -70, "max": 70},
    "bed_head_board_joint":       {"label": "头板角度", "unit": "°", "min": -70, "max": 70},
    "bed_panel_left_leg_joint":   {"label": "左腿板", "unit": "°", "min": -90, "max": 90},
    "bed_panel_right_leg_joint":  {"label": "右腿板", "unit": "°", "min": -90, "max": 90},
    "bed_panel_left_leg_lower_joint":  {"label": "左下腿板", "unit": "°", "min": -90, "max": 90},
    "bed_panel_right_leg_lower_joint": {"label": "右下腿板", "unit": "°", "min": -90, "max": 90},
}

CARM_JOINTS: dict[str, dict] = {
    "arm_height_joint":         {"label": "C臂高度", "unit": "mm", "min": 300, "max": 400},
    "arm_tilt_joint":           {"label": "C臂旋转", "unit": "°", "min": -185, "max": 185},
    "c_ring_rotation_joint":    {"label": "C臂前后旋转", "unit": "°", "min": -30, "max": 30},
    "arm_front_back_joint":     {"label": "C臂前后平移", "unit": "mm", "min": 0, "max": 350},
}

BED_PRESETS: dict[str, dict] = {
    "flat": {"name": "平卧位", "state": {"bed_height_joint":750,"bed_tilt_joint":0,"bed_lateral_joint":0,"bed_front_back_joint":0,"bed_panel_back_joint":0}},
    "trendelenburg": {"name": "头低脚高位", "state": {"bed_height_joint":700,"bed_tilt_joint":-15,"bed_panel_back_joint":0}},
    "reverse_trendelenburg": {"name": "头高脚低位", "state": {"bed_height_joint":750,"bed_tilt_joint":15}},
    "beach_chair": {"name": "沙滩椅位", "state": {"bed_height_joint":650,"bed_panel_back_joint":70,"bed_tilt_joint":10}},
    "lithotomy": {"name": "截石位", "state": {"bed_height_joint":600,"bed_panel_left_leg_joint":60,"bed_panel_right_leg_joint":60}},
    "lateral_left": {"name": "左侧卧位", "state": {"bed_lateral_joint":-15}},
    "lateral_right": {"name": "右侧卧位", "state": {"bed_lateral_joint":15}},
}

# ── 内存设备状态 ──
_device_state: dict = {
    "bed": {
        "bed_height_joint": 750, "bed_tilt_joint": 0, "bed_lateral_joint": 0,
        "bed_front_back_joint": 0, "bed_panel_back_joint": 0, "bed_head_board_joint": 0,
        "bed_panel_left_leg_joint": 0, "bed_panel_right_leg_joint": 0,
        "bed_panel_left_leg_lower_joint": 0, "bed_panel_right_leg_lower_joint": 0,
    },
    "cArm": {
        "arm_height_joint": 350, "arm_tilt_joint": 0,
        "c_ring_rotation_joint": 0, "arm_front_back_joint": 150,
    },
    "cArmMode": 0,  # 1=sync, -1=mirror, 0=free
    "emergencyStopped": False,
}


# ── 工具函数 ──

async def get_device_state(args: dict | None = None) -> dict:
    """获取手术室完整设备状态"""
    s = copy.deepcopy(_device_state)
    # 关节中文标注
    bed_info = {}
    for joint, meta in BED_JOINTS.items():
        bed_info[joint] = {"value": s["bed"].get(joint, 0), "label": meta["label"], "unit": meta["unit"], "range": [meta["min"], meta["max"]]}
    carm_info = {}
    for joint, meta in CARM_JOINTS.items():
        carm_info[joint] = {"value": s["cArm"].get(joint, 0), "label": meta["label"], "unit": meta["unit"], "range": [meta["min"], meta["max"]]}
    mode_name = {1: "同步模式", -1: "镜像模式", 0: "脱离模式"}.get(s["cArmMode"], "未知")
    return {
        "bed": bed_info,
        "cArm": carm_info,
        "cArmMode": mode_name,
        "emergencyStopped": s["emergencyStopped"],
    }


async def list_joints(args: dict | None = None) -> dict:
    """列出所有可控关节和体位预设"""
    return {
        "bed_joints": [{"name": j, "label": m["label"], "unit": m["unit"], "range": [m["min"], m["max"]]} for j, m in BED_JOINTS.items()],
        "carm_joints": [{"name": j, "label": m["label"], "unit": m["unit"], "range": [m["min"], m["max"]]} for j, m in CARM_JOINTS.items()],
        "presets": [{"id": pid, "name": p["name"]} for pid, p in BED_PRESETS.items()],
    }


async def move_bed_joint(args: dict) -> dict:
    """移动手术床指定关节"""
    if _device_state["emergencyStopped"]:
        return {"ok": False, "error": "系统已紧急停止，无法操作"}
    joint = args.get("joint", "")
    if joint not in BED_JOINTS:
        return {"ok": False, "error": f"未知关节: {joint}"}
    meta = BED_JOINTS[joint]
    old = _device_state["bed"].get(joint, 0)

    target = args.get("target_value")
    delta = args.get("delta")
    if target is not None:
        new_val = float(target)
    elif delta is not None:
        new_val = old + float(delta)
    else:
        return {"ok": False, "error": "请提供 target_value 或 delta"}

    new_val = max(meta["min"], min(meta["max"], new_val))
    _device_state["bed"][joint] = new_val
    return {"ok": True, "joint": joint, "label": meta["label"], "old": old, "new": new_val, "unit": meta["unit"]}


async def move_carm_joint(args: dict) -> dict:
    """移动C臂指定关节"""
    if _device_state["emergencyStopped"]:
        return {"ok": False, "error": "系统已紧急停止，无法操作"}
    joint = args.get("joint", "")
    if joint not in CARM_JOINTS:
        return {"ok": False, "error": f"未知关节: {joint}"}
    meta = CARM_JOINTS[joint]
    old = _device_state["cArm"].get(joint, 0)

    target = args.get("target_value")
    delta = args.get("delta")
    if target is not None:
        new_val = float(target)
    elif delta is not None:
        new_val = old + float(delta)
    else:
        return {"ok": False, "error": "请提供 target_value 或 delta"}

    new_val = max(meta["min"], min(meta["max"], new_val))
    _device_state["cArm"][joint] = new_val
    return {"ok": True, "joint": joint, "label": meta["label"], "old": old, "new": new_val, "unit": meta["unit"]}


async def apply_bed_preset(args: dict) -> dict:
    """应用手术体位预设"""
    if _device_state["emergencyStopped"]:
        return {"ok": False, "error": "系统已紧急停止"}
    preset_id = args.get("preset_id", "")
    preset = BED_PRESETS.get(preset_id)
    if not preset:
        ids = ", ".join(BED_PRESETS.keys())
        return {"ok": False, "error": f"未找到预设: {preset_id}。可用: {ids}"}
    for joint, val in preset["state"].items():
        meta = BED_JOINTS.get(joint)
        if meta:
            _device_state["bed"][joint] = max(meta["min"], min(meta["max"], val))
    return {"ok": True, "preset": preset["name"]}


async def set_carm_mode(args: dict) -> dict:
    """设置C臂工作模式"""
    mode = args.get("mode", 0)
    if mode not in (1, -1, 0):
        return {"ok": False, "error": "无效模式: 1=同步, -1=镜像, 0=脱离"}
    _device_state["cArmMode"] = mode
    name = {1: "同步", -1: "镜像", 0: "脱离"}[mode]
    return {"ok": True, "mode": mode, "name": name}


async def emergency_stop(args: dict | None = None) -> dict:
    """紧急停止"""
    _device_state["emergencyStopped"] = True
    return {"ok": True, "message": "紧急停止已触发！所有设备不可操作"}


async def reset_emergency(args: dict | None = None) -> dict:
    """解除紧急停止"""
    _device_state["emergencyStopped"] = False
    return {"ok": True, "message": "紧急停止已解除"}
