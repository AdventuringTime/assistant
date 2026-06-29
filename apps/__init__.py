"""
应用列表定义文件
定义现有应用的名称、图标、点击操作等信息
"""
from importlib import import_module


APP_LIST = {
    "settings": {
        "display_name": "设置",
        "window": lambda: import_module('apps.settings').SettingsWindow()
    },
    "calendar": {
        "display_name": "日程",
        "window": lambda: import_module('apps.calendar').CalendarWindow()
    },
    "tasks": {
        "display_name": "任务",
        "window": lambda: import_module('apps.tasks').TaskWindow()
    },
    "graduate_worktime": {
        "display_name": "研招工时统计",
        "window": lambda: import_module('apps.graduate_worktime').GraduateWorktimeWindow()
    },
    "search_words": {
        "display_name": "搜索词",
        "window": lambda: import_module('apps.search_words').SearchWordsWindow()
    },
    "expenses": {
        "display_name": "记账",
        "window": lambda: import_module('apps.expenses').ExpensesWindow()
    },
    "peer_tutor_2026": {
        "display_name": "芙芙伴学",
        "window": lambda: import_module('apps.peer_tutor_2026').FurinaWindow(),
        "icon": "apps/peer_tutor_2026/assets/icon.ico"
    },
    "tokenizer": {
        "display_name": "词元提取器",
        "window": lambda: import_module('apps.tokenizer').TokenizerWindow()
    }
}