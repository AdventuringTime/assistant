"""
应用列表定义文件
定义现有应用的名称、图标、点击操作等信息
"""

import os

# 应用列表定义（字典格式，键为应用名，对应路径apps/应用名）
APP_LIST = {
    # 示例应用（注释状态）
    # "example": {
    #     "display_name": "示例应用",
    #     "icon": "apps/example/icon.svg",  # 默认路径apps/应用名/icon.svg
    #     "window": lambda: __import__('apps.example').ExampleWindow(),
    #     "description": "这是一个示例应用"
    # }
}