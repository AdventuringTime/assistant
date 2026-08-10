"""MCP 服务器：通过各应用的数据管理器向外暴露数据读写工具

随主程序（run.py）一起运行，由 McpServerManager 管理生命周期。
"""

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
    name="assistant-data",
    title="桌面应用数据服务器",
    description="读取日程、任务、研招工时、搜索词、记账和芙芙伴学数据，并支持修改芙芙伴学任务进度",
    version="0.1.0",
)

server.add_tool(
    get_today_schedules,
    name="get_today_schedules",
    title="读取今天日程",
    description="读取今天的所有日程信息，包含标题、类型、开始/结束时间、地点、重复规则和描述",
)

server.add_tool(
    get_tasks,
    name="get_tasks",
    title="读取任务",
    description="读取当前所有任务信息。参数 is_completed 为 False 时返回未完成任务，为 True 时返回已完成任务",
)

server.add_tool(
    get_graduate_worktime,
    name="get_graduate_worktime",
    title="读取研招工时",
    description="读取当前所有研招工时记录（日期、内容、时长），并附带总时长统计",
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
    description="读取当前周芙芙伴学所有任务信息，当前周数据不存在时自动从上周继承",
)

server.add_tool(
    update_peer_tutor_task_progress,
    name="update_peer_tutor_task_progress",
    title="修改芙芙伴学任务进度",
    description="修改当前周芙芙伴学特定任务的完成进度。task_index 为任务序号（从1开始），completed 为新的完成数量",
)
