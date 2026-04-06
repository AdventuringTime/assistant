"""
应用列表定义文件
定义现有应用的名称、图标、点击操作等信息
"""
import os


APP_LIST = {
    "settings": {
        "display_name": "设置",
        "icon": "apps/settings/icon.svg",
        "window": lambda: __import__('apps.settings').SettingsWindow()
    }
}