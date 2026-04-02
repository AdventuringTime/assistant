import sys
from PySide6.QtWidgets import QApplication
from homepage.main_window import MainWindow

def run_application():
    """
    运行应用程序的主函数
    """
    # 创建应用程序对象
    app = QApplication(sys.argv)
    
    # 创建主窗口对象
    window = MainWindow()
    
    # 显示窗口
    window.show()
    
    # 进入应用程序事件循环，等待用户操作
    return app.exec()

if __name__ == "__main__":
    # 运行应用程序
    sys.exit(run_application())