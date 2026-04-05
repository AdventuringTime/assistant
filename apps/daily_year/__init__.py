from datetime import date

from core.notification import notification_system
from .utils.isFirstToday import is_first_run_today

base_url_format = "https://baike.baidu.com/item/{year}%E5%B9%B4/0"

def get_timedelta(today=None, target_day=None):
    if today is None:
        today = date.today()
    if target_day is None:
        target_day = date(2031, 5, 25)
    return int((target_day - today).days)

if is_first_run_today():
    year = get_timedelta()
    notification_system.notify(
        title="每日年度事记",
        content="今天带来的是{}年哦".format(year),
        click_action={"type": "open_url", "value": base_url_format.format(year=year)}
    )
