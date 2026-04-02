from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

class ContentWidget(QWidget):
    """自定义内容部件，包含文本和切换按钮"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化显示状态
        self.is_hello = True
        
        # 创建布局和部件
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建布局
        layout = QHBoxLayout()
        
        # 创建文本标签
        self.text_label = QLabel("Hello, world!")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 创建切换按钮
        self.toggle_button = QPushButton("切换文字")
        
        # 连接按钮点击事件
        self.toggle_button.clicked.connect(self.toggle_text)
        
        # 将部件添加到布局
        layout.addWidget(self.text_label)
        layout.addWidget(self.toggle_button)
        
        # 设置布局
        self.setLayout(layout)
    
    def toggle_text(self):
        """切换显示的文本"""
        if self.is_hello:
            # 切换到另一段文字
            self.text_label.setText("欢迎使用PySide6应用程序！\n这是一个功能演示。")
        else:
            # 切换回Hello world
            self.text_label.setText("Hello, world!")
        
        # 切换状态
        self.is_hello = not self.is_hello