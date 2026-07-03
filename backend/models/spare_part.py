"""备件数据模型"""
from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class SparePart(Base):
    __tablename__ = "spare_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="")
    stock: Mapped[int] = mapped_column(Integer, default=0)
    min_stock: Mapped[int] = mapped_column(Integer, default=1)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    alternatives: Mapped[str] = mapped_column(String(500), default="")
    applicable_devices: Mapped[str] = mapped_column(String(200), default="")

    def to_dict(self) -> dict:
        return {
            "part_no": self.part_no,
            "name": self.name,
            "category": self.category,
            "stock": self.stock,
            "min_stock": self.min_stock,
            "lead_time_days": self.lead_time_days,
            "unit_price": self.unit_price,
            "alternatives": self.alternatives.split(",") if self.alternatives else [],
            "applicable_devices": self.applicable_devices,
            "in_stock": self.stock > 0,
        }
