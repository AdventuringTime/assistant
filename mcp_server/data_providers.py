"""MCP 服务器数据访问层，通过各应用的数据管理器读写数据，不直接操作文件"""

import datetime
import json
import os

from core.functions import get_today

from apps.calendar.calendar_schedule_manager import CalendarSchedulesManager
from apps.dew_point import calc_dew_point as _calc_dew_point
from apps.expenses import ExpenseDataManager
from apps.graduate_worktime import GraduateWorktimeDataManager
from apps.peer_tutor_2026 import TaskDataManager as PeerTutorTaskDataManager
from apps.search_words import SearchWordsDataManager
from apps.tasks import TaskDataManager as TasksDataManager


# 当前操作的记账月份 (year, month)，None 表示默认今天所在月
_current_expense_month = None


def get_today_schedules() -> dict:
    """读取今天的所有日程信息"""
    today = get_today()
    schedules = CalendarSchedulesManager().get_schedules(today.year, today.month, today.day)
    return schedules


def get_date_schedules(year: int, month: int, day: int) -> dict:
    """
    读取指定日期的所有日程信息

    Parameters:
        year (int): 年份
        month (int): 月份（1-12）
        day (int): 日期

    Returns:
        dict: 以日程ID为键的日程数据，该日期无日程时返回空字典
    """
    return CalendarSchedulesManager().get_schedules(year, month, day)


def get_tasks(is_completed: bool = False) -> dict:
    """
    读取所有未完成或已完成任务信息

    Parameters:
        is_completed (bool): 是否读取已完成任务，False 读取未完成任务（默认）

    Returns:
        dict: 以任务名为键的任务数据
    """
    manager = TasksDataManager()
    names = manager.completed_names if is_completed else manager.todo_names
    return {name: manager.tasks[name] for name in names}


def get_graduate_worktime() -> str:
    """读取当前所有研招工时信息（含总时长统计）"""
    return GraduateWorktimeDataManager().get_export_text()


def get_search_words() -> list[str]:
    """读取当前所有待搜索词信息"""
    return list(SearchWordsDataManager().words)


def _annotate_expense_children(children: list, manager: ExpenseDataManager, constants: dict,
                               prefix: list = ()) -> list:
    """
    递归为记账数据附加预估/实际汇总、预算公式与 idx 路径，不修改原始数据

    Parameters:
        children (list): 记账子项列表
        manager (ExpenseDataManager): 数据管理器，用于调用汇总逻辑
        constants (dict): 常量字典，用于评估预估金额表达式
        prefix (list): 当前层级的父级索引路径

    Returns:
        list: 新列表，每个节点新增 idx 字段，每个 type 节点新增 estimated 与 actual 字段
    """
    result = []
    for i, child in enumerate(children):
        idx = list(prefix) + [i]
        annotated = {'idx': idx}
        for key, value in child.items():
            if key == 'children':
                annotated['children'] = _annotate_expense_children(value, manager, constants, idx)
            else:
                annotated[key] = value
        if child.get('type') == 'type':
            estimated, actual = manager.sum_expenses(child.get('children', []), constants)
            annotated['estimated'] = estimated
            annotated['actual'] = actual
        result.append(annotated)
    return result


def _resolve_parent_list(children: list, idx_path) -> list:
    """
    按索引路径定位记账数据中的父列表

    Parameters:
        children (list): 根级子项列表
        idx_path (list[int] | None): 根到目标的索引路径，None 或空表示根级列表

    Returns:
        list: 目标节点所在的列表

    Raises:
        IndexError: 索引路径超出范围
        ValueError: 路径中的节点不是记账类型（没有子项）
    """
    if not idx_path:
        return children
    node_list = children
    node = None
    for i in idx_path:
        if not 0 <= i < len(node_list):
            raise IndexError(f"记账索引 {idx_path} 超出范围")
        node = node_list[i]
        node_list = node.get('children', [])
    if node.get('type') != 'type':
        raise ValueError(f"记账索引 {idx_path} 指向的不是记账类型，无法继续定位")
    return node.get('children', [])


def _resolve_expense(children: list, idx_path):
    """
    按索引路径定位记账数据中的节点

    Parameters:
        children (list): 根级子项列表
        idx_path (list[int]): 根到目标的索引路径

    Returns:
        dict: 目标节点数据

    Raises:
        IndexError: 索引路径超出范围
    """
    if not idx_path:
        raise IndexError("记账索引不能为空")
    node_list = children
    node = None
    for i in idx_path:
        if not 0 <= i < len(node_list):
            raise IndexError(f"记账索引 {idx_path} 超出范围")
        node = node_list[i]
        node_list = node.get('children', [])
    return node


def _get_current_expense_month() -> tuple:
    """获取当前操作的记账月份（年, 月），未显式切换时使用今天所在月"""
    if _current_expense_month is None:
        today = get_today()
        return today.year, today.month
    return _current_expense_month


def get_month_expenses() -> dict:
    """读取当前操作月份的所有记账信息，每一项附带自身 idx 与预算公式，并附上总额汇总"""
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    constants = data.get('constants', {})
    children = data.get('children', [])
    estimated, actual = manager.sum_expenses(children, constants)
    return {
        "year": year,
        "month": month,
        "constants": constants,
        "children": _annotate_expense_children(children, manager, constants),
        "summary": {"estimated": estimated, "actual": actual},
    }


def get_peer_tutor_week_tasks() -> dict:
    """读取当前周芙芙伴学所有任务信息，当前周数据不存在时自动从上周继承"""
    manager = PeerTutorTaskDataManager()
    week = manager.get_current_week_num()
    manager.inherit_tasks_from_last_week_if_not_exist(week)
    tasks = manager.get_tasks(week)
    return {"week": week, "tasks": tasks}


def get_peer_tutor_window_screenshot():
    """截取芙芙伴学主窗口并返回窗口图片给 AI。

    Returns:
        Image: PNG 格式的窗口截图
    """
    from mcp.server.mcpserver.utilities.types import Image
    from apps.peer_tutor_2026 import get_window_screenshot_bytes

    return Image(data=get_window_screenshot_bytes(), format="png")


def update_peer_tutor_task_progress(index: int, completed: float) -> dict:
    """
    修改当前周芙芙伴学特定任务的完成进度

    Parameters:
        index (int): 任务序号（从0开始）
        completed (float): 新的完成数量

    Returns:
        dict: 修改后的任务数据

    Raises:
        IndexError: 任务序号超出范围
    """
    manager = PeerTutorTaskDataManager()
    week = manager.get_current_week_num()
    manager.inherit_tasks_from_last_week_if_not_exist(week)
    tasks = manager.get_tasks(week)
    if not 0 <= index < len(tasks):
        raise IndexError(f"任务序号 {index} 超出范围（共 {len(tasks)} 个任务）")
    tasks[index]['completed'] = completed
    manager.mark_modified(week)
    manager.save_tasks()
    return tasks[index]


def update_peer_tutor_task(
    index: int = None,
    name: str = None,
    required: float = None,
    weight: int = None,
) -> dict | str:
    """
    添加、修改或删除当前周芙芙伴学任务数据

    规则：
    - index 未指定：添加新任务（必须提供非空 name，completed 固定为 0.0，required 默认 1.0，weight 默认 100）
    - index 指定且至少提供一项数据字段：修改该任务对应的字段（未提供的字段保持不变）
    - index 指定但未提供任何数据字段：删除该任务

    Parameters:
        index (int, optional): 任务序号（从0开始），未指定表示添加
        name (str, optional): 任务名称
        required (float, optional): 所需次数
        weight (int, optional): 权重

    Returns:
        dict: 添加/修改时返回操作结果，包含周数、任务序号与任务数据
        str: 删除时返回“已删除”

    Raises:
        ValueError: 添加时未提供任务名称
        IndexError: 任务序号超出范围
    """
    manager = PeerTutorTaskDataManager()
    week = manager.get_current_week_num()
    manager.inherit_tasks_from_last_week_if_not_exist(week)
    tasks = manager.get_tasks(week)

    if index is None:
        # 未指定 index，添加新任务
        if not name or not str(name).strip():
            raise ValueError("添加任务时必须提供非空的任务名称 name")
        task = {
            'name': str(name).strip(),
            'completed': 0.0,
            'required': required if required is not None else 1.0,
            'weight': weight if weight is not None else 100,
        }
        tasks.append(task)
        manager.mark_modified(week)
        manager.save_tasks()
        return {"week": week, "index": len(tasks) - 1, "task": task}

    if not 0 <= index < len(tasks):
        raise IndexError(f"任务序号 {index} 超出范围（共 {len(tasks)} 个任务）")
    task = tasks[index]

    fields = {k: v for k, v in (
        ('name', name),
        ('required', required),
        ('weight', weight),
    ) if v is not None}
    if not fields:
        # 指定 index 但未提供任何数据字段，删除该任务
        tasks.pop(index)
        manager.mark_modified(week)
        manager.save_tasks()
        return "已删除任务：" + task['name']

    task.update(fields)
    manager.mark_modified(week)
    manager.save_tasks()
    return {"week": week, "index": index, "task": task}


# ============================ 日程 ============================


def _parse_schedule_time(value):
    """
    解析日程时间字符串

    Parameters:
        value (str): "YYYY-MM-DD HH:MM" 格式的时间字符串

    Returns:
        datetime.datetime: 解析后的时间

    Raises:
        ValueError: 时间格式不正确
    """
    try:
        return datetime.datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        raise ValueError(f"时间格式应为 'YYYY-MM-DD HH:MM'，收到：{value}")


def add_schedule(begin: str, end: str, title: str = "新日程", type: int = 0,
                 place: str = None, repeat: int = 0, description: str = None) -> dict:
    """
    添加一条日程

    Parameters:
        begin (str): 开始时间，格式 "YYYY-MM-DD HH:MM"
        end (str): 结束时间，格式 "YYYY-MM-DD HH:MM"
        title (str, optional): 日程标题，默认“新日程”
        type (int, optional): 日程类型（0 其他 / 1 会议 / 2 娱乐 / 3 活动 / 4 课程），默认 0
        place (str, optional): 地点
        repeat (int, optional): 重复方式（0 无 / 1 每天 / 2 每周），默认 0
        description (str, optional): 描述

    Returns:
        dict: 新增日程的结果，包含日期、ID 与日程数据

    Raises:
        ValueError: 时间格式不正确
    """
    start_time = _parse_schedule_time(begin)
    end_time = _parse_schedule_time(end)

    schedule_data = {
        "title": (str(title).strip() or "新日程") if title else "新日程",
        "type": int(type) if type is not None else 0,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "location": (str(place).strip() or None) if place else None,
        "repetition": int(repeat) if repeat is not None else 0,
        "description": (str(description).strip() or None) if description else None,
    }
    manager = CalendarSchedulesManager()
    year, month, day, id_new = manager.save_schedule(schedule_data)
    manager.flush_to_disk()
    return schedule_data


def edit_schedule(year: int, month: int, day: int, id: str,
                  copy: bool = False, delete: bool = False,
                  title: str = None, type: int = None, begin: str = None, end: str = None,
                  place: str = None, repeat: int = None, description: str = None) -> dict | str:
    """
    编辑、复制或删除指定日期的一条日程

    规则：
    - delete 为 True：删除该日程（此时忽略其余数据字段）
    - copy 为 True：以修改后的数据生成一条副本（保留原日程，ID 冲突时自动加后缀）
    - 其余情况：修改原日程，仅覆盖提供了的字段（begin 改变时会同时移动日程所属日期）

    Parameters:
        year (int): 目标日程所在年份
        month (int): 目标日程所在月份（1-12）
        day (int): 目标日程所在日期
        id (str): 目标日程ID（读取日程时返回的键，如 "360"，副本可能带后缀）
        copy (bool, optional): 是否保存为副本，默认 False
        delete (bool, optional): 是否删除，默认 False
        title (str, optional): 新的标题
        type (int, optional): 新的类型（0 其他 / 1 会议 / 2 娱乐 / 3 活动 / 4 课程）
        begin (str, optional): 新的开始时间，格式 "YYYY-MM-DD HH:MM"
        end (str, optional): 新的结束时间，格式 "YYYY-MM-DD HH:MM"
        place (str, optional): 新的地点
        repeat (int, optional): 新的重复方式（0 无 / 1 每天 / 2 每周）
        description (str, optional): 新的描述

    Returns:
        dict: 编辑/复制的结果，包含日期、ID 与日程数据
        str: 删除时返回“已删除”

    Raises:
        IndexError: 指定日期或ID的日程不存在
        ValueError: 时间格式不正确
    """
    manager = CalendarSchedulesManager()
    schedules = manager.get_schedules(year, month, day)
    if id not in schedules:
        raise IndexError(f"{year}-{month}-{day} 下不存在 ID 为 {id} 的日程")

    if delete:
        title_deleted = schedules[id].get('title')
        manager.delete_schedule(year, month, day, id)
        manager.flush_to_disk()
        return f"已删除日程：{title_deleted}"

    schedule_data = dict(schedules[id])

    if begin is not None:
        begin_time = _parse_schedule_time(begin)
        schedule_data["start_time"] = begin_time.strftime("%Y-%m-%d %H:%M")
    if end is not None:
        end_time = _parse_schedule_time(end)
        schedule_data["end_time"] = end_time.strftime("%Y-%m-%d %H:%M")
    if title is not None:
        schedule_data["title"] = str(title).strip() or "新日程"
    if type is not None:
        schedule_data["type"] = int(type)
    if place is not None:
        schedule_data["location"] = str(place).strip() or None
    if repeat is not None:
        schedule_data["repetition"] = int(repeat)
    if description is not None:
        schedule_data["description"] = str(description).strip() or None

    year_new, month_new, day_new, id_new = manager.save_schedule(
        schedule_data,
        year, month, day, id,
        copy=copy,
    )
    manager.flush_to_disk()
    return schedule_data


# ============================ 任务 ============================


def _validate_task(task: dict):
    """
    校验任务数据的合法性

    Parameters:
        task (dict): 任务数据

    Raises:
        ValueError: 任务类型非法
    """
    if task.get('type', 0) not in (0, 1):
        raise ValueError("任务类型 type 只能是 0（支线）或 1（主线）")


def add_task(name: str, type: int = None, subtasks: str = None, required: float = None,
             deadline: str = None, estimated_complete: str = None, link: str = None) -> dict:
    """
    添加一个任务

    任务名为空时使用“未命名任务”，与现有任务重名时会自动追加 -1、-2 等后缀

    Parameters:
        name (str): 任务名称
        type (int, optional): 任务类型（0 支线 / 1 主线），默认 0
        subtasks (str, optional): 子任务内容（每行一个）
        required (float, optional): 所需完成次数，默认 1.0
        deadline (str, optional): 截止日期，格式 "YYYY-MM-DD"
        estimated_complete (str, optional): 预计完成日期，格式 "YYYY-MM-DD"
        link (str, optional): 关联链接

    Returns:
        dict: 新增任务的结果，包含任务名与任务数据

    Raises:
        ValueError: 任务类型非法
    """
    manager = TasksDataManager()
    task_data = {
        'type': 0,
        'completed': 0.0,
        'required': 1.0,
    }
    task_data.update({k: v for k, v in {
        'type': type,
        'subtasks': subtasks,
        'required': required,
        'deadline': deadline,
        'estimated_time': estimated_complete,
        'link': link,
    }.items() if v is not None})
    _validate_task(task_data)

    new_name = manager.add_task(name, task_data)
    manager.save_tasks()
    return {"name": new_name, "task": task_data}


def switch_tracking(name: str) -> dict:
    """
    切换指定任务的追踪状态（正在追踪则停止，否则开始追踪）

    Parameters:
        name (str): 任务名

    Returns:
        dict: 切换后的追踪任务名（未追踪任何任务时为 None）

    Raises:
        KeyError: 任务不存在
    """
    manager = TasksDataManager()
    if name not in manager.tasks:
        raise KeyError(f"任务不存在：{name}")
    manager.tracking_task_name = None if manager.tracking_task_name == name else name
    manager.save_tasks()
    return {"tracking_task_name": manager.tracking_task_name}


def edit_task(name: str, copy: bool = False, delete: bool = False, new_name: str = None,
              type: int = None, subtasks: str = None, required: float = None,
              deadline: str = None, estimated_complete: str = None, link: str = None) -> dict | str:
    """
    编辑、复制或删除指定任务

    规则：
    - delete 为 True：删除该任务（此时忽略其余数据字段）
    - copy 为 True：以修改后的数据生成一条副本（保留原任务，副本插入原任务之后）
    - 其余情况：修改原任务，仅覆盖提供了的字段

    Parameters:
        name (str): 目标任务名
        copy (bool, optional): 是否保存为副本，默认 False
        delete (bool, optional): 是否删除，默认 False
        new_name (str, optional): 新的任务名
        type (int, optional): 新的任务类型（0 支线 / 1 主线）
        subtasks (str, optional): 新的子任务内容（每行一个）
        required (float, optional): 新的所需完成次数
        deadline (str, optional): 新的截止日期，格式 "YYYY-MM-DD"
        estimated_complete (str, optional): 新的预计完成日期，格式 "YYYY-MM-DD"
        link (str, optional): 新的关联链接

    Returns:
        dict: 编辑/复制的结果，包含任务名与任务数据
        str: 删除时返回“已删除”

    Raises:
        KeyError: 任务不存在
        ValueError: 任务类型非法
    """
    manager = TasksDataManager()
    if name not in manager.tasks:
        raise KeyError(f"任务不存在：{name}")

    if delete:
        manager.remove_task(name)
        manager.save_tasks()
        return f"已删除任务：{name}"

    fields = {k: v for k, v in {
        'type': type,
        'subtasks': subtasks,
        'required': required,
        'deadline': deadline,
        'estimated_time': estimated_complete,
        'link': link,
    }.items() if v is not None}

    task = dict(manager.tasks[name])
    task.update(fields)
    _validate_task(task)

    if copy:
        new_name = manager.copy_task(name, new_name, task)
    else:
        desired_name = new_name if new_name is not None else name
        new_name = manager.replace_task(name, desired_name, task)

    manager.save_tasks()
    return {"name": new_name, "task": task}


def go_to_tracking_task() -> str:
    """
    打开追踪中任务关联的链接（前往追踪中任务）

    要求存在追踪中的任务且该任务有链接，否则报错；等价于界面上追踪任务“前往”按钮可用时点击该按钮

    Returns:
        str: 已打开链接的说明

    Raises:
        KeyError: 没有追踪中的任务或该任务不存在
        ValueError: 追踪中任务没有可前往的链接
    """
    manager = TasksDataManager()
    name = manager.tracking_task_name
    if not name or name not in manager.tasks:
        raise KeyError("当前没有追踪中的任务")
    link = manager.tasks[name].get('link')
    if not link:
        raise ValueError(f"追踪中任务“{name}”没有可前往的链接")

    manager.open_link(link)
    return f"已打开追踪中任务“{name}”的链接：{link}"


def complete_tracking_task() -> str:
    """
    完成追踪中的任务（仅当任务列表界面的“完成”按钮可用时可用）

    行为与界面点击“完成”按钮一致：
    - 任务名追加 -已完成 后缀后移入已完成列表
    - 子任务多于一行时，移除第一行并重置进度；否则直接删除该任务

    Returns:
        str: 原任务已标记一次完成的说明

    Raises:
        KeyError: 没有追踪中的任务或该任务不存在
        ValueError: 任务未完成（进度未达到所需次数）
    """
    manager = TasksDataManager()
    name = manager.tracking_task_name
    if not name or name not in manager.tasks:
        raise KeyError("当前没有追踪中的任务")
    task = manager.tasks[name]
    completed = task.get('completed', 0.0)
    required = task.get('required', 1.0)
    if not (required <= 0 or completed >= required):
        raise ValueError(f"任务“{name}”尚未完成（{completed}/{required}），不能标记为完成")

    manager.complete_task(name)
    manager.save_tasks()
    return f"{name}已标记一次完成"


def change_task_order(name: str, new_idx: int) -> list:
    """
    更改指定任务在未完成任务列表中的顺序（0-based）

    Parameters:
        name (str): 任务名
        new_idx (int): 新的位置（从0开始）

    Returns:
        list: 调整后的未完成任务名列表

    Raises:
        KeyError: 任务不在未完成任务列表中
        IndexError: 新位置超出范围
    """
    manager = TasksDataManager()
    if name not in manager.todo_names:
        raise KeyError(f"未完成任务列表中不存在：{name}")
    if not 0 <= new_idx < len(manager.todo_names):
        raise IndexError(f"新的位置 {new_idx} 超出范围（共 {len(manager.todo_names)} 个任务）")
    manager.todo_names.remove(name)
    manager.todo_names.insert(new_idx, name)
    manager.save_tasks()
    return list(manager.todo_names)


# ============================ 工时（研招） ============================


def add_worktime_row(content: str = "") -> dict:
    """
    在研招工时末尾添加一行（日期默认今天，时长默认 1.5 小时）

    Parameters:
        content (str, optional): 工作内容

    Returns:
        dict: 新增行的结果，包含行号与记录数据
    """
    manager = GraduateWorktimeDataManager()
    record = {
        "date": get_today().strftime("%Y-%m-%d"),
        "content": "" if content is None else content,
        "duration": "1.5",
    }
    manager.records.append(record)
    manager.save_records()
    return {"idx": len(manager.records) - 1, "record": record}


def edit_worktime_row(idx: int, date: str = None, content: str = None, duration: str = None) -> dict:
    """
    编辑研招工时的某一行，仅覆盖提供了的字段

    Parameters:
        idx (int): 行号（从0开始）
        date (str, optional): 新的日期，格式 "YYYY-MM-DD"
        content (str, optional): 新的工作内容
        duration (str, optional): 新的时长（小时）

    Returns:
        dict: 编辑后的记录数据

    Raises:
        IndexError: 行号超出范围
        ValueError: 日期格式不正确
    """
    manager = GraduateWorktimeDataManager()
    if not 0 <= idx < len(manager.records):
        raise IndexError(f"行号 {idx} 超出范围（共 {len(manager.records)} 行）")
    record = manager.records[idx]
    if date is not None:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"日期格式不正确：{date}")
        record["date"] = date
    if content is not None:
        record["content"] = content
    if duration is not None:
        record["duration"] = duration
    manager.save_records()
    return record


def delete_worktime_row(idx: int) -> str:
    """
    删除研招工时的某一行

    Parameters:
        idx (int): 行号（从0开始）

    Returns:
        str: 删除结果说明

    Raises:
        IndexError: 行号超出范围
    """
    manager = GraduateWorktimeDataManager()
    if not 0 <= idx < len(manager.records):
        raise IndexError(f"行号 {idx} 超出范围（共 {len(manager.records)} 行）")
    record = manager.records.pop(idx)
    manager.save_records()
    return f"已删除记录：{record}"


def clear_worktime() -> str:
    """
    清空所有研招工时记录

    Returns:
        str: 清空结果说明
    """
    manager = GraduateWorktimeDataManager()
    count = len(manager.records)
    manager.records = []
    manager.save_records()
    return f"已清空 {count} 条工时记录"


# ============================ 搜索词 ============================


def add_search_word(content: str) -> dict:
    """
    在搜索词列表末尾添加一个搜索词

    Parameters:
        content (str): 搜索词内容

    Returns:
        dict: 新增结果，包含序号与内容
    """
    manager = SearchWordsDataManager()
    manager.words.append("" if content is None else str(content))
    manager.save_words()
    return {"idx": len(manager.words) - 1, "content": manager.words[-1]}


def rename_search_word(idx: int, content: str) -> dict:
    """
    重命名指定搜索词

    Parameters:
        idx (int): 搜索词序号（从0开始）
        content (str): 新的搜索词内容

    Returns:
        dict: 重命名结果，包含序号与内容

    Raises:
        IndexError: 序号超出范围
    """
    manager = SearchWordsDataManager()
    if not 0 <= idx < len(manager.words):
        raise IndexError(f"搜索词序号 {idx} 超出范围（共 {len(manager.words)} 个）")
    manager.words[idx] = "" if content is None else str(content)
    manager.save_words()
    return {"idx": idx, "content": manager.words[idx]}


def delete_search_word(idx: int) -> str:
    """
    删除指定搜索词

    Parameters:
        idx (int): 搜索词序号（从0开始）

    Returns:
        str: 删除结果说明

    Raises:
        IndexError: 序号超出范围
    """
    manager = SearchWordsDataManager()
    if not 0 <= idx < len(manager.words):
        raise IndexError(f"搜索词序号 {idx} 超出范围（共 {len(manager.words)} 个）")
    removed = manager.words.pop(idx)
    manager.save_words()
    return f"已删除搜索词：{removed}"


# ============================ 记账 ============================


def switch_expense_month(year: int, month: int) -> dict:
    """
    切换记账操作的目标月份（影响其余记账工具与读取近12个月余额）

    Parameters:
        year (int): 年份
        month (int): 月份（1-12）

    Returns:
        dict: 切换后的目标年月
    """
    global _current_expense_month
    if not 1 <= int(month) <= 12:
        raise ValueError(f"月份必须在 1-12 之间，收到：{month}")
    _current_expense_month = (int(year), int(month))
    return {"year": _current_expense_month[0], "month": _current_expense_month[1]}


def add_expense_item(name: str, idx: list = None) -> dict:
    """
    在指定位置添加一个记账项

    Parameters:
        name (str): 记账项名称
        idx (list, optional): 父节点的索引路径（如 [0,2] 表示 根.children[0].children[2]），省略表示根级

    Returns:
        dict: 新增记账项的索引路径与数据

    Raises:
        IndexError: 索引路径超出范围
        ValueError: 父节点不是记账类型，或名称为空
    """
    if not name or not str(name).strip():
        raise ValueError("添加记账项必须提供非空名称 name")
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    children = data.setdefault('children', [])
    parent = _resolve_parent_list(children, idx)
    item = {
        'type': 'item',
        'name': str(name).strip(),
        'estimated_amount': "0",
        'actual_amount': 0,
    }
    parent.append(item)
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return {"idx": list(idx or []) + [len(parent) - 1], "item": item}


def add_expense_type(name: str, idx: list = None) -> dict:
    """
    在指定位置添加一个记账类型

    Parameters:
        name (str): 记账类型名称
        idx (list, optional): 父节点的索引路径（如 [0,2] 表示 根.children[0].children[2]），省略表示根级

    Returns:
        dict: 新增记账类型的索引路径与数据

    Raises:
        IndexError: 索引路径超出范围
        ValueError: 父节点不是记账类型，或名称为空
    """
    if not name or not str(name).strip():
        raise ValueError("添加记账类型必须提供非空名称 name")
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    children = data.setdefault('children', [])
    parent = _resolve_parent_list(children, idx)
    node = {
        'type': 'type',
        'name': str(name).strip(),
        'children': [],
    }
    parent.append(node)
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return {"idx": list(idx or []) + [len(parent) - 1], "node": node}


def edit_expense_constant(name: str, value: int = None) -> dict | str:
    """
    修改或删除记账常量

    Parameters:
        name (str): 常量名称
        value (int, optional): 新的常量值；省略（None）时删除该常量

    Returns:
        dict: 修改时的结果，包含常量名与值
        str: 删除时的结果说明
    """
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    constants = data.setdefault('constants', {})
    if value is None:
        if name not in constants:
            raise KeyError(f"常量不存在：{name}")
        del constants[name]
        manager.mark_modified(year, month)
        manager.save_all_modified()
        return f"已删除常量：{name}"
    constants[name] = int(value)
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return {"name": name, "value": constants[name]}


def rename_expense(idx: list, new_name: str) -> dict:
    """
    重命名指定的记账项或记账类型

    Parameters:
        idx (list): 根到目标的索引路径（如 [0,2]）
        new_name (str): 新名称

    Returns:
        dict: 重命名后的节点数据

    Raises:
        IndexError: 索引路径超出范围
        ValueError: 名称为空
    """
    if not new_name or not str(new_name).strip():
        raise ValueError("新名称不能为空")
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    node = _resolve_expense(data.get('children', []), idx)
    node['name'] = str(new_name).strip()
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return node


def delete_expense(idx: list) -> str:
    """
    删除指定的记账项或记账类型（连同其子项）

    Parameters:
        idx (list): 根到目标的索引路径（如 [0,2]）

    Returns:
        str: 删除结果说明

    Raises:
        IndexError: 索引路径超出范围
    """
    if not idx:
        raise IndexError("记账索引不能为空")
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    parent = _resolve_parent_list(data.get('children', []), idx[:-1])
    node = parent[idx[-1]]
    parent.pop(idx[-1])
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return f"已删除：{node.get('name')}"


def modify_expense_budget(idx: list, budget_formula: str) -> dict:
    """
    修改指定记账项的预算公式

    Parameters:
        idx (list): 根到目标的索引路径（如 [0,2]）
        budget_formula (str): 新的预算公式（如 "10 * days"）

    Returns:
        dict: 修改后的记账项数据

    Raises:
        IndexError: 索引路径超出范围
        ValueError: 目标不是记账项
    """
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    node = _resolve_expense(data.get('children', []), idx)
    if node.get('type') != 'item':
        raise ValueError(f"记账索引 {idx} 指向的不是记账项，无法修改预算")
    node['estimated_amount'] = "" if budget_formula is None else str(budget_formula)
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return node


def record_expense(idx: list, delta: float) -> dict:
    """
    对指定记账项记账，使其实际消费增加 delta

    Parameters:
        idx (list): 根到目标的索引路径（如 [0,2]）
        delta (float): 消费金额增量

    Returns:
        dict: 修改后的记账项数据

    Raises:
        IndexError: 索引路径超出范围
        ValueError: 目标不是记账项
    """
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    node = _resolve_expense(data.get('children', []), idx)
    if node.get('type') != 'item':
        raise ValueError(f"记账索引 {idx} 指向的不是记账项，无法记账")
    node['actual_amount'] = round(node.get('actual_amount', 0) + float(delta), 2)
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return node


def reorder_expense(idx: list, new_idx: int) -> dict:
    """
    调整指定记账项/类型在其同级列表中的顺序

    只影响该节点同级列表中的位置；若需要调整某个子项，请传入包含其父项路径的完整索引

    Parameters:
        idx (list): 根到目标的索引路径（如 [0,2]）
        new_idx (int): 同级列表中的新位置（从0开始）

    Returns:
        dict: 新的索引路径与节点数据

    Raises:
        IndexError: 索引路径或新位置超出范围
    """
    if not idx:
        raise IndexError("记账索引不能为空")
    year, month = _get_current_expense_month()
    manager = ExpenseDataManager()
    data = manager.load_month_data(year, month)
    parent = _resolve_parent_list(data.get('children', []), idx[:-1])
    if not 0 <= new_idx < len(parent):
        raise IndexError(f"新的位置 {new_idx} 超出范围（同级共 {len(parent)} 项）")
    node = parent.pop(idx[-1])
    parent.insert(new_idx, node)
    manager.mark_modified(year, month)
    manager.save_all_modified()
    return {"idx": list(idx[:-1]) + [new_idx], "node": node}


def get_recent_12_months_balance() -> dict:
    """
    读取近12个月余额（当前操作月份的前12个月，不含当前月份）

    Returns:
        dict: 以 "YYYY-MM" 为键、余额为值的字典

    Raises:
        FileNotFoundError: 余额数据文件不存在
    """
    year, month = _get_current_expense_month()
    months = []
    y, m = year, month
    for _ in range(12):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        months.append((y, m))
    months.reverse()

    balance_path = os.path.join("apps/expenses/data", "monthly_balance.json")
    if os.path.exists(balance_path):
        with open(balance_path, 'r', encoding='utf-8') as f:
            balance_data = json.load(f)
    else:
        balance_data = {}
    return {f"{y}-{m:02d}": balance_data.get(f"{y}-{m:02d}") for y, m in months}


def set_last_month_balance(balance: float) -> dict:
    """
    修改上个月（当前操作月份的前一个月）的余额

    Parameters:
        balance (float): 新的余额

    Returns:
        dict: 修改后的年月与余额
    """
    year, month = _get_current_expense_month()
    last_year, last_month = (year, month - 1) if month > 1 else (year - 1, 12)
    key = f"{last_year}-{last_month:02d}"

    balance_path = os.path.join("apps/expenses/data", "monthly_balance.json")
    if os.path.exists(balance_path):
        with open(balance_path, 'r', encoding='utf-8') as f:
            balance_data = json.load(f)
    else:
        balance_data = {}
    balance_data[key] = float(balance)
    os.makedirs(os.path.dirname(balance_path), exist_ok=True)
    with open(balance_path, 'w', encoding='utf-8') as f:
        json.dump(balance_data, f, ensure_ascii=False, indent=4)
    return {"year": last_year, "month": last_month, "balance": balance_data[key]}


# ============================ 露点计算 ============================


def calculate_dew_point(temperature: float, humidity: float) -> float:
    """
    根据温度与相对湿度计算露点温度

    Parameters:
        temperature (float): 温度（摄氏度）
        humidity (float): 相对湿度（百分比，0~100）

    Returns:
        float: 露点温度（摄氏度）
    """
    dew_point = _calc_dew_point(float(temperature), float(humidity))
    return round(dew_point, 1)


# ============================ 词元提取器 ============================


def extract_tokens(text: str) -> dict:
    """
    对文本进行分词，返回词元列表

    Parameters:
        text (str): 待分词的文本

    Returns:
        dict: 包含词元列表 splitted_list 与词元数量 len（len 为词元个数）
    """
    from apps.tokenizer.deepseek_tokenizer import tokenize
    splitted_list = tokenize("" if text is None else str(text))
    return {"splitted_list": splitted_list, "len": len(splitted_list)}
