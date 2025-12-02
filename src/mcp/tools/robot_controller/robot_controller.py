"""
机器人控制单例实现.

提供单例模式的机器人控制器，在注册时初始化，支持异步操作。
"""

import asyncio
from email import message
import string
import time
from typing import Dict, List, Optional, Tuple
import rclpy
from rclpy.node import Node
import std_msgs
from std_msgs.msg import Int32, Int8
from geometry_msgs.msg import Twist

# from src.constants.constants import RobotConfig
from src.utils.logging_config import get_logger
import std_msgs.msg

STOP = 0
SWING = 1
WAVE = 2
logger = get_logger(__name__)


class RobotRosNode(Node):
    def __init__(self):
        super().__init__("robotControlNode")
        # 机械臂控制发布器
        self.modelPub = self.create_publisher(Int32, "/model", 10)
        # 移动控制发布器 - 使用geometry_msgs/Twist消息类型
        # 为避免干扰，仅用于语音/非跟随场景，改为独立话题，默认不占用主cmd_vel
        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel_voice", 10)
        # 模式控制发布器 - 添加人体跟随控制
        self.mode_pub = self.create_publisher(Int8, "/mode", 10)
        # 声源/自定义跟踪状态控制发布器
        self.sound_track_state_pub = self.create_publisher(Int8, "/sound_track_state", 10)
        # 声源追踪控制发布器
        try:
            # 尝试导入自定义消息类型
            from wheeltec_mic_msg.msg import MotionControl
            self.motion_control_msg_type = MotionControl
            self.sound_follow_pub = self.create_publisher(MotionControl, "/motion_msg", 10)
            self.has_sound_follow = True
        except ImportError:
            logger.warning("wheeltec_mic_msg包未找到，声源追踪功能不可用")
            self.has_sound_follow = False
            self.sound_follow_pub = None
        
    def publishModel(self, model: int = STOP):
        msg = std_msgs.msg.Int32()
        msg.data = model
        self.modelPub.publish(msg)
        
    def publish_velocity(self, linear_x: float = 0.0, angular_z: float = 0.0):
        """发布速度命令到/cmd_vel话题"""
        msg = Twist()
        msg.linear.x = linear_x*0.1
        msg.linear.y = 0.0
        msg.linear.z = 0.0
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = angular_z*0.1
        self.cmd_vel_pub.publish(msg)
    
    def publish_mode(self, mode: int = 1):
        """发布模式命令到/mode话题"""
        msg = std_msgs.msg.Int8()
        msg.data = mode
        self.mode_pub.publish(msg)

    def publish_sound_track_state(self, state: int = 1):
        """发布声源/声控跟踪状态到/sound_track_state"""
        msg = std_msgs.msg.Int8()
        msg.data = state
        self.sound_track_state_pub.publish(msg)
    
    def publish_sound_follow(self, follow_flag: int = 1, linear_x: float = 0.0, angular_z: float = 0.0, cmd_vel_flag: int = 0):
        """发布声源追踪控制命令"""
        if not self.has_sound_follow or self.sound_follow_pub is None:
            logger.warning("声源追踪功能不可用")
            return False
        
        try:
            msg = self.motion_control_msg_type()
            msg.follow_flag = follow_flag
            msg.linear_x = linear_x
            msg.angular_z = angular_z
            msg.cmd_vel_flag = cmd_vel_flag
            self.sound_follow_pub.publish(msg)
            return True
        except Exception as e:
            logger.error(f"发布声源追踪命令失败: {e}")
            return False


class RobotController:
    """机器人控制器 - 专为IoT设备设计

    实现真正的ROS2移动控制功能
    """

    def __init__(self):
        # 初始化ROS2节点
        rclpy.init()
        self.node = RobotRosNode()
        
        # 核心状态
        self.is_moving = False
        self.current_position = (0, 0)  # (x, y) 坐标
        self.current_orientation = 0  # 0: 前, 90: 右, 180: 后, 270: 左
        self.arm_state = "release"  # "release" "movement" "greeting"
        self.light_level = 0  # 0-100, 0表示关闭
        self.human_following_mode = False  # 人体跟随模式状态
        self.sound_following_mode = False  # 声源追踪模式状态
        self.sensor_data = {
            "distance": 0.0,  # 米
            "temperature": 0.0,  # 摄氏度
            "humidity": 0.0,  # 百分比
            "camera": None,  # 摄像头图像数据
        }

        logger.info("机器人控制器单例初始化完成")

    def __del__(self):
        rclpy.shutdown()

    async def start_emotion_detection(self, model = STOP) -> Dict[str, str]:
        """
        用户情绪模式
        """
        try:
            self.node.publishModel(model)
            logger.info("发送情绪模式")
            return {
                "status": "success",
                "message": "已发送给情绪模式"
            }
        except Exception as e:
            logger.error(f"发送情绪模式失败：{e}")
            return {"status": "error", "message": f"发送情绪模式失败：{str(e)}"}
        
        
    # 人体跟随控制
    async def start_human_following(self) -> Dict[str, str]:
        """
        开启人体跟随模式.
        """
        try:
            # 如果声源追踪模式开启，先关闭
            if self.sound_following_mode:
                await self.stop_sound_following()
                
            self.node.publish_mode(2)  # 发布人体跟随开启指令
            self.human_following_mode = True
            logger.info("人体跟随模式已开启")
            return {
                "status": "success", 
                "message": "人体跟随模式已开启，机器人将自动跟随检测到的人体"
            }
        except Exception as e:
            logger.error(f"开启人体跟随失败: {e}")
            return {"status": "error", "message": f"开启人体跟随失败: {str(e)}"}

    async def stop_human_following(self) -> Dict[str, str]:
        """
        关闭人体跟随模式.
        """
        try:
            self.node.publish_mode(1)  # 发布人体跟随关闭指令
            self.human_following_mode = False
            logger.info("人体跟随模式已关闭")
            return {"status": "success", "message": "人体跟随模式已关闭"}
        except Exception as e:
            logger.error(f"关闭人体跟随失败: {e}")
            return {"status": "error", "message": f"关闭人体跟随失败: {str(e)}"}

    # 声源追踪控制
    async def start_sound_following(self) -> Dict[str, str]:
        """
        开启声源追踪模式.
        """
        try:
            # 如果人体跟随模式开启，先关闭
            if self.human_following_mode:
                await self.stop_human_following()
                
            success = self.node.publish_sound_follow(
                follow_flag=1, 
                linear_x=0.0, 
                angular_z=0.0, 
                cmd_vel_flag=0
            )
            
            if success:
                self.sound_following_mode = True
                logger.info("声源追踪模式已开启")
                return {
                    "status": "success", 
                    "message": "声源追踪模式已开启，机器人将自动追踪声源方向"
                }
            else:
                return {"status": "error", "message": "声源追踪功能不可用"}
                
        except Exception as e:
            logger.error(f"开启声源追踪失败: {e}")
            return {"status": "error", "message": f"开启声源追踪失败: {str(e)}"}

    async def stop_sound_following(self) -> Dict[str, str]:
        """
        关闭声源追踪模式.
        """
        try:
            success = self.node.publish_sound_follow(
                follow_flag=0, 
                linear_x=0.0, 
                angular_z=0.0, 
                cmd_vel_flag=0
            )
            
            if success:
                self.sound_following_mode = False
                logger.info("声源追踪模式已关闭")
                return {"status": "success", "message": "声源追踪模式已关闭"}
            else:
                return {"status": "error", "message": "声源追踪功能不可用"}
                
        except Exception as e:
            logger.error(f"关闭声源追踪失败: {e}")
            return {"status": "error", "message": f"关闭声源追踪失败: {str(e)}"}

    # 机器人移动控制 - 实现真正的ROS2控制
    async def move_forward(self, duration: int = 2, speed: int = 2) -> Dict[str, str]:
        """
        前进指定时间（秒）和速度（米/秒）.
        """
        try:
            # 如果人体跟随模式开启，先关闭
            if self.human_following_mode:
                await self.stop_human_following()
            # 如果声源追踪模式开启，先关闭
            if self.sound_following_mode:
                await self.stop_sound_following()
                
            self.is_moving = True
            logger.info(f"机器人开始前进，速度: {speed} 米/秒，持续时间: {duration} 秒")
            
            # 发布前进命令
            start_time = time.time()
            while time.time() - start_time < duration:
                self.node.publish_velocity(linear_x=speed, angular_z=0.0)
                await asyncio.sleep(0.1)  # 10Hz发布频率
            # self.node.publish_velocity(linear_x=speed, angular_z=0.0)
            # await asyncio.sleep(duration)  # 10Hz发布频率
            
            # 停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            
            # 更新位置（模拟）
            distance = speed * duration
            # self.current_position = (self.current_position[0] + distance, self.current_position[1])

            logger.info(f"机器人前进完成，移动距离: {distance:.2f} 米")
            return {
                "status": "success",
                "message": f"机器人已前进 {distance:.2f} 米",
                "position": self.current_position,
            }
        except Exception as e:
            logger.error(f"前进失败: {e}")
            # 确保在异常时停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            return {"status": "error", "message": f"前进失败: {str(e)}"}

    async def move_backward(self, duration: int = 2, speed: int = 2) -> Dict[str, str]:
        """
        后退指定时间（秒）和速度（米/秒）.
        """
        try:
            # 如果人体跟随模式开启，先关闭
            if self.human_following_mode:
                await self.stop_human_following()
            # 如果声源追踪模式开启，先关闭
            if self.sound_following_mode:
                await self.stop_sound_following()
                
            self.is_moving = True
            logger.info(f"机器人开始后退，速度: {speed} 米/秒，持续时间: {duration} 秒")
            
            # 发布后退命令（负速度）
            start_time = time.time()
            while time.time() - start_time < duration:
                self.node.publish_velocity(linear_x=-speed, angular_z=0.0)
                await asyncio.sleep(0.1)  # 10Hz发布频率
            
            # 停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            
            # 更新位置（模拟）
            distance = speed * duration
            self.current_position = (self.current_position[0] - distance, self.current_position[1])

            logger.info(f"机器人后退完成，移动距离: {distance:.2f} 米")
            return {
                "status": "success",
                "message": f"机器人已后退 {distance:.2f} 米",
                "position": self.current_position,
            }
        except Exception as e:
            logger.error(f"后退失败: {e}")
            # 确保在异常时停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            return {"status": "error", "message": f"后退失败: {str(e)}"}

    async def turn_left(self, duration: int = 2, speed: int = 2) -> Dict[str, str]:
        """
        左转指定时间（秒）和角速度（弧度/秒）.
        """
        try:
            # 如果人体跟随模式开启，先关闭
            if self.human_following_mode:
                await self.stop_human_following()
            # 如果声源追踪模式开启，先关闭
            if self.sound_following_mode:
                await self.stop_sound_following()
                
            self.is_moving = True
            logger.info(f"机器人开始左转，角速度: {speed} 弧度/秒，持续时间: {duration} 秒")
            
            # 发布左转命令（正角速度）
            start_time = time.time()
            while time.time() - start_time < duration:
                self.node.publish_velocity(linear_x=0.0, angular_z=speed)
                await asyncio.sleep(0.1)  # 10Hz发布频率
            
            # 停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            
            # 更新朝向（模拟）
            angle_degrees = (speed * duration * 180 / 3.14159)  # 弧度转角度
            self.current_orientation = (self.current_orientation - angle_degrees) % 360

            logger.info(f"机器人左转完成，转向角度: {angle_degrees:.1f} 度")
            return {
                "status": "success",
                "message": f"机器人已左转 {angle_degrees:.1f} 度",
                "orientation": self.current_orientation,
            }
        except Exception as e:
            logger.error(f"左转失败: {e}")
            # 确保在异常时停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            return {"status": "error", "message": f"左转失败: {str(e)}"}

    async def turn_right(self, duration: int = 2, speed: int = 2) -> Dict[str, str]:
        """
        右转指定时间（秒）和角速度（弧度/秒）.
        """
        try:
            # 如果人体跟随模式开启，先关闭
            if self.human_following_mode:
                await self.stop_human_following()
            # 如果声源追踪模式开启，先关闭
            if self.sound_following_mode:
                await self.stop_sound_following()
                
            self.is_moving = True
            logger.info(f"机器人开始右转，角速度: {speed} 弧度/秒，持续时间: {duration} 秒")
            
            # 发布右转命令（负角速度）
            start_time = time.time()
            while time.time() - start_time < duration:
                self.node.publish_velocity(linear_x=0.0, angular_z=-speed)
                await asyncio.sleep(0.1)  # 10Hz发布频率
            
            # 停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            
            # 更新朝向（模拟）
            angle_degrees = (speed * duration * 180 / 3.14159)  # 弧度转角度
            self.current_orientation = (self.current_orientation + angle_degrees) % 360

            logger.info(f"机器人右转完成，转向角度: {angle_degrees:.1f} 度")
            return {
                "status": "success",
                "message": f"机器人已右转 {angle_degrees:.1f} 度",
                "orientation": self.current_orientation,
            }
        except Exception as e:
            logger.error(f"右转失败: {e}")
            # 确保在异常时停止机器人
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            return {"status": "error", "message": f"右转失败: {str(e)}"}

    async def stop(self) -> Dict[str, str]:
        """
        立即停止机器人移动.
        """
        try:
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            self.is_moving = False
            logger.info("机器人已停止")
            return {"status": "success", "message": "机器人已停止"}
        except Exception as e:
            logger.error(f"停止失败: {e}")
            return {"status": "error", "message": f"停止失败: {str(e)}"}

    # 机械臂控制

    async def action(self, model = STOP) -> Dict[str, str]:
        """
        机器人动作组控制。
        """
        try:
            self.node.publishModel(model)
            logger.info(f"动作组执行完成{model}")
            return {"status": "success", "message": "动作组执行完成"}
        except Exception as e:
            logger.error(f"执行失败：{e}")
            return {"status": "error", "message": f"动作组执行失败：{str(e)}"}


    async def greet(self) -> Dict[str, str]:
        """
        机器人打招呼.
        """
        try:
            self.node.publishModel(WAVE)
            logger.info("打招呼完成")
            return {"status": "success", "message": "打招呼完成"}

        except Exception as e:
            logger.error(f"抓取失败: {e}")
            return {"status": "error", "message": f"抓取失败: {str(e)}"}

    async def release(self) -> Dict[str, str]:
        """
        手臂归位.
        """
        try:
            if self.arm_state == "released":
                return {"status": "info", "message": "回位完成"}
            self.node.publishModel(STOP)
            self.arm_state = "released"
            await asyncio.sleep(0.5)  # 模拟释放时间

            logger.info("回位完成")
            return {"status": "success", "message": "回位完成"}

        except Exception as e:
            logger.error(f"回位失败: {e}")
            return {"status": "error", "message": f"回位失败: {str(e)}"}

    async def move_arm(self, position: str) -> Dict[str, str]:
        """
        移动机械臂到指定位置.
        
        位置参数: "home", "pickup", "drop"
        """
        try:
            if position not in ["home", "pickup", "drop"]:
                return {"status": "error", "message": "无效的位置参数"}

            # 模拟移动
            self.arm_state = "moving"
            await asyncio.sleep(0.5)
            self.arm_state = "idle"

            logger.info(f"机械臂已移动到 {position} 位置")
            return {
                "status": "success",
                "message": f"机械臂已移动到 {position} 位置",
                "position": position,
            }
        except Exception as e:
            logger.error(f"移动机械臂失败: {e}")
            return {"status": "error", "message": f"移动机械臂失败: {str(e)}"}

    # 灯光控制
    async def turn_on_light(self, level: int = 50) -> Dict[str, str]:
        """
        打开灯光并设置亮度.
        """
        try:
            if level < 0 or level > 100:
                return {"status": "error", "message": "亮度值必须在0-100之间"}

            self.light_level = level
            logger.info(f"灯光已打开，亮度: {level}%")
            return {"status": "success", "message": f"灯光已打开，亮度: {level}%"}
        except Exception as e:
            logger.error(f"打开灯光失败: {e}")
            return {"status": "error", "message": f"打开灯光失败: {str(e)}"}

    async def turn_off_light(self) -> Dict[str, str]:
        """
        关闭灯光.
        """
        try:
            self.light_level = 0
            logger.info("灯光已关闭")
            return {"status": "success", "message": "灯光已关闭"}
        except Exception as e:
            logger.error(f"关闭灯光失败: {e}")
            return {"status": "error", "message": f"关闭灯光失败: {str(e)}"}

    # 传感器读取
    async def read_sensors(self) -> Dict[str, str]:
        """
        读取传感器数据.
        """
        try:
            # 模拟传感器读取
            self.sensor_data["distance"] = 1.5 + (time.time() % 5) * 0.1  # 模拟距离
            self.sensor_data["temperature"] = 25.0 + (time.time() % 10) * 0.1  # 模拟温度
            self.sensor_data["humidity"] = 50.0 + (time.time() % 10) * 0.5  # 模拟湿度
            self.sensor_data["camera"] = f"camera_image_{int(time.time())}"  # 模拟摄像头图像

            logger.info("传感器数据已读取")
            return {
                "status": "success",
                "message": "传感器数据已读取",
                "data": self.sensor_data,
            }
        except Exception as e:
            logger.error(f"读取传感器数据失败: {e}")
            return {"status": "error", "message": f"读取传感器数据失败: {str(e)}"}

    # 状态查询
    async def get_status(self) -> Dict[str, str]:
        """
        获取机器人当前状态.
        """
        try:
            return {
                "status": "success",
                "message": "机器人状态查询成功",
                "state": {
                    "position": self.current_position,
                    "orientation": self.current_orientation,
                    "arm_state": self.arm_state,
                    "light_level": self.light_level,
                    "human_following_mode": self.human_following_mode,
                    "sound_following_mode": self.sound_following_mode,  # 添加声源追踪状态
                    "sensor_data": self.sensor_data,
                    "is_moving": self.is_moving,
                },
            }
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return {"status": "error", "message": f"获取状态失败: {str(e)}"}

    # 属性getter方法
    async def get_current_position(self):
        return self.current_position

    async def get_current_orientation(self):
        return self.current_orientation

    async def get_arm_state(self):
        return self.arm_state

    async def get_light_level(self):
        return self.light_level

    async def get_sensor_data(self):
        return self.sensor_data

    async def get_human_following_mode(self):
        return self.human_following_mode

    async def get_sound_following_mode(self):
        return self.sound_following_mode

    async def set_sound_track_state(self, state: int = 1) -> Dict[str, str]:
        """
        设置声源/声控跟踪状态，默认1表示开始第一次追踪。
        """
        try:
            self.node.publish_sound_track_state(state)
            logger.info(f"发布sound_track_state: {state}")
            return {"status": "success", "message": f"sound_track_state 已设为 {state}"}
        except Exception as e:
            logger.error(f"设置sound_track_state失败: {e}")
            return {"status": "error", "message": f"设置sound_track_state失败: {str(e)}"}

    def __del__(self):
        """
        清理资源.
        """
        try:
            # 确保机器人停止和所有模式关闭
            self.node.publish_velocity(linear_x=0.0, angular_z=0.0)
            if self.human_following_mode:
                self.node.publish_mode(1)
            if self.sound_following_mode:
                self.node.publish_sound_follow(follow_flag=0)
            logger.info("机器人控制器资源清理完成")
        except Exception:
            # 忽略错误
            pass


# 全局机器人控制器实例
_robot_controller_instance = None


def get_robot_controller_instance() -> RobotController:
    """
    获取机器人控制器单例.
    """
    global _robot_controller_instance
    if _robot_controller_instance is None:
        _robot_controller_instance = RobotController()
        logger.info("[RobotController] 创建机器人控制器单例实例")
    return _robot_controller_instance
