"""Tool 函数 + Pydantic 校验测试"""
import pytest
from tools.base import (
    QueryDeviceStatusInput, SearchFaultCodeInput, SearchMaintenanceLogsInput,
    QuerySparePartsInput, RunDiagnosticsInput, CreateWorkOrderInput,
    DeviceType, BedJoint, CArmJoint, DiagnosticsCommand, WorkOrderPriority,
)


class TestQueryDeviceStatusInput:
    def test_valid_surgical_bed(self):
        inp = QueryDeviceStatusInput(device_type="surgical_bed", device_id="SB-00123")
        assert inp.device_type == DeviceType.SURGICAL_BED

    def test_valid_carm(self):
        inp = QueryDeviceStatusInput(device_type="c_arm", device_id="CA-00456")
        assert inp.device_type == DeviceType.C_ARM

    def test_invalid_device_type(self):
        with pytest.raises(ValueError):
            QueryDeviceStatusInput(device_type="laser", device_id="SB-00123")

    def test_invalid_device_id_format(self):
        with pytest.raises(ValueError):
            QueryDeviceStatusInput(device_type="surgical_bed", device_id="bad-id")


class TestSearchFaultCodeInput:
    def test_valid(self):
        inp = SearchFaultCodeInput(code="E1023")
        assert inp.code == "E1023"

    def test_too_short(self):
        with pytest.raises(ValueError):
            SearchFaultCodeInput(code="E")

    def test_too_long(self):
        with pytest.raises(ValueError):
            SearchFaultCodeInput(code="E" * 30)


class TestSearchMaintenanceLogsInput:
    def test_valid_minimal(self):
        inp = SearchMaintenanceLogsInput(query="back panel noise")
        assert inp.date_range_days == 90

    def test_invalid_date_range(self):
        with pytest.raises(ValueError):
            SearchMaintenanceLogsInput(query="test", date_range_days=0)
        with pytest.raises(ValueError):
            SearchMaintenanceLogsInput(query="test", date_range_days=400)


class TestQuerySparePartsInput:
    def test_by_name(self):
        inp = QuerySparePartsInput(part_name="motor")
        assert inp.part_name == "motor"

    def test_by_part_no(self):
        inp = QuerySparePartsInput(part_no="MTR-BK-001")
        assert inp.part_no == "MTR-BK-001"

    def test_both_empty_fails(self):
        with pytest.raises(ValueError):
            QuerySparePartsInput()


class TestRunDiagnosticsInput:
    def test_valid(self):
        inp = RunDiagnosticsInput(
            device_id="SB-00123",
            command="motor_reset",
            joint_name="bed_panel_back_joint",
        )
        assert inp.command == DiagnosticsCommand.MOTOR_RESET

    def test_carm_joint_on_bed_fails(self):
        with pytest.raises(ValueError):
            RunDiagnosticsInput(
                device_id="SB-00123",
                command="motor_reset",
                joint_name="arm_tilt_joint",  # C-arm joint on surgical bed
            )

    def test_invalid_command(self):
        with pytest.raises(ValueError):
            RunDiagnosticsInput(
                device_id="SB-00123",
                command="destroy_machine",
                joint_name="bed_panel_back_joint",
            )


class TestCreateWorkOrderInput:
    def test_valid(self):
        inp = CreateWorkOrderInput(
            device_id="SB-00123",
            fault_description="Back panel motor overload",
            priority="high",
        )
        assert inp.priority == WorkOrderPriority.HIGH

    def test_description_too_short(self):
        with pytest.raises(ValueError):
            CreateWorkOrderInput(
                device_id="SB-00123",
                fault_description="bad",
                priority="low",
            )
