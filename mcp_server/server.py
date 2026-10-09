"""MCP 服务器：通过各应用的数据管理器向外暴露数据读写工具

随主程序（run.py）一起运行，由 McpServerManager 管理生命周期。
"""

from core.global_constants import APP_VERSION
from mcp.server.mcpserver import MCPServer

from mcp_server.data_providers import (
    add_expense_item,
    add_expense_type,
    add_schedule,
    add_search_word,
    add_task,
    add_worktime_row,
    calculate_dew_point,
    change_task_order,
    clear_worktime,
    complete_tracking_task,
    delete_expense,
    delete_search_word,
    delete_worktime_row,
    edit_expense_constant,
    edit_schedule,
    edit_task,
    edit_worktime_row,
    extract_tokens,
    get_date_schedules,
    get_graduate_worktime,
    get_month_expenses,
    get_peer_tutor_week_tasks,
    get_peer_tutor_window_screenshot,
    get_recent_12_months_balance,
    get_search_words,
    set_last_month_balance,
    get_tasks,
    get_today_schedules,
    go_to_tracking_task,
    modify_expense_budget,
    record_expense,
    rename_expense,
    rename_search_word,
    reorder_expense,
    switch_expense_month,
    switch_tracking,
    update_peer_tutor_task,
    update_peer_tutor_task_progress,
)


server = MCPServer(
    name="assistant",
    title="探索酱的小助手连接器",
    description="探索酱的小助手连接器",
    version=APP_VERSION,
)

# ---------------------------- 日程 ----------------------------

server.add_tool(
    get_today_schedules,
    name="get_today_schedules",
    title="读取今天日程",
    description="读取今天的所有日程信息",
)

server.add_tool(
    get_date_schedules,
    name="get_date_schedules",
    title="读取指定日期日程",
    description="读取指定日期的所有日程信息",
)

server.add_tool(
    add_schedule,
    name="add_schedule",
    title="添加日程",
    description="添加一条日程。begin 与 end 为必填（格式 'YYYY-MM-DD HH:MM'），"
                "title/type/place/repeat/description 可选。type：0 其他（默认） 1 会议 2 娱乐 3 活动 4 课程；"
                "repeat：0 无（默认） 1 每天 2 每周",
)

server.add_tool(
    edit_schedule,
    name="edit_schedule",
    title="编辑日程",
    description="编辑指定日期（year, month, day）下 ID 为 id 的日程，仅覆盖提供了的字段。"
                "delete 为 True 时删除；copy 为 True 时保存副本；begin 改变时日程会移动到新日期",
)

# ---------------------------- 任务 ----------------------------

server.add_tool(
    get_tasks,
    name="get_tasks",
    title="读取任务",
    description="读取当前所有未完成或已完成的任务信息。读取未完成还是已完成的任务由参数 is_completed 决定",
)

server.add_tool(
    add_task,
    name="add_task",
    title="添加任务",
    description="添加一个任务。仅 name 必填，type/subtasks/required/deadline/estimated_complete/link 可选。"
                "type：0 支线（默认） 1 主线；子任务每行一个",
)

server.add_tool(
    switch_tracking,
    name="switch_tracking",
    title="切换任务追踪",
    description="切换指定任务的追踪状态：正在追踪则停止追踪，否则开始追踪",
)

server.add_tool(
    edit_task,
    name="edit_task",
    title="编辑任务",
    description="编辑指定任务，仅覆盖提供了的字段。delete 为 True 时删除；copy 为 True 时保存副本",
)

server.add_tool(
    go_to_tracking_task,
    name="go_to_tracking_task",
    title="前往追踪中任务",
    description="打开追踪中任务关联的链接",
)

server.add_tool(
    complete_tracking_task,
    name="complete_tracking_task",
    title="完成追踪中任务",
    description="完成追踪中的任务，仅在进度已达到所需次数时可完成",
)

server.add_tool(
    change_task_order,
    name="change_task_order",
    title="更改任务顺序",
    description="更改指定任务在未完成任务列表中的顺序，new_idx 从 0 开始",
)

# ---------------------------- 研招工时 ----------------------------

server.add_tool(
    get_graduate_worktime,
    name="get_graduate_worktime",
    title="读取研招工时",
    description="读取当前所有研招工时记录，以及总时长统计",
)

server.add_tool(
    add_worktime_row,
    name="add_worktime_row",
    title="添加工时行",
    description="在研招工时末尾添加一行，日期默认今天、时长默认 1.5 小时，可选填工作内容 content",
)

server.add_tool(
    edit_worktime_row,
    name="edit_worktime_row",
    title="编辑工时行",
    description="编辑研招工时的某一行（idx 从 0 开始），仅覆盖提供了的字段（date/content/duration）",
)

server.add_tool(
    delete_worktime_row,
    name="delete_worktime_row",
    title="删除工时行",
    description="删除研招工时的某一行（idx 从 0 开始）",
)

server.add_tool(
    clear_worktime,
    name="clear_worktime",
    title="清空工时",
    description="清空所有研招工时记录",
)

# ---------------------------- 搜索词 ----------------------------

server.add_tool(
    get_search_words,
    name="get_search_words",
    title="读取搜索词",
    description="读取当前所有待搜索词信息",
)

server.add_tool(
    add_search_word,
    name="add_search_word",
    title="添加搜索词",
    description="在搜索词列表末尾添加一个搜索词",
)

server.add_tool(
    rename_search_word,
    name="rename_search_word",
    title="重命名搜索词",
    description="重命名指定搜索词（idx 从 0 开始）",
)

server.add_tool(
    delete_search_word,
    name="delete_search_word",
    title="删除搜索词",
    description="删除指定搜索词（idx 从 0 开始）",
)

# ---------------------------- 记账 ----------------------------

server.add_tool(
    get_month_expenses,
    name="get_month_expenses",
    title="读取当月记账",
    description="读取当前月的所有记账信息（常量与各记账项），并附带预估与实际总额汇总",
)

server.add_tool(
    switch_expense_month,
    name="switch_expense_month",
    title="切换记账月份",
    description="切换记账操作的目标月份，影响其余记账工具与读取近12个月余额",
)

server.add_tool(
    add_expense_item,
    name="add_expense_item",
    title="添加记账项",
    description="在指定位置添加记账项。idx 为父节点的索引路径（如 [0,2]），省略表示根级；name 为记账项名称",
)

server.add_tool(
    add_expense_type,
    name="add_expense_type",
    title="添加记账类型",
    description="在指定位置添加记账类型。idx 为父节点的索引路径（如 [0,2]），省略表示根级；name 为类型名称",
)

server.add_tool(
    edit_expense_constant,
    name="edit_expense_constant",
    title="编辑记账常量",
    description="添加、修改或删除记账常量。value 为整数时设置该常量；value 省略时删除该常量",
)

server.add_tool(
    rename_expense,
    name="rename_expense",
    title="重命名记账项",
    description="重命名指定的记账项或记账类型。idx 为根到目标的索引路径（如 [0,2]）",
)

server.add_tool(
    delete_expense,
    name="delete_expense",
    title="删除记账项",
    description="删除指定的记账项或记账类型（连同其子项）。idx 为根到目标的索引路径（如 [0,2]）",
)

server.add_tool(
    modify_expense_budget,
    name="modify_expense_budget",
    title="修改记账预算",
    description="修改指定记账项的预算公式（如 '10 * days'）。idx 为根到目标的索引路径",
)

server.add_tool(
    record_expense,
    name="record_expense",
    title="记账",
    description="对指定记账项记账，使其实际消费增加 delta。idx 为根到目标的索引路径",
)

server.add_tool(
    reorder_expense,
    name="reorder_expense",
    title="排序记账项",
    description="调整指定记账项/类型在其同级列表中的顺序，new_idx 从 0 开始。"
                "只影响该节点同级的位置，要调整子项需传入包含父项路径的完整 idx",
)

server.add_tool(
    get_recent_12_months_balance,
    name="get_recent_12_months_balance",
    title="读取近12个月余额",
    description="读取近12个月余额（当前操作月份的前12个月，不含当前月份）",
)

server.add_tool(
    set_last_month_balance,
    name="set_last_month_balance",
    title="修改上个月余额",
    description="修改当前操作月份的前一个月的余额",
)

# ---------------------------- 露点计算 ----------------------------

server.add_tool(
    calculate_dew_point,
    name="calculate_dew_point",
    title="计算露点",
    description="根据温度（摄氏度）与相对湿度（百分比 0~100）计算露点温度",
)

# ---------------------------- 词元提取器 ----------------------------

server.add_tool(
    extract_tokens,
    name="extract_tokens",
    title="提取词元",
    description="对文本进行分词，返回词元列表 splitted_list 与词元数量 len",
)

# ---------------------------- 芙芙伴学 ----------------------------

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
    description="修改当前周芙芙伴学特定任务的完成进度。task_index 为任务序号（从0开始），completed 为新的完成数量",
)

server.add_tool(
    update_peer_tutor_task,
    name="update_peer_tutor_task",
    title="修改芙芙伴学任务",
    description="添加、修改或删除当前周芙芙伴学任务。index 未指定时添加新任务（需提供 name）；"
                "指定 index（从0开始）且提供数据字段（name/required/weight）时修改对应任务；"
                "指定 index 且未提供任何数据字段时删除该任务。修改完成进度请使用 update_peer_tutor_task_progress",
)

server.add_tool(
    get_peer_tutor_window_screenshot,
    name="get_peer_tutor_window_screenshot",
    title="读取芙芙伴学窗口截图",
    description="截取芙芙伴学主窗口，返回窗口图片",
)
