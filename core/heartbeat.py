from PySide6.QtCore import QTimer, QObject, Signal


class Heartbeat(QObject):
    """心跳器"""
    stopped = Signal()
    def __init__(self, func, interval, immediate=True, parent=None):
        """
        初始化心跳器

        Parameters:
            func (callable): 要定期执行的函数
            interval (int): 执行间隔时间（秒）
            immediate (bool): 是否在初始化时立即执行一次，默认True
            parent (QObject): 父对象
        """
        super().__init__(parent)
        self.func = func
        self.interval = interval
        self.immediate = immediate

    def start(self):
        """启动心跳器"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timeout)
        self.timer.start(self.interval * 1000)  # 转换为毫秒
        if self.immediate:
            self._on_timeout()

    def _on_timeout(self):
        """定时器触发时执行心跳函数"""
        self.func()

    def stop(self):
        """停止心跳器"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        self.stopped.emit()

class DynamicHeartbeat(Heartbeat):
    """动态心跳器，支持根据执行结果调整间隔时间"""

    def __init__(self, func, interval, immediate=True, parent=None):
        """
        初始化动态心跳器

        Parameters:
            func (callable): 要定期执行的函数，返回新的interval值
            interval (int): 初始执行间隔时间（秒）
            immediate (bool): 是否在初始化时立即执行一次，默认True
            parent (QObject): 父对象
        """
        super().__init__(func, interval, immediate, parent)

    def _on_timeout(self):
        """定时器触发时执行检查函数，并根据返回值调整间隔"""
        # 执行检查函数，获取新的间隔时间
        result = self.func()
        if result is not None:
            self.interval = result
            self.timer.stop()
            self.timer.start(self.interval * 1000)  # 转换为毫秒
