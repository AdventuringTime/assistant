"""
应用列表定义文件
定义现有应用的名称、图标、点击操作等信息
"""
from importlib import import_module
import os


APP_LIST = {
    "settings": {
        "display_name": "设置",
        "icon": "apps/settings/icon.svg",
        "window": lambda: import_module('apps.settings').SettingsWindow()
    }
}