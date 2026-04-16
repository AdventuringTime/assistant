"""
应用列表定义文件
定义现有应用的名称、图标、点击操作等信息
"""
from importlib import import_module


APP_LIST = {
    "settings": {
        "display_name": "设置",
        "icon": "apps/settings/icon.svg",
        "window": lambda: import_module('apps.settings').SettingsWindow()
    },
    "calendar": {
        "display_name": "日程",
        "icon": "apps/calendar/icon.svg",
        "window": lambda: import_module('apps.calendar').CalendarWindow()
    },
    "tokenizer": {
        "display_name": "词元提取器",
        "window": lambda: import_module('apps.tokenizer').TokenizerWindow()
    }
}