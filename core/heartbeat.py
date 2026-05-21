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

        Parameters:
            func (callable): 要定期执行的函数
            interval (int): 执行间隔时间（秒），默认为1800秒
            immediate (bool): 是否在初始化时立即执行一次，默认True
        """
        self.func = func
        self.interval = interval
        self.immediate = immediate
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def __del__(self):
        """析构函数，设置停止标志并等待线程终止"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

    def _run(self):
        """
        心跳器主循环，定期执行指定函数

        循环执行流程：
        1. 如果immediate为False，先等待一个interval周期
        2. 进入循环，执行用户指定的func函数
        3. 捕获并打印执行过程中的异常
        4. 等待interval秒后继续下一次执行
        """
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

        Parameters:
            func (callable): 要定期执行的函数，返回新的interval值
            interval (int): 初始执行间隔时间（秒），默认为1800秒
            first_run (bool): 是否在初始化时立即执行一次，默认True
        """
        super().__init__(func, interval, first_run)

    def _run(self):
        """
        动态心跳器主循环，支持动态调整执行间隔

        与基类不同的是，每次执行func后会获取返回值作为新的interval。
        循环执行流程：
        1. 如果immediate为False，先等待一个interval周期
        2. 进入循环，执行用户指定的func函数
        3. 将func的返回值设为新的interval
        4. 捕获并打印执行过程中的异常
        5. 等待新的interval秒后继续下一次执行
        """
        if not self.immediate:
            sleep(self.interval)

        while self.running:
            try:
                self.interval = self.func()
            except Exception:
                traceback.print_exc()

            # 等待下一个心跳周期
            sleep(self.interval)