"""MCP 服务器数据访问层，通过各应用的数据管理器读写数据，不直接操作文件"""

from core.functions import get_today

from apps.calendar.calendar_schedule_manager import CalendarSchedulesManager
from apps.expenses import ExpenseDataManager, evaluate_estimated_amount
from apps.graduate_worktime import GraduateWorktimeDataManager
from apps.peer_tutor_2026 import TaskDataManager as PeerTutorTaskDataManager
from apps.search_words import SearchWordsDataManager
from apps.tasks import TaskDataManager as TasksDataManager


def get_today_schedules() -> list[dict]:
    """读取今天的所有日程信息"""
    today = get_today()
    schedules = CalendarSchedulesManager().get_schedules(today.year, today.month, today.day)
    return [
        {"id": str(id_), "date": today.isoformat(), **data}
        for id_, data in schedules.items()
    ]


def get_tasks(is_completed: bool = False) -> list[dict]:
    """
    读取所有未完成或已完成任务信息

    Parameters:
        is_completed (bool): 是否读取已完成任务，False 读取未完成任务（默认）
    """
    manager = TasksDataManager()
    tasks = manager.completed_tasks if is_completed else manager.tasks
    return list(tasks)


def get_graduate_worktime() -> dict:
    """读取当前所有研招工时信息，附带总时长统计"""
    records = list(GraduateWorktimeDataManager().records)
    total_hours = 0.0
    for record in records:
        try:
            total_hours += float(record.get("duration", 0))
        except (TypeError, ValueError):
            pass
    return {"records": records, "total_hours": total_hours}


def get_search_words() -> list[str]:
    """读取当前所有待搜索词信息"""
    return list(SearchWordsDataManager().words)


def _sum_expenses(children: list, constants: dict) -> tuple:
    """
    递归汇总记账数据中的预估与实际金额

    Parameters:
        children (list): 记账子项列表
        constants (dict): 常量字典

    Returns:
        tuple: (预估总额, 实际总额)，预估表达式无效时预估总额为 "Error"
    """
    estimated = 0.0
    actual = 0.0
    for child in children:
        if child.get('type') == 'item':
            value = evaluate_estimated_amount(child.get('estimated_amount', '0'), constants)
            if value == "Error":
                estimated = "Error"
            elif estimated != "Error":
                estimated += value
            actual += child.get('actual_amount', 0)
        elif child.get('type') == 'type':
            sub_estimated, sub_actual = _sum_expenses(child.get('children', []), constants)
            if sub_estimated == "Error":
                estimated = "Error"
            elif estimated != "Error":
                estimated += sub_estimated
            actual += sub_actual
    return estimated, actual


def get_month_expenses() -> dict:
    """读取当前月的所有记账信息，附带预估与实际总额汇总"""
    today = get_today()
    data = ExpenseDataManager().load_month_data(today.year, today.month)
    constants = data.get('constants', {})
    children = data.get('children', [])
    estimated, actual = _sum_expenses(children, constants)
    return {
        "year": today.year,
        "month": today.month,
        "constants": constants,
        "children": children,
        "summary": {"estimated": estimated, "actual": actual},
    }


def get_peer_tutor_week_tasks() -> dict:
    """读取当前周芙芙伴学所有任务信息，当前周数据不存在时自动从上周继承"""
    manager = PeerTutorTaskDataManager()
    week = manager.get_current_week_num()
    tasks = manager.get_current_week_tasks()
    return {"week": week, "tasks": tasks}


def update_peer_tutor_task_progress(task_index: int, completed: float) -> dict:
    """
    修改当前周芙芙伴学特定任务的完成进度

    Parameters:
        task_index (int): 任务序号（从1开始）
        completed (float): 新的完成数量
    """
    manager = PeerTutorTaskDataManager()
    week = manager.get_current_week_num()
    manager.inherit_tasks_from_last_week_if_not_exist(week)
    manager.update_task_progress(week, task_index, completed)
    return {
        "week": week,
        "task_index": task_index,
        "completed": completed,
        "tasks": manager.get_tasks(week),
    }
