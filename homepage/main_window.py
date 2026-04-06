import json
from core.heartbeat import Heartbeat
'''
主窗口类，包含系统托盘和内容部件

常需修改的变量：
- content_widgets：要在主窗口显示的内容部件列表。
'''

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from core.base_window import BaseWindow, WindowsManager
from core.global_constants import app_name
from core.widgets import TopStatusWidget, AppEntryWidget, notification_system

class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题
        self.setWindowTitle(app_name)
        
        # 初始化系统托盘
        self.init_system_tray()
    
        # 初始化窗口内容
        self.init_content()

        # 初始化自启动程序
        self.init_auto_start()

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
        # 如果窗口是最小化状态，先解除最小化
        if self.isMinimized():
            self.showNormal()
        
        # 显示窗口并激活
        self.show()
        self.activateWindow()
        self.raise_()
    
    def on_tray_activated(self, reason):
        """托盘图标激活事件"""
        # 如果是左键点击或双击托盘图标，显示窗口
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()
    
    def closeEvent(self, event):
        """关闭窗口不会退出程序"""
        event.ignore()  # 忽略关闭事件
        self.hide()     # 隐藏窗口
    
    def quit_application(self):
        """退出应用程序，关闭所有窗口"""
        # 关闭所有注册的窗口
        WindowsManager.close_all_windows()
        # 退出应用程序
        QApplication.quit()
    
    def init_content(self):
        """初始化窗口内容"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setMinimumSize(720, 480)
        
        # 创建内容容器
        container = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 内容部件
        self.top_status_widget = TopStatusWidget()
        self.notification_system = notification_system  # NotificationSystemWidget
        self.app_entry_widget = AppEntryWidget()
        self.content_widgets = [
            self.top_status_widget,
            self.app_entry_widget,
            self.notification_system
        ]
        
        # 组合部件
        for widget in self.content_widgets:
            layout.addWidget(widget)
        container.setLayout(layout)
        
        # 设置滚动区域的内容部件
        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

    def init_auto_start(self):
        """初始化自启动程序"""
        self.auto_start = []
        with open("apps/news_monitor/data/settings.json", "r") as f:
            news_monitor_settings = json.load(f)
        if news_monitor_settings["activated"]:
            from apps import news_monitor
            self.auto_start.append((news_monitor,
                Heartbeat(news_monitor.check_news_update, news_monitor_settings["interval"])))

        with open("apps/daily_year/data/settings.json", "r") as f:
            daily_year_settings = json.load(f)
        if daily_year_settings["activated"]:
            from apps import daily_year
            self.auto_start.append((daily_year,))