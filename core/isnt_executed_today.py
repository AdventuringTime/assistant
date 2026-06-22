import datetime
import json
import os

from core.functions import get_today

# 统一数据文件路径（相对于项目根目录 data/）
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "last_run_dates.json")


class DataManager:
    """
    统一管理所有模块的运行日期记录。
    初始化时一次性读取 data/last_run_dates.json，内容格式为 {key: date_string}。
    提供内存缓存，写入时直接写回同一文件。
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._data = {}
        self._load()

    def _load(self):
        """从文件加载所有键值对"""
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            self._data = {}
            for key, val in raw.items():
                try:
                    self._data[key] = datetime.datetime.strptime(val, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    continue
        except Exception:
            self._data = {}

    def get(self, key: str) -> datetime.date | None:
        """获取指定 key 上次执行的日期"""
        return self._data.get(key)

    def set(self, key: str, date: datetime.date):
        """设置指定 key 的执行日期并立即写回文件"""
        self._data[key] = date
        self._save()

    def _save(self):
        """将内存数据写回文件"""
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        serialized = {key: str(val) for key, val in self._data.items()}
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(serialized, f, indent=4, ensure_ascii=False)


# 全局单例实例
_manager = DataManager()


def isnt_executed_at_day(key_str: str, today: datetime.date) -> bool:
    """
    判断指定 key 是否为指定日期首次调用。
    若是首次调用（无记录或日期不同），则记录并返回 True；
    否则返回 False。

    Parameters:
        key_str (str): 模块标识键，例如 "daily_year"
        today (datetime.date): 当前日期

    Returns:
        bool: 如果是该日首次调用则返回 True，否则返回 False
    """
    last_date = _manager.get(key_str)
    if last_date is None or last_date != today:
        _manager.set(key_str, today)
        return True
    return False

def mark_executed_at_day(key_str: str, today: datetime.date):
    """
    记录指定 key 已执行指定日期。

    Parameters:
        key_str (str): 模块标识键，例如 "daily_year"
        today (datetime.date): 当前日期
    """
    _manager.set(key_str, today)

def isnt_executed_today(key_str: str, dt: datetime.datetime = None, boundary_hour: int = 4) -> bool:
    """
    判断指定 key 是否为今天首次调用。
    内部使用 get_today 确定"今天"的日期（以 boundary_hour 为日界）。

    Parameters:
        key_str (str): 模块标识键，例如 "daily_year"
        dt (datetime.datetime, optional): 输入的时间，默认使用当前时间
        boundary_hour (int, optional): 日界小时（0-23），默认4（凌晨4点）

    Returns:
        bool: 如果是今天首次调用则返回 True，否则返回 False
    """
    today = get_today(dt, boundary_hour)
    return isnt_executed_at_day(key_str, today)