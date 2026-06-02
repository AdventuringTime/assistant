from warnings import warn
from PySide6.QtCore import Signal, QEventLoop, QTimer, QThread, QTimer
from PySide6.QtGui import Qt, QIcon
from PySide6.QtWidgets import QDialog, QMainWindow, QPushButton
from core.global_constants import icon_path


class WindowsManager:
    """窗口管理器，用于统一管理所有打开的窗口"""

    _instance = None
    _windows = []

    def __new__(cls):
        """创建单例实例，确保全局只有一个窗口管理器"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_window(cls, window):
        """注册窗口到管理器"""
        if window not in cls._windows:
            cls._windows.append(window)

    @classmethod
    def unregister_window(cls, window):
        """从管理器注销窗口"""
        if window in cls._windows:
            cls._windows.remove(window)

    @classmethod
    def close_all_windows(cls):
        """关闭所有注册的窗口"""
        for window in cls._windows[:]:  # 使用副本遍历，避免修改列表时出错
            try:
                window.close()
                cls.unregister_window(window)
            except Exception:
                # 如果窗口已经销毁，忽略错误
                pass

    @classmethod
    def get_window_count(cls):
        """获取当前打开的窗口数量"""
        return len(cls._windows)


class BaseWindow(QMainWindow):
    """
    基础窗口类，提供统一的窗口样式和生命周期管理
    """
    def __init__(self, parent=None):
        """
        初始化基础窗口

        Parameters:
            parent (QWidget, optional): 父窗口，默认为None
        """
        super().__init__(parent)

        # 设置窗口图标
        self.icon = QIcon(icon_path)
        self.setWindowIcon(self.icon)

        # 设置窗口背景颜色（深色主题）
        self.setStyleSheet("QMainWindow { background-color: #1E1E1E; }")

        # 设置窗口关闭时自动销毁
        self.setAttribute(Qt.WA_DeleteOnClose)

        # 注册窗口到窗口管理器
        WindowsManager.register_window(self)

    def closeEvent(self, event):
        """
        窗口关闭事件处理

        Parameters:
            event (QCloseEvent): 关闭事件对象
        """
        # 从窗口管理器注销
        WindowsManager.unregister_window(self)
        super().closeEvent(event)

class BaseDialog(QDialog):
    """
    基础对话框类，提供统一的对话框样式和生命周期管理
    """
    def __init__(self, parent=None):
        """
        初始化基础对话框

        Parameters:
            parent (QWidget, optional): 父窗口，默认为None
        """
        super().__init__(parent)

        # 设置对话框图标
        self.icon = QIcon(icon_path)
        self.setWindowIcon(self.icon)

        # 设置对话框背景颜色（深色主题）
        self.setStyleSheet("QDialog { background-color: #2D2D30; }")

        # 设置窗口关闭时自动销毁
        self.setAttribute(Qt.WA_DeleteOnClose)

        # 注册对话框到窗口管理器
        WindowsManager.register_window(self)

    def closeEvent(self, event):
        """
        对话框关闭事件处理

        Parameters:
            event (QCloseEvent): 关闭事件对象
        """
        # 从窗口管理器注销
        WindowsManager.unregister_window(self)
        super().closeEvent(event)


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


class DeleteButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            QPushButton {
                background-color: #641A1A;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #6B2020;
            }
            QPushButton:pressed {
                background-color: #4A1515;
            }
        """)
