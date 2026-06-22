import datetime
from PySide6.QtCore import QTimer

from core.functions import get_today
from core.isnt_executed_today import isnt_executed_at_day, mark_executed_at_day
from homepage.widgets import NotificationSystemWidget


class ScheduledTask:
    """
    定时任务，在指定时间执行一次回调函数。

    如果应用在指定时间正在运行，则在那个时间执行回调；
    如果应用在指定时间之后启动，则在启动时立即执行回调（每天仅一次）。

    通过 key_str 记录上次执行日期，确保每天只执行一次。
    通过 boundary_hour 指定日界，与 get_today() 语义一致。
    """

    def __init__(self, time, callback, key_str=None):
        """
        初始化定时任务

        Parameters:
            time (datetime.time): 每日触发时间
            callback (callable): 要执行的回调函数（无参数）
            key_str (str, optional): 用于记录上次执行日期的键名。
                提供此参数后，若应用在指定时间之后启动，会检查今天是否已执行，
                未执行则立即执行。不提供则仅在指定时间触发，错过则等待次日。
            boundary_hour (int, optional): 日界小时（0-23）。默认与 time.hour 一致，
                即日界与任务触发时间对齐。
        """
        self.time = time
        self.callback = callback
        self.key_str = key_str
        self._boundary_hour = time.hour
        self._running = False
        self.timer = QTimer()

    def start(self):
        """启动定时任务"""
        now = datetime.datetime.now()
        today = get_today(boundary_hour=self._boundary_hour)
        target = datetime.datetime.combine(today, self.time) + datetime.timedelta(days=1)

        if self.key_str and isnt_executed_at_day(self.key_str, today):
            # 有记录文件且当天未执行 → 立即执行
            self.callback()

        wait_ms = int((target - now).total_seconds() * 1000)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_timeout)
        self.timer.start(wait_ms)
        self._running = True

    def _on_timeout(self):
        """定时器触发时的处理"""
        self._execute()
        if self._running:
            # 安排明天的执行（24小时后）
            self.timer.start(86400000)

    def _execute(self):
        """执行回调并记录执行日期"""
        if self.key_str:
            self._mark_executed_today()
        self.callback()

    def _mark_executed_today(self):
        """记录今天已执行"""
        today = get_today(boundary_hour=self._boundary_hour)
        if self.key_str:
            mark_executed_at_day(self.key_str, today)

    def stop(self):
        """停止定时任务"""
        self._running = False
        self.timer.stop()


class ScheduledNotificationItem:
    """
    定时通知项，使用 ScheduledTask 实现每天固定时间的通知触发。
    """

    def __init__(self,
                 time,
                 key_str=None,
                 title="来自助手的通知",
                 content="助手没收到更多内容哦",
                 click_action=None,
                 icon_path='',
                 is_read=False):
        """
        初始化定时通知项。

        Parameters:
            time (datetime.time): 通知触发时间
            key_str (str, optional): 用于记录上次执行日期的键名。
                提供此参数后，若应用在指定时间之后启动，会检查今天是否已执行，
                未执行则立即执行。不提供则仅在指定时间触发，错过则等待次日。
            title (str, optional): 通知标题
            content (str, optional): 通知内容
            click_action (dict, optional): 点击操作，格式为{"type": "open_url|open_file|open_app", "value": ...}
            icon_path (str, optional): 通知图标路径
            is_read (bool, optional): 是否已读，默认 False
        """
        self.time = time
        self.key_str = key_str
        self.title = title
        self.content = content
        self.click_action = click_action
        self.icon_path = icon_path
        self.is_read = is_read
        self._task = ScheduledTask(
            time=self.time,
            callback=self._notify,
            key_str=self.key_str
        )

    def start(self):
        """开始定时通知"""
        self._task.start()

    def _notify(self):
        """发送通知"""
        notification_system = NotificationSystemWidget()
        notification_system.notify(
            title=self.title,
            content=self.content,
            click_action=self.click_action,
            icon_path=self.icon_path,
            is_read=self.is_read
        )

    def stop(self):
        """停止定时通知"""
        if self._task:
            self._task.stop()


def start():
    """启动预定义列表中的定时通知"""
    global scheduled_notifications
    scheduled_notifications = [
        ScheduledNotificationItem(
            datetime.time(22, 30),
            "FurinaNotification",
            "芙芙伴学",
            "芙芙喊你来记录今日任务完成情况啦",
            {"type": "open_app", "value": "peer_tutor_2026"}
        )
    ]

    for item in scheduled_notifications:
        item.start()

def stop():
    """停止所有定时通知"""
    for item in scheduled_notifications:
        item.stop()