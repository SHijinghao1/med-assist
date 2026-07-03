"""Tool: 历史维修记录搜索"""
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from models.maintenance_log import MaintenanceLog
from tools.base import SearchMaintenanceLogsInput
from utils.logging import log


async def search_maintenance_logs(
    db: AsyncSession,
    input_data: SearchMaintenanceLogsInput | dict,
) -> dict:
    """搜索历史维修记录 (BM25 关键词 + 语义兜底由 retriever 处理)"""
    if isinstance(input_data, dict):
        input_data = SearchMaintenanceLogsInput(**input_data)

    query = input_data.query
    device_type = input_data.device_type
    days = input_data.date_range_days

    since = datetime.utcnow() - timedelta(days=days)

    stmt = select(MaintenanceLog).where(
        MaintenanceLog.created_at >= since
    )

    if device_type:
        stmt = stmt.where(MaintenanceLog.device_type == device_type.value)

    # 关键词模糊匹配
    stmt = stmt.where(or_(
        MaintenanceLog.fault_code.ilike(f"%{query}%"),
        MaintenanceLog.description.ilike(f"%{query}%"),
        MaintenanceLog.solution.ilike(f"%{query}%"),
    ))

    stmt = stmt.order_by(MaintenanceLog.created_at.desc()).limit(20)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    log.info("tool.maintenance_logs", query=query[:50], hits=len(logs))

    return {
        "query": query,
        "date_range_days": days,
        "count": len(logs),
        "records": [log.to_dict() for log in logs],
    }
