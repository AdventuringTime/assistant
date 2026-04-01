from PySide6.QtWidgets import QLabel, QSystemTrayIcon, QMenu, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from core.base_window import BaseWindow
import os

class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题
        self.setWindowTitle("我的第一个PySide6程序")
        
        # 设置窗口大小
        self.resize(400, 300)
        
        # 初始化系统托盘
        self.init_system_tray()
    
        # 初始化窗口内容
        self.init_content()

    def init_system_tray(self):
        """初始化系统托盘"""
        # 创建系统托盘图标
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip("我的第一个PySide6程序")
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 添加退出菜单项
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)
        
        # 设置托盘菜单
        self.tray.setContextMenu(tray_menu)
        
        # 连接托盘图标点击事件
        self.tray.activated.connect(self.on_tray_activated)
        
        # 显示托盘图标
        self.tray.show()
    
    def show_window(self):
        """显示窗口"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def quit_application(self):
        """退出应用程序"""
        self.tray.hide()
        QApplication.quit()
    
    def on_tray_activated(self, reason):
        """托盘图标激活事件"""
        # 如果是左键点击或双击托盘图标，显示窗口
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()
    
    def closeEvent(self, event):
        """关闭窗口不会退出程序"""
        event.ignore()  # 忽略关闭事件
        self.hide()     # 隐藏窗口
    
    def init_content(self):
        """初始化窗口内容"""
        # 创建标签，显示文字
        label = QLabel("Hello, world!", self)
        
        # 设置标签居中显示
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 设置标签样式（可选，让文字更大更好看）
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #3498db;
            }
        """)
        
        # 将标签设置为窗口的中心部件
        self.setCentralWidget(label)