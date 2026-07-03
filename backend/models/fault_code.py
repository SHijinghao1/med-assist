"""故障码数据模型"""
from sqlalchemy import String, Integer, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from db.database import Base


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DeviceType(str, enum.Enum):
    SURGICAL_BED = "surgical_bed"
    C_ARM = "c_arm"


class FaultCode(Base):
    __tablename__ = "fault_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    device_type: Mapped[DeviceType] = mapped_column(SAEnum(DeviceType), nullable=False)
    component: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(SAEnum(Severity), nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, default="")
    action_steps: Mapped[str] = mapped_column(Text, default="")
    related_parts: Mapped[str] = mapped_column(String(500), default="")

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "device_type": self.device_type.value,
            "component": self.component,
            "description": self.description,
            "severity": self.severity.value,
            "root_cause": self.root_cause,
            "action_steps": self.action_steps,
            "related_parts": self.related_parts,
        }
