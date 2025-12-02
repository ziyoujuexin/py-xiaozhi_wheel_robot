"""
机器人工具管理器.

负责机器人工具的初始化、配置和MCP工具注册
"""

from email.policy import default
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .robot_controller import get_robot_controller_instance

logger = get_logger(__name__)

STOP = 0
SWING = 1
WAVE = 2
NOD = 3
HAPPY = 4
MAD = 5
SAD = 6
NORMAL = 7

class RobotToolsManager:
    """
    机器人工具管理器.
    """

    def __init__(self):
        """
        初始化机器人工具管理器.
        """
        self._initialized = False
        self._robot_controller = None
        logger.info("[RobotManager] 机器人工具管理器初始化")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        初始化并注册所有机器人工具.
        """
        try:
            logger.info("[RobotManager] 开始注册机器人工具")

            # 获取机器人控制器单例实例
            self._robot_controller = get_robot_controller_instance()


            # 注册情感控制工具
            self._register_emotion_detection_tools(add_tool, PropertyList, Property, PropertyType)
            
            # 注册移动控制工具
            self._register_move_tools(add_tool, PropertyList, Property, PropertyType)

            # 注册机械臂控制工具
            self._register_arm_tools(add_tool, PropertyList, Property, PropertyType)

            
            # 注册传感器读取工具
            # self._register_sensor_tools(add_tool, PropertyList)

            # # 注册人体跟随工具
            self._register_human_following_tools(add_tool, PropertyList)

            # 注册声源追踪工具（旧链路）已禁用，改用声控声源定位
            # self._register_sound_following_tools(add_tool, PropertyList)

            # 注册获取状态工具
            # self._register_get_status_tool(add_tool, PropertyList)

            # 注册声控/声源定位工具
            self._register_sound_track_tools(add_tool, PropertyList, Property, PropertyType)

            self._initialized = True
            logger.info("[RobotManager] 机器人工具注册完成")

        except Exception as e:
            logger.error(f"[RobotManager] 机器人工具注册失败: {e}", exc_info=True)
            raise
    def _register_emotion_detection_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        注册情绪感应工具 
        """
        async def send_emotion_feeling_wrapper(args: Dict[str,Any]) ->str:
            model = args.get("model", STOP)
            result = await self._robot_controller.start_emotion_detection(model)
            return result.get("message", "已发送情绪模式")
        

        emotion_prop = PropertyList(
            [
                Property("model", PropertyType.INTEGER, min_value=STOP, default_value=STOP),
            ]
        )
        add_tool(
            (
                "robot_controller.send_emotion_mode",
                # "本工具用于发送机器人的情绪"
                "该工具用于向客户端反馈大模型在对话过程中感知到的机器人自身应该有的语义情绪或应答情绪。"
                "当模型根据聊天内容判断当前应表达某种情绪状态时,可调用此工具,通过传入一个整数参数来表示对应的情绪类型。"
                "调用条件："
                "当对话内容明显表达出喜悦、悲伤、困惑等情绪时；"
                "感受到用户心情较为愉悦、低落、思考等明显情绪时；"
                "机器人认为自己有较为明显的情绪时"
                "当大模型认为回应应当带有情绪色彩以增强共情能力时；"
                "当机器人未听懂用户的意思时，可传入思考情绪。"
                # "不需频繁调用,仅在情绪状态发生显著变化或关键交互节点时触发。"
                "参数说明:"
                "model:区别不同情绪的变量"
                "检测到表示开心,愉悦等积极情绪时,传入4"
                "检测到表示疑惑，思考，不解等情绪时,传入5"
                "检测到表示难过,伤心等情绪时,传入6"
                "当用户明确要求,如:做一个开心的动作:传入4"
                "做一个思考的动作:传入5"
                "做一个悲伤的动作:传入6"
                "你很开心：检测到机器人现在情绪较为积极，传入4"
                "动作描述："
                "开心：微微抬头，手臂斜上举后微微摆动；"
                "疑惑：头部微偏，手举起来挠挠头"
                "悲伤：双手抱头，头部左右摇晃。",
                emotion_prop,
                send_emotion_feeling_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册情感模式控制工具完成")
    
    
    def _register_human_following_tools(self, add_tool, PropertyList):
        """
        注册人体跟随控制工具.
        """

        async def start_human_following_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.start_human_following()
            return result.get("message", "人体跟随模式已开启")

        add_tool(
            (
                "robot_controller.start_human_following",
                "开启机器人的人体跟随模式。"
                "在以下情况下使用此工具：\n"
                "1. 用户要求机器人跟随人、跟着我、跟我走等\n"
                "2. 用户希望机器人自动跟随移动\n"
                "3. 用户使用诸如'跟随模式'、'人体跟踪'、'跟着我走'等表达\n"
                "开启后,机器人将通过视觉传感器自动检测并跟随前方的人体。",
                PropertyList(),
                start_human_following_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册开启人体跟随工具成功")

        async def stop_human_following_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.stop_human_following()
            return result.get("message", "人体跟随模式已关闭")

        add_tool(
            (
                "robot_controller.stop_human_following",
                "关闭机器人的人体跟随模式。"
                "在以下情况下使用此工具：\n"
                "1. 用户要求停止跟随、取消跟随模式\n"
                "2. 用户希望手动控制机器人移动\n"
                "3. 用户使用诸如'停止跟随'、'关闭跟踪'、'取消跟随'等表达\n"
                "关闭后,机器人将停止自动跟随,恢复手动控制模式。",
                PropertyList(),
                stop_human_following_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册关闭人体跟随工具成功")

    def _register_sound_following_tools(self, add_tool, PropertyList):
        """
        注册声源追踪控制工具.
        """

        async def start_sound_following_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.start_sound_following()
            return result.get("message", "声源追踪模式已开启")

        add_tool(
            (
                "robot_controller.start_sound_following",
                "开启机器人的声源追踪模式。"
                "在以下情况下使用此工具：\n"
                "1. 用户要求机器人追踪声音、寻找声源、听声辨位等\n"
                "2. 用户希望机器人自动转向声源方向\n"
                "3. 用户使用诸如'声源追踪'、'声音跟踪'、'寻找声音'等表达\n"
                "开启后,机器人将通过麦克风阵列自动检测并转向声源方向。"
                "用户要求开启声源追踪，调用本工具后，机器人不要发出声音，不需要回复，只允许说“已启动声源追踪”，避免干扰声源追踪",
                PropertyList(),
                start_sound_following_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册开启声源追踪工具成功")

        async def stop_sound_following_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.stop_sound_following()
            return result.get("message", "声源追踪模式已关闭")

        add_tool(
            (
                "robot_controller.stop_sound_following",
                "关闭机器人的声源追踪模式。"
                "在以下情况下使用此工具：\n"
                "1. 用户要求停止声源追踪、取消声音跟踪\n"
                "2. 用户希望手动控制机器人移动\n"
                "3. 用户使用诸如'停止声源追踪'、'关闭声音跟踪'等表达\n"
                "关闭后,机器人将停止自动转向声源,恢复手动控制模式。",
                PropertyList(),
                stop_sound_following_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册关闭声源追踪工具成功")

    def _register_move_tools(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        注册移动控制工具.
        """

        async def move_forward_wrapper(args: Dict[str, Any]) -> str:
            duration = args.get("duration", 5.0)
            speed = args.get("speed", 0.2)
            result = await self._robot_controller.move_forward(float(duration), float(speed))
            return result.get("message", "前进完成")

        forward_props = PropertyList(
            [
                Property("duration", PropertyType.INTEGER, min_value=1, default_value=5),
                Property("speed", PropertyType.INTEGER, min_value=1, max_value=5, default_value=2)
            ]
        )

        add_tool(
            (
                "robot_controller.move_forward",
                "控制机器人向前移动指定时间和速度。使用此功能让机器人向前行进。"
                "用户命令机器人前进,向前走时,调用该工具"
                "参数说明：'duration'向前前进的时间（秒）；'speed'前进速度（m/s）。"
                "用户未指定速度、时间时,不传入参数。"
                "用户说明需求速度时间时,将速度传入speed内,时间传入duration",
                forward_props,
                move_forward_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册前进工具成功")

        async def move_backward_wrapper(args: Dict[str, Any]) -> str:
            duration = args.get("duration", 5.0)
            speed = args.get("speed", 0.2)
            result = await self._robot_controller.move_backward(float(duration), float(speed))
            return result.get("message", "后退完成")

        backward_props = PropertyList(
            [
                Property("duration", PropertyType.INTEGER, min_value=1, default_value=5),
                Property("speed", PropertyType.INTEGER, min_value=1, max_value=5, default_value=2)
            ]
        )

        add_tool(
            (
                "robot_controller.move_backward",
                "控制机器人向后移动指定时间和速度。使用此功能让机器人向后移动。"
                "用户命令机器人后退,向后走时调用此工具"
                "参数说明：'duration'向前前进的时间（秒）；'speed'前进速度（m/s）。"
                "用户未指定速度、时间时,不传入参数。"
                "用户说明需求速度时间时,将速度传入speed内,时间传入duration",
                backward_props,
                move_backward_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册后退工具成功")

        async def turn_left_wrapper(args: Dict[str, Any]) -> str:
            duration = args.get("duration", 2.0)
            speed = args.get("speed", 0.5)
            result = await self._robot_controller.turn_left(float(duration), float(speed))
            return result.get("message", "左转完成")

        left_props = PropertyList(
            [
                Property("duration", PropertyType.INTEGER, min_value=1, default_value=5),
                Property("speed", PropertyType.INTEGER, min_value=1, max_value=5, default_value=2)
            ]
        )

        add_tool(
            (
                "robot_controller.turn_left",
                "控制机器人向左转向指定时间和速度。使用此功能改变机器人的方向向左。"
                "用户命令机器人左转、向左看时,调用此工具"
                "参数说明：'duration'向前前进的时间（秒）；'speed'前进速度（rad/s）。"
                "用户未指定速度、时间时,不传入参数。"
                "用户说明需求速度时间时,将速度传入speed内,时间传入duration",
                left_props,
                turn_left_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册左转工具成功")

        async def turn_right_wrapper(args: Dict[str, Any]) -> str:
            duration = args.get("duration", 2.0)
            speed = args.get("speed", 0.5)
            result = await self._robot_controller.turn_right(float(duration), float(speed))
            return result.get("message", "右转完成")

        right_props = PropertyList(
            [
                Property("duration", PropertyType.INTEGER, min_value=1, default_value=5),
                Property("speed", PropertyType.INTEGER, min_value=1, max_value=5, default_value=2)
            ]
        )

        add_tool(
            (
                "robot_controller.turn_right",
                "控制机器人向右转向指定时间和速度。使用此功能改变机器人的方向向右。"
                "用户命令机器人右转、向右看时调用此工具"
                "参数说明：'duration'向前前进的时间（秒）；'speed'转向速度（rad/s）。"
                "用户未指定速度、时间时,不传入参数。"
                "用户说明需求速度时间时,将速度传入speed内,时间传入duration",
                right_props,
                turn_right_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册右转工具成功")

        async def stop_robot_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.stop()
            return result.get("message", "停止完成")

        add_tool(
            (
                "robot_controller.stop",
                "立即停止机器人的所有移动。使用此功能在任何时候停止机器人。"
                "用户要求机器人停下来,命令机器人停止运动时,调用此工具",
                PropertyList(),
                stop_robot_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册停止工具成功")

    def _register_arm_tools(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        注册机器人功能.
        """


        async def action_wrapper(args: Dict[str,Any]) ->str:
            model = args.get("model")
            result = await self._robot_controller.action(model)
            return result.get("message", "动作组执行完成")

        action_prop = PropertyList(
            [
                Property("model", PropertyType.INTEGER,default_value=STOP)
            ]
        )

        add_tool(
            (
                "robot_controller.actionGroup",
                "本工具包含机器人的一些动作组,"
                "动作组包含：点头、挥手、摆臂"
                "当用户要求机器人点头/摆臂/挥手时，调用此工具。"
                "当用户要求机器人表演才艺时，随机调用某一个动作组。"
                "参数说明："
                "model：控制执行的动作组"
                "当要调用点头动作组时，传入3"
                "当要调用挥手动作组时，传入2"
                "当要调用摆臂动作组时，传入1"
                "注意：严禁与robot_controller.greet工具同时调用",
                action_prop,
                action_wrapper
            )
        )


        async def greet_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.greet()
            return result.get("message", "打招呼完成")

        add_tool(
            (
                "robot_controller.greet",
                "机器人使用手臂执行物理打招呼动作。"
                "在以下情况下使用此工具：\n"
                # "1. 用户首次与机器人交互时（初始问候）\n"
                "2. 用户明确要求机器人说你好，打招呼时\n"
                "3. 用户处于社交性或介绍性对话场景中,问候在上下文中是合适的（例如对话开始阶段、自我介绍后）\n"
                "4. 用户期望机器人通过非语言的具身动作回应,以表达对存在或友好的认可\n"
                "5. 用户使用诸如“说 hello”、“挥个手”、“跟我打招呼”、“你好机器人”等类似表达明确请求问候\n"
                "机器人将通过手臂做出挥手或问候动作,以回应并确认用户的互动。"
                "Endlish:"
                # "1. Initiates the first interaction with the robot (initial greeting) \n"
                "2. Explicitly requests the robot to say hello, wave, or greet in any form \n"
                "3. Engages in a social or introductory context where a greeting is contextually appropriate (e.g., beginning of a conversation, post-introduction) \n"
                "4. Expects a non-verbal, embodied response to acknowledge presence or friendliness \n"
                "5. Explicitly requests a greeting using phrases such as 'say hello', 'wave hello', 'greet me', 'hello robot', or similar \n"
                "The robot will perform a waving or greeting motion with its arm to acknowledge the user. "
                "example:“说 hello”、“跟我打招呼”、“你好机器人”、“打个招呼吧”、“向我问好”\n",
                PropertyList(),
                greet_wrapper,
            )
        )
        logger.info("[RobotManager] 注册打招呼成功")

        async def release_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.release()
            return result.get("message", "回位完成")

        add_tool(
            (
                "robot_controller.release",
                "【回位】当用户要求机器人立正,恢复,手臂垂下等场景时,调用此工具"
                "功能：控制机器人手臂回到初始位置",
                PropertyList(),
                release_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册释放工具成功")

    def _register_light_tools(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        注册灯光控制工具.
        """

        async def turn_on_light_wrapper(args: Dict[str, Any]) -> str:
            level = args.get("level", 50)
            result = await self._robot_controller.turn_on_light(int(level))
            return result.get("message", "灯光已打开")

        light_props = PropertyList(
            [
                Property(
                    "level",
                    PropertyType.INTEGER,
                    min_value=0,
                    max_value=100,
                    default_value=50,
                )
            ]
        )

        add_tool(
            (
                "robot_controller.turn_on_light",
                "Turn on the robot's lights and set the brightness level. "
                "Use this to illuminate the environment or for visual effects.",
                light_props,
                turn_on_light_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册打开灯光工具成功")

        async def turn_off_light_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.turn_off_light()
            return result.get("message", "灯光已关闭")

        add_tool(
            (
                "robot_controller.turn_off_light",
                "Turn off the robot's lights. Use this to turn off the lights when not needed.",
                PropertyList(),
                turn_off_light_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册关闭灯光工具成功")

    def _register_sensor_tools(self, add_tool, PropertyList):
        """
        注册传感器读取工具.
        """

        async def read_sensors_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.read_sensors()
            if result.get("status") == "success":
                data = result.get("data", {})
                sensor_info = []
                sensor_info.append(f"距离: {data.get('distance', 0.0):.2f}米")
                sensor_info.append(f"温度: {data.get('temperature', 0.0):.2f}°C")
                sensor_info.append(f"湿度: {data.get('humidity', 0.0):.2f}%")
                if data.get("camera"):
                    sensor_info.append(f"摄像头: {data.get('camera')}")
                return "传感器数据:\n" + "\n".join(sensor_info)
            else:
                return result.get("message", "读取传感器数据失败")

        add_tool(
            (
                "robot_controller.read_sensors",
                "Read the robot's sensor data including distance, temperature, humidity, and camera. "
                "Use this to get information about the robot's environment.",
                PropertyList(),
                read_sensors_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册传感器读取工具成功")

    def _register_get_status_tool(self, add_tool, PropertyList):
        """
        注册获取状态工具.
        """

        async def get_status_wrapper(args: Dict[str, Any]) -> str:
            result = await self._robot_controller.get_status()
            if result.get("status") == "success":
                state = result.get("state", {})
                status_info = []
                status_info.append(f"当前位置: {state.get('position', (0, 0))}")
                status_info.append(f"当前朝向: {state.get('orientation', 0)}°")
                status_info.append(f"机械臂状态: {state.get('arm_state', 'idle')}")
                status_info.append(f"灯光亮度: {state.get('light_level', 0)}%")
                status_info.append(f"人体跟随模式: {'开启' if state.get('human_following_mode', False) else '关闭'}")
                status_info.append(f"声源追踪模式: {'开启' if state.get('sound_following_mode', False) else '关闭'}")  # 添加声源追踪状态
                return "\n".join(status_info)
            else:
                return "获取机器人状态失败"

        add_tool(
            (
                "robot_controller.get_status",
                "Get the current status of the robot including position, orientation, arm state, light level, human following mode, and sound following mode. "
                "Use this to check the robot's current state and environment.",
                PropertyList(),
                get_status_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册获取状态工具成功")

    def _register_sound_track_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        注册声控跟踪状态工具，用于“来这里/来我这边/到我这里来”触发。
        """

        async def set_sound_track_state_wrapper(args: Dict[str, Any]) -> str:
            state = args.get("state", 1)
            result = await self._robot_controller.set_sound_track_state(state)
            return result.get("message", f"sound_track_state 已设为 {state}")

        props = PropertyList(
            [
                Property("state", PropertyType.INTEGER, default_value=1, min_value=0, max_value=10),
            ]
        )

        add_tool(
            (
                "robot_controller.set_sound_track_state",
                "当用户说“来这里”、“来我这边”、“到我这里来”、“到我身边来”、“过来”时调用本工具。"
                "作用：设置 /sound_track_state（默认1 = 开始第一次追踪），驱动声源+雷达联合跟随流程。"
                "不要在无关对话中调用，避免误触发运动。",
                props,
                set_sound_track_state_wrapper,
            )
        )
        logger.debug("[RobotManager] 注册声控跟踪状态工具成功")

    def is_initialized(self) -> bool:
        """
        检查管理器是否已初始化.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        获取管理器状态.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 15,  # 更新工具数量（新增2个声源追踪工具）
            "available_tools": [
                "move_forward",
                "move_backward",
                "turn_left",
                "turn_right",
                "stop",
                "greet",
                "release",
                "turn_on_light",
                "turn_off_light",
                "read_sensors",
                "start_human_following",
                "stop_human_following",
                "start_sound_following",  # 新增
                "stop_sound_following",   # 新增
                "get_status",
            ],
            "robot_controller_ready": self._robot_controller is not None,
        }


# 全局管理器实例
_robot_tools_manager = None


def get_robot_tools_manager() :
    """
    获取机器人工具管理器单例.
    """
    global _robot_tools_manager
    if _robot_tools_manager is None:
        _robot_tools_manager = RobotToolsManager()
        logger.debug("[RobotManager] 创建机器人工具管理器实例")
    return _robot_tools_manager
