import sys

# 打开指定app窗口
if len(sys.argv) > 1:
    app_name = sys.argv[1]
else:
    app_name = input("请输入应用名称: ")

from apps import APP_LIST
if app_name not in APP_LIST:
    raise NameError(f"Unknown app: {app_name}")

# 创建应用程序
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

# 设置全局异常处理
from core.error_window import excepthook
sys.excepthook = excepthook

window = APP_LIST[app_name]["window"]()
window.show()

# 运行应用程序
sys.exit(app.exec())