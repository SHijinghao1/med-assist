"""Tool: 设备实时状态查询 (Mock)"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.device import Device
from tools.base import QueryDeviceStatusInput
from utils.logging import log


# Mock 关节数据（实际对接 Modbus/WebSocket）
_MOCK_JOINTS = {
    "surgical_bed": {
        "bed_height_joint": 750, "bed_tilt_joint": 0, "bed_lateral_joint": 0,
        "bed_front_back_joint": 0, "bed_panel_back_joint": 0, "bed_head_board_joint": 0,
        "bed_panel_left_leg_joint": 0, "bed_panel_right_leg_joint": 0,
        "bed_panel_left_leg_lower_joint": 0, "bed_panel_right_leg_lower_joint": 0,
    },
    "c_arm": {
        "arm_height_joint": 350, "arm_tilt_joint": 0,
        "c_ring_rotation_joint": 0, "arm_front_back_joint": 150,
    },
}

_MOCK_SENSORS = {
    "surgical_bed": {
        "motor_currents": {"back_panel": 1.2, "tilt": 0.8, "height": 2.1},
        "temperatures": {"motor_back": 35, "motor_tilt": 32, "controller": 38},
        "faults": [],
    },
    "c_arm": {
        "motor_currents": {"arm_height": 1.5, "arm_rotation": 2.0},
        "temperatures": {"motor_height": 40, "xray_tube": 42},
        "faults": [],
    },
}


async def query_device_status(db: AsyncSession, input_data: QueryDeviceStatusInput | dict) -> dict:
    """查询设备实时运行状态"""
    if isinstance(input_data, dict):
        input_data = QueryDeviceStatusInput(**input_data)

    device_type = input_data.device_type.value
    device_id = input_data.device_id

    # 查设备注册信息
    stmt = select(Device).where(Device.device_id == device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    joints = _MOCK_JOINTS.get(device_type, {})
    sensors = _MOCK_SENSORS.get(device_type, {})

    log.info("tool.device_status", device_type=device_type, device_id=device_id)

    return {
        "device_id": device_id,
        "device_type": device_type,
        "device_info": device.to_dict() if device else None,
        "joints": joints,
        "sensors": sensors,
        "status": "online",
        "faults": sensors.get("faults", []),
    }
