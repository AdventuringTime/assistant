import datetime
import json
import os

# 模块级别的缓存字典，用于存储不同模块的调用状态
_cached_dates = {}

def get_today(dt=None):
    """
    给定一个datetime，返回一个date为今天的日期，以凌晨四点为界

    参数:
        dt: datetime对象，如果为None则使用当前时间

    返回:
        date对象，表示今天的日期
    """
    if dt is None:
        dt = datetime.datetime.now()

    # 如果当前时间在凌晨0点到4点之间，则日期算作前一天
    if dt.hour < 4:
        today = dt.date() - datetime.timedelta(days=1)
    else:
        today = dt.date()

    return today

def is_first_run_today(data_file, dt=None):
    """
    判断指定模块是否为今天首次调用
    使用内部缓存减少重复读取文件操作

    参数:
        data_file: 数据文件路径，用于存储模块的独立判定
        dt: datetime对象，供手动指定时间，默认使用当前时间

    返回:
        bool值，如果是今天首次调用则返回True，否则返回False
    """
    global _cached_dates

    today = get_today(dt)


    # # 检查缓存中是否有该模块的记录
    if data_file not in _cached_dates:
        # 若缓存无效，读取文件
        try:
            # 读取上次调用的日期
            with open(data_file, 'r', encoding='utf-8') as f:
                last_date_str = json.load(f)
            _cached_dates[data_file] = datetime.datetime.strptime(last_date_str, '%Y-%m-%d').date()
        except Exception:
            # 读取文件出错，视为首次调用
            os.makedirs(os.path.dirname(data_file), exist_ok=True)
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(str(today), f, indent=4)
            _cached_dates[data_file] = today
            return True

    if _cached_dates[data_file] != today:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(str(today), f, indent=4)
        _cached_dates[data_file] = today
        return True
    else:
        return False

def get_this_week(dt=None, start_date=None):
    """
    计算当前时间对应的周数（float）

    Parameters:
        dt (datetime.datetime, optional): 如果为None则使用当前时间。
        start_date (datetime.datetime, optional): 起始时间，默认为 datetime.datetime(2025, 9, 11, 4, 0, 0)

    Returns:
        周数。例如，如果第二周已过30%，则返回1.3。
    """
    if dt is None:
        dt = datetime.datetime.now()

    # 默认起始时间：2025年9月11日 4:00
    if start_date is None:
        start_date = datetime.datetime(2025, 9, 11, 4, 0, 0)
    duration_of_a_week = 604800 # 一周的秒数

    collapsed = (dt - start_date).total_seconds()

    return collapsed / duration_of_a_week