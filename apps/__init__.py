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
    "worktime": {
        "display_name": "工作时间",
        "window": lambda: import_module('apps.worktime').WorktimeWindow()
    },
    "search_words": {
        "display_name": "搜索词",
        "window": lambda: import_module('apps.search_words').SearchWordsWindow()
    },
    "peer_tutor_2026": {
        "display_name": "朋辈助学",
        "window": lambda: import_module('apps.peer_tutor_2026').TaskWindow()
    },
    "tokenizer": {
        "display_name": "词元提取器",
        "window": lambda: import_module('apps.tokenizer').TokenizerWindow()
    },
    "expenses": {
        "display_name": "记账",
        "window": lambda: import_module('apps.expenses').ExpensesWindow()
    }
}