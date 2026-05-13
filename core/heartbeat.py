import threading
from time import sleep
import traceback


class Heartbeat:
    """
    心跳器类，__init__时自动启动线程，__del__时终止线程
    """

    def __init__(self, func, interval=1800, immediate=True):
        """
        初始化心跳器并自动启动线程

        参数:
            func: 要定期执行的函数
            interval: 执行间隔时间（秒），默认为1800秒
            immediate: 是否在初始化时立即执行一次，默认True
        """
        self.func = func
        self.interval = interval
        self.immediate = immediate
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def __del__(self):
        """析构函数，终止线程"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def _run(self):
        """心跳器主循环"""
        if not self.immediate:
            sleep(self.interval)

        while self.running:
            try:
                self.func()
            except Exception:
                traceback.print_exc()

            # 等待下一个心跳周期
            sleep(self.interval)

class DynamicHeartbeat(Heartbeat):
    """
    动态心跳器类，interval可以在运行时动态设置
    """
    def __init__(self, func, interval=1800, first_run=True):
        """
        初始化动态心跳器

        参数:
            func: 要定期执行的函数，返回新的interval值
            interval: 初始执行间隔时间（秒），默认为1800秒
            first_run: 是否在初始化时立即执行一次，默认True
        """
        super().__init__(func, interval, first_run)

    def _run(self):
        """心跳器主循环"""
        if not self.immediate:
            sleep(self.interval)

        while self.running:
            try:
                self.interval = self.func()
            except Exception:
                traceback.print_exc()

            # 等待下一个心跳周期
            sleep(self.interval)
