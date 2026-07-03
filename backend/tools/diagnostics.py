"""Tool: 诊断命令执行 (⚠️ 高危，需 HITL 确认)"""
from sqlalchemy.ext.asyncio import AsyncSession

from tools.base import RunDiagnosticsInput
from utils.logging import log


async def run_diagnostics(
    db: AsyncSession,
    input_data: RunDiagnosticsInput | dict,
) -> dict:
    """
    ⚠️ 高危操作: 执行设备诊断命令。
    调用前必须经过 Human-in-the-Loop 确认。
    """
    if isinstance(input_data, dict):
        input_data = RunDiagnosticsInput(**input_data)

    command = input_data.command.value
    joint = input_data.joint_name.value
    device_id = input_data.device_id

    log.warning("tool.diagnostics.execute",
                command=command, joint=joint, device_id=device_id)

    # Mock 执行结果
    results = {
        "motor_reset": f"✅ {joint} 电机强制复位完成，电流恢复正常",
        "current_test": f"{joint} 电流测试结果: 1.5A (正常范围 0.5-2.0A)",
        "sensor_calibration": f"✅ {joint} 传感器校准完成，偏差 ±0.1°",
        "self_test": f"设备 {device_id} 自检完成: 12/12 项通过",
    }

    return {
        "device_id": device_id,
        "command": command,
        "joint": joint,
        "result": results.get(command, "未知命令"),
        "dangerous": True,
        "executed_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
