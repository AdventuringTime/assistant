from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon
from core.global_constants import icon_path

class BaseWindow(QMainWindow):
    """
    基础窗口类，提供统一的窗口样式
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置窗口图标
        self.icon = QIcon(icon_path)
        self.setWindowIcon(self.icon)
        
        # 设置窗口背景颜色
        self.setStyleSheet("QMainWindow { background-color: #1E1E1E; }")