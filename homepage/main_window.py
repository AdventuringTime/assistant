from core.heartbeat import DynamicHeartbeat
import json
'''
主窗口类，包含系统托盘和内容部件

常需修改的变量：
- content_widgets：要在主窗口显示的内容部件列表。
'''

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QVBoxLayout, QWidget, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from core.base_window import BaseWindow, WindowsManager
from core.functions import get_today
from core.global_constants import app_name
from homepage.widgets import top_status, app_entry, notification_system

class MainWindow(BaseWindow):
    def __init__(self):
        super().__init__()

        # 设置窗口标题
        self.setWindowTitle(app_name)

        # 初始化系统托盘
        self.init_system_tray()

        # 初始化自启动程序
        self.init_auto_start()

        # 初始化窗口内容
        self.init_content()

    def init_system_tray(self):
        """初始化系统托盘"""
        # 创建系统托盘图标
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip(app_name)

        # 创建托盘菜单
        tray_menu = QMenu()

        # 更新顶部状态显示
        update_topstatus_action = QAction("更新顶部状态", self)
        update_topstatus_action.triggered.connect(lambda: self.top_status_widget.update_display())
        tray_menu.addAction(update_topstatus_action)

        tray_menu.addSeparator()

        # 退出
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.quit_)
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

    def quit_(self):
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
        scroll_area.setMinimumSize(720, 480)

        # 创建内容容器
        container = QWidget()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 内容部件
        self.top_status_widget = top_status
        self.test_button = None
        if self.test_button:
            self.test_button.clicked.connect(self.test_function)

        self.notification_system = notification_system
        self.app_entry_widget = app_entry
        self.content_widgets = [
            self.top_status_widget,
            self.app_entry_widget,
            self.notification_system
        ]
        if self.test_button:
            self.content_widgets.insert(1, self.test_button)

        # 组合部件
        for widget in self.content_widgets:
            layout.addWidget(widget)
        container.setLayout(layout)

        # 设置滚动区域的内容部件
        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

    def test_function(self):
        pass

    def init_auto_start(self):
        """初始化自启动程序"""
        self.auto_start = {}

        # news_monitor
        with open("apps/news_monitor/data/settings.json", "r") as f:
            news_monitor_settings = json.load(f)
        if news_monitor_settings["activated"]:
            from apps import news_monitor
            self.auto_start["news_monitor"] = (
                DynamicHeartbeat(news_monitor.check_news_update, news_monitor_settings["interval"])
            )

        # daily_year
        with open("apps/daily_year/data/settings.json", "r") as f:
            daily_year_settings = json.load(f)
        if daily_year_settings["activated"]:
            from apps import daily_year
            self.auto_start["daily_year"] = daily_year

        # calendar_repeat_schedules
        from apps.calendar import CalendarSchedulesManager
        manager = CalendarSchedulesManager()
        manager.init_repeat_events_until_today(get_today())
        top_status.update_time_display(force_update_calendar=True)
        self.auto_start["calendar_repeat_schedules"] = manager
