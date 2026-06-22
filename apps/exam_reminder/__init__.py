import bisect
import datetime
import json
import os

from core.functions import get_today
from homepage.scheduled_notifications import ScheduledTask
from homepage.widgets import NotificationSystemWidget


GRADE_MAP = ["23物理", "23声学"]
TIME_MAP = ["8:00-10:00", "10:30-12:30", "14:00-16:00", "16:30-18:30", "19:00-21:00"]


def check_and_notify():
    """
    检查是否需要发送考试提醒通知。

    如果第二天有考试安排，则发送通知。
    通知点击后会将格式化内容复制到剪贴板。
    """
    # 读取考试数据
    exams_file = os.path.join(os.path.dirname(__file__), "data", "exams.json")
    with open(exams_file, 'r', encoding='utf-8') as f:
        exams_data = json.load(f)

    # 计算明天的日期（以 18:00 为日界）
    tomorrow = get_today(boundary_hour=-6)
    tomorrow_str = tomorrow.isoformat()

    # 检查明天是否有考试
    if tomorrow_str not in exams_data:
        return

    exams_tomorrow = exams_data[tomorrow_str]

    # 通知内容
    exam_count = len(exams_tomorrow)
    notification_content = f"明天有{exam_count}门考试哦，记得跟学弟学妹们播报~"

    # 剪贴板文本：按年级整理，exam[0] 即为列表序号
    grouped = []  # grouped[grade] = [(time, subject), ...]
    for exam in exams_tomorrow:
        grade = exam[0]
        while len(grouped) <= grade:
            grouped.append([])
        bisect.insort(grouped[grade], (exam[2], exam[1]), key=lambda x: x[0])

    # 合成剪贴板文本
    lines = [f"明天（{tomorrow.month}月{tomorrow.day}日）的考试科目"]
    for grade_idx, subjects in enumerate(grouped):
        if not subjects:
            continue

        lines.append("")  # 年级间空行

        grade_name = GRADE_MAP[grade_idx]
        lines.append(f"{grade_name}：")

        for time, subject in subjects:
            time_display = TIME_MAP[time]
            lines.append(f"{time_display} {subject}")

    clipboard_content = "\n".join(lines).strip()

    # 发送通知
    notification_system = NotificationSystemWidget()
    notification_system.notify(
        title="考试提醒",
        content=notification_content,
        click_action={
            "type": "copy_to_clipboard",
            "value": clipboard_content
        }
    )


# 用于从外部启动的定时任务实例
_task = None


def start():
    """启动考试提醒定时任务（每日 18:00 检查次日考试）"""
    global _task
    _task = ScheduledTask(
        time=datetime.time(18, 0),
        callback=check_and_notify,
        key_str="exam_reminder"
    )
    _task.start()


def stop():
    """停止考试提醒定时任务"""
    global _task
    if _task:
        _task.stop()
        _task = None