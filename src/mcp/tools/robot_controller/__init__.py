"""
机器人控制工具包.

提供完整的机器人控制功能，包括移动、打招呼、手臂归位、人体跟随、声源追踪等操作。
"""

from .robot_controller import get_robot_controller_instance
from .manager import RobotToolsManager, get_robot_tools_manager

__all__ = [
    "RobotToolsManager",
    "get_robot_tools_manager",
    "get_robot_controller_instance",
]