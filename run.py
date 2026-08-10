import sys

# 创建应用程序
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

# 设置应用程序不在窗口关闭后退出
app.setQuitOnLastWindowClosed(False)

# 设置全局异常处理
from core.error_window import excepthook
sys.excepthook = excepthook

# 创建并打开主窗口
from homepage.main_window import MainWindow
window = MainWindow()
window.show()

# 启动 MCP 服务器（随主程序一起启动，退出时自动停止）
from mcp_server.lifecycle import McpServerManager
mcp_manager = McpServerManager()
mcp_manager.start()
app.aboutToQuit.connect(mcp_manager.stop)

# 运行应用程序
sys.exit(app.exec())