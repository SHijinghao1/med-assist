"""Agent 意图路由测试"""
from agent.router import route_intent


class TestIntentRouting:
    def test_diagnosis_intent(self):
        assert route_intent("背板报E1023怎么办") == "diagnosis"
        assert route_intent("手术床故障了") == "diagnosis"
        assert route_intent("设备异常，不工作了") == "diagnosis"
        assert route_intent("报警了，怎么排查") == "diagnosis"
        assert route_intent("什么原因导致背板不动") == "diagnosis"

    def test_repair_intent(self):
        assert route_intent("背板电机怎么更换") == "repair"
        assert route_intent("怎么拆背板") == "repair"
        assert route_intent("维修步骤") == "repair"
        assert route_intent("校准传感器") == "repair"
        assert route_intent("背板怎么修理") == "repair"

    def test_parts_intent(self):
        assert route_intent("背板电机备件库存") == "parts"
        assert route_intent("有没有配件") == "parts"
        assert route_intent("MTR-BK-001型号") == "parts"
        assert route_intent("备件订货") == "parts"

    def test_default_to_diagnosis(self):
        """未知意图默认走诊断"""
        assert route_intent("你好") == "diagnosis"
        assert route_intent("今天天气怎么样") == "diagnosis"

    def test_multiple_keywords(self):
        """多关键词取最高分"""
        result = route_intent("故障了怎么修")
        # "故障"→diagnosis, "怎么修"→repair, either is fine
        assert result in ("diagnosis", "repair")
