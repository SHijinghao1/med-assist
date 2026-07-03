"""Tool: 创建维修工单"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from tools.base import CreateWorkOrderInput
from utils.logging import log


async def create_work_order(
    db: AsyncSession,
    input_data: CreateWorkOrderInput | dict,
) -> dict:
    """创建维修工单"""
    if isinstance(input_data, dict):
        input_data = CreateWorkOrderInput(**input_data)

    order_id = f"WO-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    log.info("tool.work_order.created",
             order_id=order_id,
             device_id=input_data.device_id,
             priority=input_data.priority.value)

    return {
        "order_id": order_id,
        "device_id": input_data.device_id,
        "fault_description": input_data.fault_description,
        "priority": input_data.priority.value,
        "assigned_to": input_data.assigned_to or "待分配",
        "status": "created",
        "created_at": datetime.utcnow().isoformat(),
    }
