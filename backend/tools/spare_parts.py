"""Tool: 备件库存查询"""
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.spare_part import SparePart
from tools.base import QuerySparePartsInput
from utils.logging import log


async def query_spare_parts(
    db: AsyncSession,
    input_data: QuerySparePartsInput | dict,
) -> dict:
    """查询备件库存"""
    if isinstance(input_data, dict):
        input_data = QuerySparePartsInput(**input_data)

    stmt = select(SparePart)

    if input_data.part_no:
        stmt = stmt.where(SparePart.part_no == input_data.part_no.upper())
    elif input_data.part_name:
        stmt = stmt.where(or_(
            SparePart.name.ilike(f"%{input_data.part_name}%"),
            SparePart.category.ilike(f"%{input_data.part_name}%"),
        ))

    stmt = stmt.limit(20)
    result = await db.execute(stmt)
    parts = result.scalars().all()

    log.info("tool.spare_parts",
             part_name=input_data.part_name,
             part_no=input_data.part_no,
             hits=len(parts))

    return {
        "count": len(parts),
        "parts": [p.to_dict() for p in parts],
        "suggestion": _suggest(parts) if parts else "未找到匹配的备件",
    }


def _suggest(parts: list[SparePart]) -> str:
    low_stock = [p for p in parts if p.stock <= p.min_stock]
    if low_stock:
        names = ", ".join(p.name for p in low_stock)
        return f"⚠️ 以下备件库存不足: {names}"
    return f"所有备件库存充足"
