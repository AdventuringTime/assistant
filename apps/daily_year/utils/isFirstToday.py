import datetime
import json
from core.functions import get_today


import os
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "last_run_date.json")

# 添加模块级别的缓存变量，用于存储当天的调用状态
_cached_date = None

def is_first_run_today(dt=None):
    """
    判断该函数是否为今天首次调用
    使用内部缓存减少重复读取文件操作

    参数:
        dt: datetime对象，供手动指定时间，默认使用当前时间
    
    返回:
        bool值，如果是今天首次调用则返回True，否则返回False
    """
    global _cached_date
    
    today = get_today(dt)
    
    if _cached_date is None:
        # 若缓存无效，读取文件
        try:
            # 读取上次调用的日期
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                last_date_str = json.load(f)
            _cached_date = datetime.datetime.strptime(last_date_str, '%Y-%m-%d').date()
        except Exception:
            # 读取文件出错，视为首次调用
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(str(today), f, indent=4)
            _cached_date = today
            return True
                
    if _cached_date != today:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(str(today), f, indent=4)
        _cached_date = today  # 修复：更新缓存
        return True
    else:
        return False