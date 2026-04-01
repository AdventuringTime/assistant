from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题
        self.setWindowTitle("我的第一个PySide6程序")
        
        # 设置窗口大小
        self.resize(400, 300)
        
        # 创建标签，显示文字
        label = QLabel("Hello, world!", self)
        
        # 设置标签居中显示
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 设置标签样式（可选，让文字更大更好看）
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #3498db;
            }
        """)
        
        # 将标签设置为窗口的中心部件
        self.setCentralWidget(label)

if __name__ == "__main__":
    # 创建应用程序对象
    app = QApplication(sys.argv)
    
    # 创建主窗口对象
    window = MainWindow()
    
    # 显示窗口
    window.show()
    
    # 进入应用程序事件循环，等待用户操作
    sys.exit(app.exec())