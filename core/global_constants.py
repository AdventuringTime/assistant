import json
import os

app_name = "探索酱的小助手"
icon_path = "assets/logo.ico"

_version_json_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'assets', 'version.json')
try:
    with open(_version_json_path, 'r', encoding='utf-8') as f:
        APP_VERSION = json.load(f)
except (FileNotFoundError, IOError, json.JSONDecodeError):
    APP_VERSION = "0.1.0"

# 注意：不要在全局常量中直接创建QIcon对象
# 因为QGuiApplication必须在QIcon之前创建
# 应该在应用程序启动后动态创建QIcon