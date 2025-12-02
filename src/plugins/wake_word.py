from typing import Any

from src.constants.constants import AbortReason
from src.plugins.base import Plugin
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# 声控跟随唤醒短语
SOUND_TRACK_WAKE_WORDS = {
    "来这里",
    "来我这边",
    "到我这里来",
    "到我这边来",
    "过来"
}


class WakeWordPlugin(Plugin):
    name = "wake_word"

    def __init__(self) -> None:
        super().__init__()
        self.app = None
        self.detector = None

    async def setup(self, app: Any) -> None:
        self.app = app
        try:
            from src.audio_processing.wake_word_detect import WakeWordDetector

            self.detector = WakeWordDetector()
            if not getattr(self.detector, "enabled", False):
                self.detector = None
                return

            # 绑定回调
            self.detector.on_detected(self._on_detected)
            self.detector.on_error = self._on_error
        except Exception:
            self.detector = None

    async def start(self) -> None:
        if not self.detector:
            return
        try:
            # 需要音频编码器以提供原始PCM数据
            audio_codec = getattr(self.app, "audio_codec", None)
            if audio_codec is None:
                return
            await self.detector.start(audio_codec)
        except Exception:
            pass

    async def stop(self) -> None:
        if self.detector:
            try:
                await self.detector.stop()
            except Exception:
                pass

    async def shutdown(self) -> None:
        if self.detector:
            try:
                await self.detector.stop()
            except Exception:
                pass

    async def _on_detected(self, wake_word, full_text):
        # 检测到唤醒词：切到自动对话（根据 AEC 自动选择实时/自动停）
        try:
            trigger_sound_track = False
            if isinstance(full_text, str):
                trigger_sound_track = full_text in SOUND_TRACK_WAKE_WORDS

            if trigger_sound_track:
                logger.info(f"检测到声控跟随唤醒短语: {full_text}, 发布 /sound_track_state=1")
                try:
                    from src.mcp.tools.robot_controller import (
                        get_robot_controller_instance,
                    )

                    controller = get_robot_controller_instance()
                    # 发布 sound_track_state=1
                    await controller.set_sound_track_state(1)
                except Exception as e:
                    logger.error(f"发布 sound_track_state 失败: {e}")

            # 若正在说话，交给应用的打断/状态机处理
            if hasattr(self.app, "device_state") and hasattr(
                self.app, "start_auto_conversation"
            ):
                if self.app.is_speaking():
                    await self.app.abort_speaking(AbortReason.WAKE_WORD_DETECTED)
                    audio_plugin = self.app.plugins.get_plugin("audio")
                    if audio_plugin:
                        await audio_plugin.codec.clear_audio_queue()
                else:
                    # 声控跟随唤醒后等待3秒再开始对话，避免干扰角度捕获
                    if trigger_sound_track:
                        await asyncio.sleep(3.0)
                    await self.app.start_auto_conversation()
        except Exception:
            pass

    def _on_error(self, error):
        try:
            if hasattr(self.app, "set_chat_message"):
                self.app.set_chat_message("assistant", f"[KWS错误] {error}")
        except Exception:
            pass
