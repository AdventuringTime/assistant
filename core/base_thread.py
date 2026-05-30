from PySide6.QtCore import Signal, QEventLoop, QTimer, QThread, QTimer
from warnings import warn


class ThreadManager:
    """线程管理器，负责管理所有后台线程的生命周期"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._threads = []
        return cls._instance

    def register_thread(self, thread):
        """
        注册一个线程到管理器

        Parameters:
            thread (QThread): QThread 对象
        """
        if thread not in self._threads:
            self._threads.append(thread)

    def unregister_thread(self, thread):
        """
        注销一个线程

        Parameters:
            thread (QThread): QThread 对象
        """
        if thread in self._threads:
            self._threads.remove(thread)

    def stop_all_threads(self):
        """
        停止所有注册的线程
        """
        for thread in self._threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()


class BaseThread(QThread):
    """
    基础线程类，继承自QThread，自动注册到ThreadManager

    使用方式：
        thread = BaseThread(worker)
        thread.start()

    线程会在启动时自动注册到ThreadManager，在应用退出时自动停止
    """
    _worker_stopping = Signal()

    def __init__(self, worker=None, parent=None):
        """
        初始化基础线程

        Parameters:
            worker (QObject, optional):
                要移动到线程的worker对象。
                - 支持start方法：线程会在启动时自动调用start方法，无需connect启动事件。
                - 支持stop方法：线程会在退出时自动调用stop方法，使工作对象安全退出。
                - stop方法结束应使用`try-finally`语句发射stopped信号：  
                `try: <your code> finally: self.stopped.emit()`。

            parent (QObject, optional): 父对象
        """
        super().__init__(parent)
        self.worker = worker

        # 自动注册到线程管理器
        ThreadManager().register_thread(self)

        # 如果有worker，将其移动到线程中
        if worker:
            worker.moveToThread(self)
            # 连接started信号到worker的start方法
            if hasattr(worker, 'start') and callable(worker.start):
                self.started.connect(worker.start)
            if hasattr(worker, 'stop') and callable(worker.stop):
                self._worker_stopping.connect(worker.stop)

    def quit(self):
        """
        退出线程，在调用父类quit前先停止worker
        """
        if self.worker and hasattr(self.worker, 'stop') and callable(self.worker.stop):
            loop = QEventLoop()
            # 连接worker停止完成的信号
            if hasattr(self.worker, 'stopped') and isinstance(self.worker.stopped, Signal):
                self.worker.stopped.connect(loop.quit)
            else:
                # 如果没有stopped信号，使用QTimer超时机制
                warn("Worker 没有 stopped 信号，我随便等等吧")
                QTimer.singleShot(1000, loop.quit)  # 1秒超时

            # 发送停止信号
            self._worker_stopping.emit()

            # 等待worker停止完成
            loop.exec_()

        super().quit()