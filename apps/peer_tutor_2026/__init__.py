import json
import os
from PySide6.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout, 
                               QScrollArea, QHBoxLayout, QInputDialog)
from PySide6.QtCore import Qt, Signal
from core.base_window import BaseWindow


class TaskItem(QWidget):
    task_updated = Signal()
    
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            TaskItem:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.layout_ = QVBoxLayout(self)

        self.name_label = QLabel(self.task.get('name', ''))
        self.name_label.setWordWrap(True)
        self.layout_.addWidget(self.name_label)

        self.completed = self.task.get('completed', 0)
        self.required = self.task.get('required', 1)

        if self.required == 0:
            self.progress_text = '已完成'
            self.progress_percent = 100
        elif self.required == 1:
            if self.completed < 1:
                self.progress_text = '未完成'
            else:
                self.progress_text = '已完成'
            self.progress_percent = self.completed * 100
        else:
            self.progress_text = f'{self.completed}/{self.required}'
            self.progress_percent = (self.completed / self.required) * 100

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(self.progress_percent))
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #4D4D50;
            }
        """)

        self.progress_label = QLabel(self.progress_text)
        self.progress_label.setStyleSheet("font-size: 16px; color: #888888;")

        self.progress_widget = QWidget()
        self.progress_layout = QHBoxLayout(self.progress_widget)
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addWidget(self.progress_label)
        
        self.progress_widget.setStyleSheet("""
            QWidget:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.progress_widget.mousePressEvent = self.on_progress_clicked

        self.layout_.addWidget(self.progress_widget)

    def on_progress_clicked(self, event):
        required = self.task.get('required', 1)
        completed = self.task.get('completed', 0)
        
        new_completed, ok = QInputDialog.getInt(self, '修改进度', 
            f'请输入完成数量（0-{required}）:',
            value=completed, minValue=0, maxValue=required)
        
        if ok:
            self.task['completed'] = new_completed
            progress_percent = (new_completed / required) * 100 if required > 0 else 100
            self.progress_bar.setValue(int(progress_percent))
            self.progress_label.setText(f'{new_completed}/{required}')
            self.task_updated.emit()


class TaskWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('任务列表')
        self.setMinimumSize(600, 400)

        self.tasks = []
        self.load_tasks()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.header = QLabel('第1周')
        self.header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        self.main_layout.addWidget(self.header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        for task in self.tasks:
            task_item = TaskItem(task)
            task_item.task_updated.connect(self.on_task_updated)
            self.content_layout.addWidget(task_item)

        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setFixedHeight(24)
        self.total_progress_bar.setStyleSheet("""
            QProgressBar::chunk {
                background-color: #4D4D50;
            }
        """)
        self.total_progress_label = QLabel('总进度: 0%')
        self.total_progress_label.setStyleSheet("font-size: 14px; color: #AAAAAA;")
        self.total_progress_widget = QWidget()
        self.total_progress_layout = QHBoxLayout(self.total_progress_widget)
        self.total_progress_layout.addWidget(self.total_progress_bar)
        self.total_progress_layout.addWidget(self.total_progress_label)
        self.main_layout.addWidget(self.total_progress_widget)

        self.update_total_progress()

    def load_tasks(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data', '1')
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            self.tasks = json.load(f)

    def save_tasks(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data', '1')
        json_path = os.path.join(data_dir, 'tasks.json')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=4)

    def on_task_updated(self):
        self.save_tasks()