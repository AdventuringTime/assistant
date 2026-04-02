import datetime
import os

# 定义数据存储文件路径
DATA_FILE = os.path.join(os.path.dirname(__file__), 'LastRunDate.dat')

# 添加模块级别的缓存变量，用于存储当天的调用状态
_cached_date = None

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
                last_date_str = f.read().strip()
            _cached_date = datetime.datetime.strptime(last_date_str, '%Y-%m-%d').date()
        except Exception:
            # 读取文件出错，视为首次调用
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                f.write(str(today))
            _cached_date = today
            return True
                
    if _cached_date != today:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(str(today))
        _cached_date = today  # 修复：更新缓存
        return True
    else:
        return False
