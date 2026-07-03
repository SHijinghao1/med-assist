"""Tool: 故障码 SQL 精确查询"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.fault_code import FaultCode
from tools.base import SearchFaultCodeInput
from utils.logging import log


async def search_fault_code(db: AsyncSession, input_data: SearchFaultCodeInput | dict) -> dict:
    """SQL 精确匹配故障码"""
    if isinstance(input_data, dict):
        input_data = SearchFaultCodeInput(**input_data)

    code = input_data.code.upper()
    stmt = select(FaultCode).where(FaultCode.code == code)
    result = await db.execute(stmt)
    fc = result.scalar_one_or_none()

    if fc:
        log.info("tool.fault_code.hit", code=code)
        return {"found": True, "data": fc.to_dict()}
    else:
        log.info("tool.fault_code.miss", code=code)
        return {"found": False, "data": None,
                "message": f"未找到故障码 '{code}'，建议用 search_maintenance_logs 搜索"}
