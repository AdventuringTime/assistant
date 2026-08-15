"""MCP 服务器数据访问层，通过各应用的数据管理器读写数据，不直接操作文件"""

from core.functions import get_today

from apps.calendar.calendar_schedule_manager import CalendarSchedulesManager
from apps.expenses import ExpenseDataManager
from apps.graduate_worktime import GraduateWorktimeDataManager
from apps.peer_tutor_2026 import TaskDataManager as PeerTutorTaskDataManager
from apps.search_words import SearchWordsDataManager
from apps.tasks import TaskDataManager as TasksDataManager


def get_today_schedules() -> dict:
    """读取今天的所有日程信息"""
    today = get_today()
    schedules = CalendarSchedulesManager().get_schedules(today.year, today.month, today.day)
    return schedules


def get_tasks(is_completed: bool = False) -> list[dict]:
    """
    读取所有未完成或已完成任务信息

    Parameters:
        is_completed (bool): 是否读取已完成任务，False 读取未完成任务（默认）
    """
    manager = TasksDataManager()
    tasks = manager.completed_tasks if is_completed else manager.tasks
    return list(tasks)


def get_graduate_worktime() -> str:
    """读取当前所有研招工时信息（含总时长统计）"""
    return GraduateWorktimeDataManager().get_export_text()


def get_search_words() -> list[str]:
    """读取当前所有待搜索词信息"""
    return list(SearchWordsDataManager().words)


def _annotate_expense_types(children: list, manager: ExpenseDataManager, constants: dict) -> list:
    """
    递归为记账类型节点附加预估与实际汇总，不修改原始数据

    Parameters:
        children (list): 记账子项列表
        manager (ExpenseDataManager): 数据管理器，用于调用汇总逻辑
        constants (dict): 常量字典，用于评估预估金额表达式

    Returns:
        list: 新列表，每个 type 节点的 estimated 与 actual 插入在 name 与 children 之间
    """
    result = []
    for child in children:
        if child.get('type') != 'type':
            result.append(child)
            continue
        estimated, actual = manager.sum_expenses(child.get('children', []), constants)
        annotated = {}
        for key, value in child.items():
            if key == 'name':
                annotated[key] = value
                annotated['estimated'] = estimated
                annotated['actual'] = actual
            elif key == 'children':
                annotated[key] = _annotate_expense_types(value, manager, constants)
            else:
                annotated[key] = value
        result.append(annotated)
    return result


def get_month_expenses() -> dict:
    """读取当前月的所有记账信息，每个记账类型附上自身汇总，附带总额汇总"""
    today = get_today()
    manager = ExpenseDataManager()
    data = manager.load_month_data(today.year, today.month)
    constants = data.get('constants', {})
    children = data.get('children', [])
    estimated, actual = manager.sum_expenses(children, constants)
    return {
        "year": today.year,
        "month": today.month,
        "constants": constants,
        "children": _annotate_expense_types(children, manager, constants),
        "summary": {"estimated": estimated, "actual": actual},
    }


def get_peer_tutor_week_tasks() -> dict:
    """读取当前周芙芙伴学所有任务信息，当前周数据不存在时自动从上周继承"""
    manager = PeerTutorTaskDataManager()
    week = manager.get_current_week_num()
    manager.inherit_tasks_from_last_week_if_not_exist(week)
    tasks = manager.get_tasks(week)
    return {"week": week, "tasks": tasks}


def update_peer_tutor_task_progress(task_index: int, completed: float) -> dict:
    """
    修改当前周芙芙伴学特定任务的完成进度

    Parameters:
        task_index (int): 任务序号（从1开始）
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
    index = task_index - 1
    if not 0 <= index < len(tasks):
        raise IndexError(f"任务序号 {task_index} 超出范围（共 {len(tasks)} 个任务）")
    tasks[index]['completed'] = completed
    manager.mark_modified(week)
    manager.save_tasks()
    return tasks[index]
