import json
import os
import datetime

from sortedcontainers import SortedDict

from core.functions import get_today


data_dir = "apps/calendar/data"

class CalendarSchedulesManager:
    """日程管理器（单例），负责日程的加载、保存和重复事件处理"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """确保全局只有一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化重复事件（仅首次创建时执行）"""
        if not self._initialized:
            self._cache_dict = {}     # {year: {month: {day: {id: schedule_data}}}
            self._dirty_dates = set() # {(year, month, day), ...}
            self.init_repeat_events_until_today(get_today())
            self._initialized = True

    def init_repeat_events_of_date(self, date):
        """
        初始化指定日期的重复事件

        根据前一天（每天重复）或前一周（每周重复）的日程，
        生成当天的重复事件。

        Parameters:
            date (date): 目标日期
        """
        # 处理每天重复事件
        yesterday = date - datetime.timedelta(days=1)
        events_yesterday = self.get_schedules(yesterday.year, yesterday.month, yesterday.day)
        for event in events_yesterday.values():
            if event.get("repetition") == 1:  # 每天重复
                start_time_old = datetime.datetime.strptime(event["start_time"], '%Y-%m-%d %H:%M')
                start_time_new = start_time_old + datetime.timedelta(days=1)
                event["start_time"] = start_time_new.strftime('%Y-%m-%d %H:%M')

                end_time_old = datetime.datetime.strptime(event["end_time"], '%Y-%m-%d %H:%M')
                end_time_new = end_time_old + datetime.timedelta(days=1)
                event["end_time"] = end_time_new.strftime('%Y-%m-%d %H:%M')

                id_ = int(((start_time_new.hour * 60 + start_time_new.minute) - 240) % 1440)
                self.save_schedule(
                    event,
                    date.year, date.month, date.day, id_,
                    copy=True)

        # 处理每周重复事件
        lastweek = date - datetime.timedelta(days=7)
        events_lastweek = self.get_schedules(lastweek.year, lastweek.month, lastweek.day)
        for event in events_lastweek.values():
            if event.get("repetition") == 2:  # 每周重复
                start_time_old = datetime.datetime.strptime(event["start_time"], '%Y-%m-%d %H:%M')
                start_time_new = start_time_old + datetime.timedelta(days=7)
                event["start_time"] = start_time_new.strftime('%Y-%m-%d %H:%M')

                end_time_old = datetime.datetime.strptime(event["end_time"], '%Y-%m-%d %H:%M')
                end_time_new = end_time_old + datetime.timedelta(days=7)
                event["end_time"] = end_time_new.strftime('%Y-%m-%d %H:%M')

                id_ = int(((start_time_new.hour * 60 + start_time_new.minute) - 240) % 1440)
                self.save_schedule(
                    event,
                    date.year, date.month, date.day, id_,
                    copy=True)

    def init_repeat_events_until_today(self, today):
        """
        初始化从上次更新到今天的所有重复事件

        从上次更新日期开始，遍历到今天，为每个日期生成重复事件。
        如果上次更新超过30天前，会发出警告并跳过更新。

        Parameters:
            today (date): 当前日期
        """
        # 获取上次更新的日期
        last_update_date_file = os.path.join(data_dir, "last_update_date.json")
        try:
            with open(last_update_date_file, 'r', encoding='utf-8') as f:
                last_update_date_str = json.load(f)
            last_update_date = datetime.datetime.strptime(last_update_date_str, '%Y-%m-%d').date()
        except Exception:
            last_update_date = today - datetime.timedelta(days=1)

        # 如果上次更新在今天或之后，直接返回
        if last_update_date >= today:
            return

        # 如果上次更新在30天之前，警告后返回
        if last_update_date + datetime.timedelta(days=30) < today:
            import warnings
            warnings.warn("上次更新在30天之前，暂不更新重复事件")
            return

        # 遍历日期，生成重复事件
        updating_date = last_update_date
        while updating_date < today:
            updating_date += datetime.timedelta(days=1)
            self.init_repeat_events_of_date(updating_date)

        # 保存最新的上次更新时间
        with open(last_update_date_file, 'w', encoding='utf-8') as f:
            json.dump(str(today), f, indent=4)

    def get_schedules(self, year, month, day):
        """
        从缓存或文件加载指定日期的日程数据

        优先从内存缓存读取，如果缓存中不存在则从文件加载并写入缓存。

        Parameters:
            year (int): 年份
            month (int): 月份
            day (int): 日期

        Returns:
            dict: 日程字典，key为日程ID，value为日程数据
        """
        # 优先从缓存读取
        cached = self._cache_dict.get(year, {}).get(month, {}).get(day)
        if cached is not None:
            return cached

        # 缓存未命中，从文件加载
        file_path = os.path.join(data_dir, str(year), str(month), str(day) + ".json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                schedules = json.load(f)
        else:
            schedules = {}

        # 写入缓存以便后续快速访问
        self._cache_dict.setdefault(year, {}).setdefault(month, {})[day] = schedules
        return schedules

    def save_schedule(
            self,
            schedule_data,
            year_new, month_new, day_new, id_new,
            year_old=None, month_old=None, day_old=None, id_old=None,
            copy=False
        ):
        """
        保存日程到内存。

        Parameters:
            schedule_data: 日程数据字典。
            year_new: 新日期的年份。
            month_new: 新日期的月份。
            day_new: 新日期的日期。
            id_new: 新日程的id。
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
            copy: 是否复制旧日程，默认False。
        """
        # 获取当前数据
        current_data = self.get_schedules(year_new, month_new, day_new)
        schedules = SortedDict(current_data)

        # 尝试删除旧日程
        if not copy and year_old is not None:
            if (year_old == year_new
                and month_old == month_new
                and day_old == day_new
            ):
                if id_old in schedules:
                    del schedules[id_old]
            else:
                self.delete_schedule(year_old, month_old, day_old, id_old)

        # 添加日程（处理ID冲突）
        id_new = str(id_new)
        if id_new in schedules:
            seen = 0
            while str(f"{id_new}_{str(seen).zfill(3)}") in schedules:
                seen += 1
            id_new = f"{id_new}_{str(seen).zfill(3)}"

        schedules[id_new] = schedule_data

        # 更新缓存并标记为脏数据
        self._cache_dict.setdefault(year_new, {}).setdefault(month_new, {})[day_new] = dict(schedules)
        self._dirty_dates.add((year_new, month_new, day_new))

    def delete_schedule(self, year_old, month_old, day_old, id_old):
        """
        从内存缓存中删除日程（不立即写磁盘，关闭窗口时统一写入）。

        Parameters:
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
        """
        # 参数有效性检查
        if not year_old:
            return 1

        # 从缓存获取当前数据
        schedules = self.get_schedules(year_old, month_old, day_old)
        if id_old not in schedules:
            return 1

        # 删除日程
        del schedules[id_old]

        # 更新缓存并标记为脏数据
        self._cache_dict.setdefault(year_old, {}).setdefault(month_old, {})[day_old] = schedules
        self._dirty_dates.add((year_old, month_old, day_old))

    def flush_to_disk(self):
        """
        将所有脏数据一次性写入磁盘。

        遍历所有已修改的日期，将缓存中的日程数据持久化到文件。
        如果某日日程已被清空，则删除对应的 JSON 文件。
        """
        for year, month, day in self._dirty_dates:
            schedules = self._cache_dict.get(year, {}).get(month, {}).get(day)
            file_path = os.path.join(data_dir, str(year), str(month), str(day) + ".json")

            if schedules:
                # 有日程数据 -> 写入文件
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(schedules, f, ensure_ascii=False, indent=4)
            else:
                # 日程已被清空 -> 删除文件（如果存在）
                if os.path.exists(file_path):
                    os.remove(file_path)

        self._dirty_dates.clear()

