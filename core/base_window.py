from PySide6.QtWidgets import QDialog, QMainWindow
from PySide6.QtGui import Qt, QIcon
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