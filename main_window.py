'''
主窗口类，包含系统托盘和内容部件

常需修改的变量：
- content_widgets：要在主窗口显示的内容部件列表。
'''

from PySide6.QtWidgets import QLabel, QSystemTrayIcon, QMenu, QApplication, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

from core.base_window import BaseWindow
from core.content_widget import ContentWidget
from core.global_constants import app_name

class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题
        self.setWindowTitle(app_name)
        
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
        self.tray.setToolTip(app_name)
        
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
        container = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 内容部件
        content_widgets = [ContentWidget()]
        
        # 组合部件
        for widget in content_widgets:
            layout.addWidget(widget)
        container.setLayout(layout)
        self.setCentralWidget(container)