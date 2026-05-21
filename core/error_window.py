"""
错误窗口模块，用于显示应用程序运行时的错误信息
"""

import sys
import traceback
from PySide6.QtWidgets import (QVBoxLayout, QTextEdit,
                               QLabel, QApplication)
from PySide6.QtGui import QFont

from core.base_window import BaseDialog


class ErrorWindow(BaseDialog):
    """错误信息显示窗口，用于展示应用程序运行时的异常信息"""

    def __init__(self, error_message, traceback_text, parent=None):
        """
        初始化错误窗口

        Parameters:
            error_message (str): 错误消息描述
            traceback_text (str): 异常堆栈跟踪信息
            parent (QWidget, optional): 父窗口，默认为None
        """
        super().__init__(parent)

        # 设置窗口属性
        self.setWindowTitle("发现异常")

        # 设置窗口样式
        self.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Courier New', monospace;
            }
        """)

        # 创建布局
        layout = QVBoxLayout()

        # 错误标题
        title_label = QLabel("发现异常")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 错误消息
        error_label = QLabel(error_message)
        layout.addWidget(error_label)

        # 错误详情文本框
        self.traceback_edit = QTextEdit()
        self.traceback_edit.setPlainText(traceback_text)
        self.traceback_edit.setReadOnly(True)
        layout.addWidget(self.traceback_edit)

        self.setLayout(layout)

        self.resize(400, 300)

    def copy_error_info(self):
        """复制错误堆栈信息到系统剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.traceback_edit.toPlainText())


def show_error_dialog(error_message, traceback_text, parent=None):
    """
    创建并显示错误对话框

    Parameters:
        error_message (str): 错误消息描述
        traceback_text (str): 异常堆栈跟踪信息
        parent (QWidget, optional): 父窗口，默认为None
    """
    error_window = ErrorWindow(error_message, traceback_text, parent)
    error_window.show()


def excepthook(exc_type, exc_value, exc_traceback):
    """
    全局异常处理钩子，捕获未处理的异常并显示错误窗口

    Parameters:
        exc_type (type): 异常类型
        exc_value (BaseException): 异常实例
        exc_traceback (traceback): 堆栈跟踪对象
    """

    # 调用原始异常处理（保留默认行为）
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

    # 显示错误对话框（如果Qt应用程序正在运行）
    if QApplication.instance() is not None:
        # 格式化错误信息
        error_message = str(exc_value)
        traceback_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        show_error_dialog(error_message, traceback_text)