from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton

from core.base_window import BaseWindow
from .deepseek_tokenizer import tokenize


class TokenizerWindow(BaseWindow):
    """词元提取器窗口，用于展示 DeepSeek 分词器的分词结果"""

    def __init__(self):
        """初始化词元提取器窗口"""
        super().__init__()

        self.setWindowTitle("词元提取器")
        self.setMinimumSize(600, 400)

        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.layout = QHBoxLayout(self.container)

        self.left_widget = QWidget()
        self.layout.addWidget(self.left_widget)
        self.left_layout = QVBoxLayout(self.left_widget)

        self.right_widget = QWidget()
        self.layout.addWidget(self.right_widget)
        self.right_layout = QVBoxLayout(self.right_widget)

        self.left_title = QLabel("输入")
        self.left_title.setFixedHeight(30)
        self.left_layout.addWidget(self.left_title)
        self.left_edit = QTextEdit()
        self.left_layout.addWidget(self.left_edit)

        self.right_title = QLabel("分词结果")
        self.right_title.setFixedHeight(30)
        self.right_layout.addWidget(self.right_title)
        self.right_edit = QTextEdit()
        self.right_edit.setReadOnly(True)
        self.right_layout.addWidget(self.right_edit)

        self.length_layout = QHBoxLayout()
        self.right_layout.addLayout(self.length_layout)

        self.length_label = QLabel("词元数")
        self.length_label.setFixedSize(100, 30)
        self.length_layout.addWidget(self.length_label)

        self.length_edit = QLineEdit()
        self.length_edit.setFixedHeight(30)
        self.length_edit.setReadOnly(True)
        self.length_layout.addWidget(self.length_edit)

        self.tokenize_button = QPushButton("分词")
        self.tokenize_button.clicked.connect(self.tokenize)
        self.tokenize_button.setFixedHeight(30)
        self.tokenize_button.setStyleSheet("background-color: #4CAF50; color: #ffffff;")
        self.left_layout.addWidget(self.tokenize_button)

    def tokenize(self):
        """执行分词操作，将输入文本分词后显示结果"""
        text = self.left_edit.toPlainText()
        tokens = tokenize(text)
        self.right_edit.setText(str(tokens))
        self.length_edit.setText(str(len(tokens)))