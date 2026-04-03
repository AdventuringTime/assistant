from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon
import os
from core.global_constants import icon_path

class BaseWindow(QMainWindow):
    """
    基础窗口类，提供统一的窗口样式
    """
    def __init__(self):
        super().__init__()
        
        # 设置窗口图标
        self.icon = QIcon(icon_path)
        self.setWindowIcon(self.icon)