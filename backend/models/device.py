"""设备数据模型"""
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from db.database import Base
from models.fault_code import DeviceType


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    device_type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="")
    ip_address: Mapped[str] = mapped_column(String(50), default="")
    modbus_port: Mapped[int] = mapped_column(Integer, default=502)
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # online/offline/maintenance/error
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "name": self.name,
            "location": self.location,
            "status": self.status,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
