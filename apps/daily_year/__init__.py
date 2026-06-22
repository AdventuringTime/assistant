from datetime import date
import os

from homepage.widgets import NotificationSystemWidget
from core.functions import isnt_executed_today

# 百度百科年度事记URL模板
base_url_format = "https://baike.baidu.com/item/{year}%E5%B9%B4"


def get_timedelta(today=None, target_day=None):
    """
    计算从今天到目标日期的天数差（未来为正，过去为负）

    Parameters:
        today (date, optional): 起始日期，默认为当前日期
        target_day (date, optional): 目标日期，默认为 2031-05-25

    Returns:
        int: 天数差
    """
    if today is None:
        today = date.today()
    if target_day is None:
        target_day = date(2031, 5, 25)
    return int((target_day - today).days)


# 每天第一次运行时，推送年度事记通知
if isnt_executed_today(os.path.join(os.path.dirname(__file__), "data", "last_run_date.json")):
    year = get_timedelta()
    NotificationSystemWidget().notify(
        title="每日年度事记",
        content="今天带来的是{}年哦".format(year),
        click_action={"type": "open_url", "value": base_url_format.format(year=year)}
    )