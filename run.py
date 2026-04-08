import sys

# 创建应用程序
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

# 设置全局异常处理
from core.error_window import excepthook
sys.excepthook = excepthook

# 创建并打开主窗口
from homepage.main_window import MainWindow
window = MainWindow()
window.show()

# 运行应用程序
sys.exit(app.exec())