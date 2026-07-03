"""Tool 基类: Pydantic 入参校验"""
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from typing import Literal, Optional


# ── 枚举 ──

class DeviceType(str, Enum):
    SURGICAL_BED = "surgical_bed"
    C_ARM = "c_arm"


class BedJoint(str, Enum):
    HEIGHT = "bed_height_joint"
    TILT = "bed_tilt_joint"
    LATERAL = "bed_lateral_joint"
    FRONT_BACK = "bed_front_back_joint"
    PANEL_BACK = "bed_panel_back_joint"
    HEAD_BOARD = "bed_head_board_joint"
    LEFT_LEG = "bed_panel_left_leg_joint"
    RIGHT_LEG = "bed_panel_right_leg_joint"
    LEFT_LEG_LOWER = "bed_panel_left_leg_lower_joint"
    RIGHT_LEG_LOWER = "bed_panel_right_leg_lower_joint"


class CArmJoint(str, Enum):
    HEIGHT = "arm_height_joint"
    TILT = "arm_tilt_joint"
    C_RING = "c_ring_rotation_joint"
    FRONT_BACK = "arm_front_back_joint"


JointName = BedJoint | CArmJoint


class DiagnosticsCommand(str, Enum):
    MOTOR_RESET = "motor_reset"
    CURRENT_TEST = "current_test"
    SENSOR_CALIBRATION = "sensor_calibration"
    SELF_TEST = "self_test"


class WorkOrderPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Tool 入参 Models ──

class QueryDeviceStatusInput(BaseModel):
    device_type: DeviceType
    device_id: str = Field(..., pattern=r"^(SB|CA)-\d{3,5}$",
                           examples=["SB-00123"])


class SearchFaultCodeInput(BaseModel):
    code: str = Field(..., min_length=2, max_length=20)


class SearchMaintenanceLogsInput(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    device_type: Optional[DeviceType] = None
    date_range_days: int = Field(default=90, ge=1, le=365)


class QuerySparePartsInput(BaseModel):
    part_name: Optional[str] = None
    part_no: Optional[str] = None

    @model_validator(mode="after")
    def check_at_least_one(self):
        if not self.part_name and not self.part_no:
            raise ValueError("必须提供 part_name 或 part_no 中的一个")
        return self


class RunDiagnosticsInput(BaseModel):
    device_id: str = Field(..., pattern=r"^(SB|CA)-\d{3,5}$")
    command: DiagnosticsCommand
    joint_name: JointName

    @model_validator(mode="after")
    def validate_joint_device_match(self):
        c_arm_joints = {j.value for j in CArmJoint}
        if self.joint_name.value in c_arm_joints and self.device_id.startswith("SB"):
            raise ValueError(f"C臂关节 '{self.joint_name.value}' 不能用于手术床设备")
        return self


class CreateWorkOrderInput(BaseModel):
    device_id: str = Field(..., pattern=r"^(SB|CA)-\d{3,5}$")
    fault_description: str = Field(..., min_length=5, max_length=2000)
    priority: WorkOrderPriority
    assigned_to: Optional[str] = None
