import datetime
from contextlib import contextmanager

def get_today(dt: datetime.datetime=None, boundary_hour: int=4) -> datetime.date:
    """
    给定一个datetime，返回一个date为今天的日期，以指定时间为界

    Parameters:
        dt (datetime.datetime, optional): 输入的时间，默认使用当前时间
        boundary_hour (int, optional): 日界小时，可超出 0-23 范围，默认4（凌晨4点）

    Returns:
        datetime.date: 表示今天的日期
    """
    if dt is None:
        dt = datetime.datetime.now()

    if 0 <= boundary_hour < 24:
        if dt.hour < boundary_hour:
            today = dt.date() - datetime.timedelta(days=1)
        else:
            today = dt.date()
    else:
        days_offset, hour = divmod(boundary_hour, 24)
        if dt.hour < hour:
            today = dt.date() - datetime.timedelta(days=days_offset + 1)
        else:
            today = dt.date() - datetime.timedelta(days=days_offset)

    return today


def get_this_week(dt: datetime.datetime=None, start_date: datetime.datetime=None) -> float:
    """
    计算当前时间对应的周数，float 类型。

    Parameters:
        dt (datetime.datetime, optional): 输入的时间，默认使用当前时间
        start_date (datetime.datetime, optional): 起始时间，默认为 datetime.datetime(2025, 9, 11, 4, 0, 0)

    Returns:
        float: 周数。例如，如果第二周已过 30%，则返回 1.3。
    """
    if dt is None:
        dt = datetime.datetime.now()

    # 默认起始时间：2025年9月11日 4:00
    if start_date is None:
        start_date = datetime.datetime(2025, 9, 11, 4, 0, 0)
    duration_of_a_week = 604800 # 一周的秒数

    collapsed = (dt - start_date).total_seconds()

    return collapsed / duration_of_a_week


@contextmanager
def block_signals(widgets):
    """
    上下文管理器：临时阻塞多个控件的信号
    
    在 `with` 块内，指定控件的信号会被阻塞，退出块后恢复。
    
    Parameters:
        widgets (list): 要阻塞信号的控件列表
    """
    for widget in widgets:
        widget.blockSignals(True)
    try:
        yield
    finally:
        for widget in widgets:
            widget.blockSignals(False)