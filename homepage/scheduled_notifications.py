import datetime
from PySide6.QtCore import QTimer

from homepage.widgets import NotificationSystemWidget
notification_system = NotificationSystemWidget()

class ScheduledNotificationItem:
    def __init__(self,
            time,
            title="来自助手的通知",
            content="助手没收到更多内容哦",
            click_action=None,
            icon_path='',
            is_read=False):
        """
        初始化定时通知项。目前支持每天触发通知。

        Parameters:
            time (datetime.time): 通知触发时间
            title (str, optional): 通知标题
            content (str, optional): 通知内容
            click_action (dict, optional): 点击操作，格式为{"type": "open_url|open_file|open_app", "value": ...}
            icon_path (str, optional): 通知图标路径
            is_read (bool, optional): 是否已读，默认 False
        """
        self.time = time
        self.title = title
        self.content = content
        self.click_action = click_action
        self.icon_path = icon_path
        self.is_read = is_read
        self.timer = QTimer()

    def start(self):
        """开始定时任务调度循环"""
        self._running = True
        now = datetime.datetime.now()
        target_time = datetime.datetime.combine(now.date(), self.time)

        if now >= target_time:
            target_time = target_time + datetime.timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.timer.start(int(wait_seconds*1000))

    def on_timer_timeout(self):
        self.notify()
        if self._running:
            self.timer.start(86400000)

    def notify(self):
        """发送通知"""
        notification_system.notify(
            title=self.title,
            content=self.content,
            click_action=self.click_action,
            icon_path=self.icon_path,
            is_read=self.is_read
        )

    def stop(self):
        """停止定时任务"""
        self._running = False
        self.timer.stop()


def start():
    """启动预定义列表中的定时通知"""
    global scheduled_notifications
    scheduled_notifications = [
        ScheduledNotificationItem(
            datetime.time(22, 30),
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