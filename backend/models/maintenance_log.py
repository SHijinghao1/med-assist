"""维修记录数据模型"""
from sqlalchemy import String, Integer, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from db.database import Base
from models.fault_code import DeviceType, Severity


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType), nullable=False)
    device_id: Mapped[str] = mapped_column(String(20), index=True)
    fault_code: Mapped[str] = mapped_column(String(20), index=True, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, default="")
    solution: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity), default=Severity.MEDIUM)
    engineer: Mapped[str] = mapped_column(String(50), default="")
    parts_used: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "device_type": self.device_type.value,
            "device_id": self.device_id,
            "fault_code": self.fault_code,
            "description": self.description,
            "root_cause": self.root_cause,
            "solution": self.solution,
            "severity": self.severity.value,
            "engineer": self.engineer,
            "parts_used": self.parts_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
