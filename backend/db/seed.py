"""种子数据: 故障码 + 备件 + 维修记录"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from models.fault_code import FaultCode, Severity, DeviceType
from models.spare_part import SparePart
from models.maintenance_log import MaintenanceLog
from utils.logging import log


FAULT_CODES = [
    # ── 手术床故障码 ──
    {"code":"E1023","device_type":DeviceType.SURGICAL_BED,"component":"背板电机","description":"背板驱动电机过载保护触发，电流超出正常工作范围","severity":Severity.HIGH,"root_cause":"导轨润滑不足、机械卡滞、电机轴承磨损","action_steps":"1.断开电源手动转动背板检查卡滞感\n2.检查导轨润滑脂状态\n3.万用表测量电机三相绕组电阻(标准2.1Ω±10%)\n4.检测控制板电流采样电路","related_parts":"MTR-BK-001,GRS-BK-001"},
    {"code":"E1024","device_type":DeviceType.SURGICAL_BED,"component":"腿板传感器","description":"右腿板位置传感器信号异常，读数跳变或超出量程","severity":Severity.MEDIUM,"root_cause":"传感器接线松动、传感器内部故障、控制板ADC通道损坏","action_steps":"1.检查传感器接线端子\n2.万用表测量传感器输出\n3.校准传感器零位\n4.更换传感器模块","related_parts":"SEN-RL-001"},
    {"code":"E1025","device_type":DeviceType.SURGICAL_BED,"component":"腿板电机","description":"左腿板驱动电机过流保护","severity":Severity.HIGH,"root_cause":"腿板机械卡滞、电机负载过大、驱动板故障","action_steps":"1.检查腿板机械传动机构\n2.测量电机电流\n3.检查驱动板MOS管\n4.更换电机或驱动板","related_parts":"MTR-LL-001,DRV-LL-001"},
    {"code":"E2001","device_type":DeviceType.SURGICAL_BED,"component":"床体升降机构","description":"床体高度调节时出现异响，升降不平稳","severity":Severity.MEDIUM,"root_cause":"液压系统气阻、丝杆磨损、导轨间隙过大","action_steps":"1.检查液压油位\n2.液压系统排气\n3.检查丝杆和导轨\n4.重新校准高度传感器","related_parts":"HYD-BED-001,GLD-BED-001"},
    {"code":"E2002","device_type":DeviceType.SURGICAL_BED,"component":"Trendelenburg倾斜机构","description":"床体倾斜功能失效，无法调节头低脚高位","severity":Severity.HIGH,"root_cause":"倾斜电机驱动故障、限位开关失效、传动齿轮断裂","action_steps":"1.检查倾斜电机供电\n2.测试限位开关通断\n3.检查传动齿轮\n4.更换电机驱动器","related_parts":"MTR-TL-001,LSW-TL-001"},
    {"code":"E2003","device_type":DeviceType.SURGICAL_BED,"component":"侧倾机构","description":"床体侧倾角度无法保持，自动回位","severity":Severity.MEDIUM,"root_cause":"侧倾电磁阀泄漏、液压缸密封失效","action_steps":"1.检查电磁阀线圈电阻\n2.更换电磁阀密封件\n3.检查液压管路泄漏\n4.重新标定侧倾传感器","related_parts":"SV-LT-001,SEAL-LT-001"},
    {"code":"E3001","device_type":DeviceType.SURGICAL_BED,"component":"主控制器","description":"主控制器通信异常，触摸屏无响应","severity":Severity.CRITICAL,"root_cause":"控制器电源模块故障、CAN总线短路、固件崩溃","action_steps":"1.检查24V供电是否正常\n2.重新上电复位\n3.检查CAN总线终端电阻\n4.更换主控制器","related_parts":"CTRL-MAIN-001,PSU-24V-001"},
    {"code":"E3002","device_type":DeviceType.SURGICAL_BED,"component":"手控器","description":"手控器按键失灵或误触发","severity":Severity.MEDIUM,"root_cause":"薄膜按键老化、线缆断裂、接口氧化","action_steps":"1.清洁按键触点\n2.检查线缆连接\n3.更换手控器","related_parts":"HC-BED-001"},
    {"code":"ESTOP","device_type":DeviceType.SURGICAL_BED,"component":"急停系统","description":"紧急停止按钮被触发或回路断开","severity":Severity.CRITICAL,"root_cause":"人为触发急停、急停回路断线、安全继电器故障","action_steps":"1.确认是否人为触发\n2.检查急停回路接线\n3.安全继电器测试\n4.系统复位","related_parts":"ESB-ALL-001,RLY-SF-001"},

    # ── C臂故障码 ──
    {"code":"E4001","device_type":DeviceType.C_ARM,"component":"C臂旋转机构","description":"C臂旋转角度与实际位置偏差超过±2°","severity":Severity.HIGH,"root_cause":"编码器零点漂移、旋转轴轴承磨损、伺服电机参数偏移","action_steps":"1.执行编码器归零校准\n2.检查旋转轴轴承状态\n3.伺服驱动器参数恢复出厂\n4.替换编码器","related_parts":"ENC-CA-001,BRG-CA-001"},
    {"code":"E4002","device_type":DeviceType.C_ARM,"component":"C臂升降机构","description":"C臂高度调节时电机堵转","severity":Severity.HIGH,"root_cause":"升降导轨卡滞、电机过载、配重失衡","action_steps":"1.检查导轨是否有异物\n2.检测电机电流\n3.检查配重块\n4.润滑导轨","related_parts":"MTR-CA-LF-001,GLD-CA-001"},
    {"code":"E4003","device_type":DeviceType.C_ARM,"component":"X射线发生器","description":"X射线管过热保护，无法曝光","severity":Severity.CRITICAL,"root_cause":"冷却系统故障、连续曝光时间过长、管球老化","action_steps":"1.等待自然冷却30分钟\n2.检查冷却风扇运转\n3.检查散热风道是否堵塞\n4.联系厂家更换管球","related_parts":"XRAY-TUBE-001,FAN-CA-001"},
    {"code":"E4004","device_type":DeviceType.C_ARM,"component":"影像系统","description":"图像噪点严重，或图像完全黑屏","severity":Severity.HIGH,"root_cause":"平板探测器故障、图像采集卡损坏、线缆接触不良","action_steps":"1.检查探测器连接线缆\n2.重启影像系统\n3.执行暗场校正\n4.更换平板探测器","related_parts":"FPD-CA-001,CBL-CA-001"},
    {"code":"E4005","device_type":DeviceType.C_ARM,"component":"C臂前后平移","description":"C臂前后移动时有异响，移动不流畅","severity":Severity.MEDIUM,"root_cause":"平移导轨润滑不足、滑块磨损、同步带松动","action_steps":"1.清洁并润滑平移导轨\n2.检查滑块磨损情况\n3.调整同步带张力\n4.更换磨损滑块","related_parts":"GLD-CA-002,SLD-CA-001"},
    {"code":"E4006","device_type":DeviceType.C_ARM,"component":"准直器","description":"准直器叶片无法开合或位置异常","severity":Severity.MEDIUM,"root_cause":"步进电机故障、叶片机械卡滞、限位传感器脏污","action_steps":"1.清洁限位传感器\n2.手动转动检查机械卡滞\n3.测试步进电机线圈\n4.更换准直器组件","related_parts":"COL-CA-001,STM-COL-001"},
    {"code":"E5001","device_type":DeviceType.C_ARM,"component":"工作站","description":"工作站无法开机或频繁重启","severity":Severity.CRITICAL,"root_cause":"电源故障、内存接触不良、硬盘损坏、主板故障","action_steps":"1.检查电源适配器输出\n2.重新插拔内存条\n3.进入BIOS检查硬件状态\n4.更换故障部件","related_parts":"PSU-WS-001,RAM-WS-001"},
    {"code":"E5002","device_type":DeviceType.C_ARM,"component":"脚踏开关","description":"脚踏开关无响应或误触发","severity":Severity.LOW,"root_cause":"开关微动损坏、线缆断裂、接口松动","action_steps":"1.检查脚踏开关接线\n2.测试微动开关通断\n3.更换脚踏开关","related_parts":"FSW-CA-001"},
]

SPARE_PARTS = [
    {"part_no":"MTR-BK-001","name":"背板驱动电机总成","category":"电机","stock":5,"min_stock":2,"lead_time_days":3,"alternatives":"MTR-BK-002","applicable_devices":"surgical_bed"},
    {"part_no":"MTR-BK-002","name":"背板驱动电机总成(升级版)","category":"电机","stock":2,"min_stock":1,"lead_time_days":7,"alternatives":"MTR-BK-001","applicable_devices":"surgical_bed"},
    {"part_no":"GRS-BK-001","name":"背板导轨润滑脂(专用)","category":"耗材","stock":20,"min_stock":5,"lead_time_days":1,"alternatives":"GRS-UNI-001","applicable_devices":"surgical_bed"},
    {"part_no":"GRS-UNI-001","name":"通用医用级硅脂","category":"耗材","stock":50,"min_stock":10,"lead_time_days":1,"alternatives":"","applicable_devices":"surgical_bed,c_arm"},
    {"part_no":"SEN-RL-001","name":"右腿板位置传感器模块","category":"传感器","stock":3,"min_stock":1,"lead_time_days":7,"alternatives":"SEN-RL-002","applicable_devices":"surgical_bed"},
    {"part_no":"SEN-RL-002","name":"腿板位置传感器(高精度版)","category":"传感器","stock":1,"min_stock":1,"lead_time_days":14,"alternatives":"SEN-RL-001","applicable_devices":"surgical_bed"},
    {"part_no":"MTR-LL-001","name":"左腿板驱动电机","category":"电机","stock":3,"min_stock":1,"lead_time_days":5,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"DRV-LL-001","name":"腿板电机驱动板","category":"驱动器","stock":2,"min_stock":1,"lead_time_days":7,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"HYD-BED-001","name":"液压系统密封维修包","category":"液压","stock":8,"min_stock":3,"lead_time_days":5,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"GLD-BED-001","name":"床体升降导轨组件","category":"机械","stock":2,"min_stock":1,"lead_time_days":14,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"MTR-TL-001","name":"倾斜驱动电机","category":"电机","stock":2,"min_stock":1,"lead_time_days":7,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"LSW-TL-001","name":"倾斜限位开关","category":"开关","stock":10,"min_stock":3,"lead_time_days":2,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"SV-LT-001","name":"侧倾电磁阀","category":"液压","stock":4,"min_stock":1,"lead_time_days":10,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"CTRL-MAIN-001","name":"主控制器总成","category":"控制器","stock":1,"min_stock":1,"lead_time_days":30,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"PSU-24V-001","name":"24V开关电源模块","category":"电源","stock":5,"min_stock":2,"lead_time_days":3,"alternatives":"","applicable_devices":"surgical_bed,c_arm"},
    {"part_no":"HC-BED-001","name":"手控器","category":"操作部件","stock":3,"min_stock":1,"lead_time_days":5,"alternatives":"","applicable_devices":"surgical_bed"},
    {"part_no":"ENC-CA-001","name":"C臂旋转编码器","category":"编码器","stock":2,"min_stock":1,"lead_time_days":14,"alternatives":"ENC-CA-002","applicable_devices":"c_arm"},
    {"part_no":"BRG-CA-001","name":"C臂旋转轴轴承","category":"机械","stock":3,"min_stock":1,"lead_time_days":10,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"MTR-CA-LF-001","name":"C臂升降电机驱动器","category":"驱动器","stock":1,"min_stock":1,"lead_time_days":10,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"GLD-CA-001","name":"C臂升降导轨","category":"机械","stock":1,"min_stock":1,"lead_time_days":21,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"XRAY-TUBE-001","name":"X射线管球总成","category":"核心部件","stock":0,"min_stock":1,"lead_time_days":90,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"FAN-CA-001","name":"冷却风扇组件","category":"散热","stock":5,"min_stock":2,"lead_time_days":3,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"FPD-CA-001","name":"平板探测器","category":"核心部件","stock":0,"min_stock":1,"lead_time_days":60,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"COL-CA-001","name":"准直器组件","category":"光学","stock":1,"min_stock":1,"lead_time_days":30,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"ESB-ALL-001","name":"急停按钮总成","category":"安全部件","stock":10,"min_stock":3,"lead_time_days":2,"alternatives":"","applicable_devices":"surgical_bed,c_arm"},
    {"part_no":"RLY-SF-001","name":"安全继电器","category":"电气","stock":5,"min_stock":2,"lead_time_days":5,"alternatives":"","applicable_devices":"surgical_bed,c_arm"},
    {"part_no":"FSW-CA-001","name":"C臂脚踏开关","category":"操作部件","stock":4,"min_stock":1,"lead_time_days":5,"alternatives":"","applicable_devices":"c_arm"},
    {"part_no":"CBL-CA-001","name":"影像系统连接线缆","category":"线缆","stock":5,"min_stock":2,"lead_time_days":3,"alternatives":"","applicable_devices":"c_arm"},
]

MAINTENANCE_LOGS = [
    {"device_type":DeviceType.SURGICAL_BED,"device_id":"SB-00123","fault_code":"E1023","description":"背板电机过载，操作背板时自动停止","root_cause":"导轨严重缺油，摩擦阻力过大","solution":"清洁导轨并重新涂抹GRS-BK-001润滑脂，电机电流恢复正常","severity":Severity.HIGH,"engineer":"张工","parts_used":"GRS-BK-001","created_at":datetime.utcnow()-timedelta(days=45)},
    {"device_type":DeviceType.SURGICAL_BED,"device_id":"SB-00156","fault_code":"E1023","description":"背板上升时电机异响并报警","root_cause":"背板电机轴承磨损导致转子偏摆","solution":"更换MTR-BK-001背板电机总成，重新校准零位","severity":Severity.HIGH,"engineer":"李工","parts_used":"MTR-BK-001","created_at":datetime.utcnow()-timedelta(days=30)},
    {"device_type":DeviceType.SURGICAL_BED,"device_id":"SB-00089","fault_code":"E1023","description":"背板动作缓慢，偶尔E1023报警","root_cause":"导轨有异物卡滞","solution":"清理导轨异物，润滑后恢复正常","severity":Severity.MEDIUM,"engineer":"王工","parts_used":"GRS-UNI-001","created_at":datetime.utcnow()-timedelta(days=10)},
    {"device_type":DeviceType.SURGICAL_BED,"device_id":"SB-00201","fault_code":"E2002","description":"床体无法倾斜到头低脚高位","root_cause":"倾斜限位开关触点氧化","solution":"更换LSW-TL-001限位开关","severity":Severity.MEDIUM,"engineer":"张工","parts_used":"LSW-TL-001","created_at":datetime.utcnow()-timedelta(days=20)},
    {"device_type":DeviceType.SURGICAL_BED,"device_id":"SB-00178","fault_code":"E2001","description":"床体升降有咯噔异响","root_cause":"丝杆螺母磨损，间隙过大","solution":"更换床体升降导轨组件GLD-BED-001","severity":Severity.MEDIUM,"engineer":"李工","parts_used":"GLD-BED-001,GRS-UNI-001","created_at":datetime.utcnow()-timedelta(days=60)},
    {"device_type":DeviceType.C_ARM,"device_id":"CA-00045","fault_code":"E4001","description":"C臂旋转角度显示偏差约3°","root_cause":"编码器零点漂移","solution":"执行编码器归零校准，恢复正常","severity":Severity.HIGH,"engineer":"赵工","parts_used":"","created_at":datetime.utcnow()-timedelta(days=15)},
    {"device_type":DeviceType.C_ARM,"device_id":"CA-00032","fault_code":"E4003","description":"X射线连续曝光后过热报警","root_cause":"冷却风扇转速不足，散热风道积灰","solution":"清理散热风道，更换冷却风扇FAN-CA-001","severity":Severity.CRITICAL,"engineer":"赵工","parts_used":"FAN-CA-001","created_at":datetime.utcnow()-timedelta(days=7)},
    {"device_type":DeviceType.C_ARM,"device_id":"CA-00078","fault_code":"E4002","description":"C臂升降到高位时堵转","root_cause":"配重块偏移导致负载不平衡","solution":"重新调整配重块位置并紧固","severity":Severity.HIGH,"engineer":"赵工","parts_used":"","created_at":datetime.utcnow()-timedelta(days=90)},
    {"device_type":DeviceType.SURGICAL_BED,"device_id":"SB-00123","fault_code":"ESTOP","description":"术中轻微碰撞导致急停误触发","root_cause":"急停按钮过于灵敏","solution":"按下急停按钮复位，恢复设备操作","severity":Severity.CRITICAL,"engineer":"张工","parts_used":"","created_at":datetime.utcnow()-timedelta(days=5)},
    {"device_type":DeviceType.SURGICAL_BED,"device_id":"SB-00310","fault_code":"E1025","description":"左腿板无法升降","root_cause":"腿板电机驱动板MOS管击穿","solution":"更换DRV-LL-001驱动板","severity":Severity.HIGH,"engineer":"王工","parts_used":"DRV-LL-001","created_at":datetime.utcnow()-timedelta(days=2)},
]


async def seed_all(db: AsyncSession):
    """初始化种子数据"""
    existing_codes = set((await db.execute(select(FaultCode.code))).scalars().all())
    fc_count = 0
    for fc_data in FAULT_CODES:
        if fc_data["code"] not in existing_codes:
            db.add(FaultCode(**fc_data))
            fc_count += 1

    existing_parts = set((await db.execute(select(SparePart.part_no))).scalars().all())
    sp_count = 0
    for sp_data in SPARE_PARTS:
        if sp_data["part_no"] not in existing_parts:
            db.add(SparePart(**sp_data))
            sp_count += 1

    # 维修记录（始终追加新记录）
    existing_log_ids = set((await db.execute(select(MaintenanceLog.id))).scalars().all())
    ml_count = 0
    for ml_data in MAINTENANCE_LOGS:
        db.add(MaintenanceLog(**ml_data))
        ml_count += 1

    await db.commit()
    log.info("seed.complete", fault_codes=fc_count, spare_parts=sp_count, maintenance_logs=ml_count)
