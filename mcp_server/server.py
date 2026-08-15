"""MCP 服务器：通过各应用的数据管理器向外暴露数据读写工具

随主程序（run.py）一起运行，由 McpServerManager 管理生命周期。
"""

from core.global_constants import APP_VERSION
from mcp.server.mcpserver import MCPServer

from mcp_server.data_providers import (
    get_graduate_worktime,
    get_month_expenses,
    get_peer_tutor_week_tasks,
    get_search_words,
    get_tasks,
    get_today_schedules,
    update_peer_tutor_task_progress,
)


server = MCPServer(
    name="assistant",
    title="探索酱的小助手连接器",
    description="读取日程、任务、研招工时、搜索词、记账和芙芙伴学数据，并支持修改芙芙伴学任务进度",
    version=APP_VERSION,
)

server.add_tool(
    get_today_schedules,
    name="get_today_schedules",
    title="读取今天日程",
    description="读取今天的所有日程信息",
)

server.add_tool(
    get_tasks,
    name="get_tasks",
    title="读取任务",
    description="读取当前所有未完成或已完成的任务信息。读取未完成还是已完成的任务由参数 is_completed 决定",
)

server.add_tool(
    get_graduate_worktime,
    name="get_graduate_worktime",
    title="读取研招工时",
    description="读取当前所有研招工时记录，以及总时长统计",
)

server.add_tool(
    get_search_words,
    name="get_search_words",
    title="读取搜索词",
    description="读取当前所有待搜索词信息",
)

server.add_tool(
    get_month_expenses,
    name="get_month_expenses",
    title="读取当月记账",
    description="读取当前月的所有记账信息（常量与各记账项），并附带预估与实际总额汇总",
)

server.add_tool(
    get_peer_tutor_week_tasks,
    name="get_peer_tutor_week_tasks",
    title="读取芙芙伴学本周任务",
    description="读取当前周芙芙伴学所有任务信息",
)

server.add_tool(
    update_peer_tutor_task_progress,
    name="update_peer_tutor_task_progress",
    title="修改芙芙伴学任务进度",
    description="修改当前周芙芙伴学特定任务的完成进度。task_index 为任务序号（从1开始），completed 为新的完成数量",
)
