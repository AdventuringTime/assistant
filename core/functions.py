import datetime

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
