"""
主窗口类，包含系统托盘和内容部件

常需修改的变量：
- content_widgets：要在主窗口显示的内容部件列表。
"""

import json
import os

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QVBoxLayout, QWidget, QScrollArea
from PySide6.QtCore import Qt, QTimer, QThread, QObject
from PySide6.QtGui import QAction

from core.base_objects import BaseWindow, WindowsManager, ThreadManager, BaseThread
from core.functions import get_today
from core.global_constants import app_name
from core.heartbeat import DynamicHeartbeat
from core.settings_manager import SettingsManager
from homepage.widgets import top_status, app_entry, NotificationSystemWidget


class MainWindow(BaseWindow):
    """主窗口类，包含系统托盘和内容部件"""

    def __init__(self):
        """初始化主窗口，包括系统托盘、自启动程序和窗口内容"""
        super().__init__()

        self.auto_start = {}

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
        """显示并激活主窗口"""
        # 如果窗口是最小化状态，先解除最小化
        if self.isMinimized():
            self.showNormal()

        # 显示窗口并激活
        self.show()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        """
        托盘图标激活事件处理

        Parameters:
            reason (QSystemTrayIcon.ActivationReason): 激活原因
        """
        # 如果是左键点击或双击托盘图标，显示窗口
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def closeEvent(self, event):
        """
        关闭窗口事件处理

        关闭窗口时不会退出程序，而是最小化到系统托盘。

        Parameters:
            event (QCloseEvent): 关闭事件
        """
        event.ignore()  # 忽略关闭事件
        self.hide()     # 隐藏窗口

    def init_content(self):
        """初始化窗口内容，创建滚动区域和内容部件布局"""
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

        self.notification_system = NotificationSystemWidget()
        self.app_entry_widget = app_entry
        self.content_widgets = [
            self.top_status_widget,
            self.notification_system,
            self.app_entry_widget
        ]
        if self.test_button:
            self.content_widgets.insert(1, self.test_button)

        # 组合部件到布局
        for widget in self.content_widgets:
            layout.addWidget(widget)
        container.setLayout(layout)

        # 设置滚动区域的内容部件
        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

    def test_function(self):
        """测试函数（预留）"""
        pass

    def init_auto_start(self):
        """
        初始化自启动模块
        """

        # scheduled_notifications - 定时通知
        from homepage import scheduled_notifications
        scheduled_notifications.start()
        self.auto_start["scheduled_notifications"] = scheduled_notifications

        # 加载设置数据
        startup_settings = SettingsManager().get_value("startup", {})

        # news_monitor - 新闻监控心跳器，定期检查新闻更新
        news_monitor_settings = startup_settings.get("news_monitor", {})
        if news_monitor_settings.get("activated", False):
            from apps import news_monitor
            interval = news_monitor_settings.get("interval", 1800)
            self.news_monitor_worker = DynamicHeartbeat(news_monitor.check_news_update, interval)
            self.news_monitor_thread = BaseThread(self.news_monitor_worker)
            self.news_monitor_thread.start()
            self.auto_start["news_monitor"] = self.news_monitor_thread

        # daily_year - 每日年度事记，导入时自动推送当天年度事记通知
        daily_year_settings = startup_settings.get("daily_year", {})
        if daily_year_settings.get("activated", False):
            from apps import daily_year
            self.auto_start["daily_year"] = daily_year

        # calendar_repeat_schedules - 日历重复事件管理器，初始化历史重复事件
        from apps.calendar import CalendarSchedulesManager
        manager = CalendarSchedulesManager()
        manager.init_repeat_events_until_today(get_today())
        top_status.update_time_display(force_update_calendar=True)
        self.auto_start["calendar_repeat_schedules"] = manager

    def quit_(self):
        """退出应用程序，关闭所有窗口"""
        # 关闭所有注册的窗口
        WindowsManager.close_all_windows()
        # 停止所有后台线程
        ThreadManager().stop_all_threads()
        # 退出应用程序
        QApplication.quit()