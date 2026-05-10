import sys
import json
import os
from PySide6.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout, 
                               QScrollArea, QHBoxLayout, QInputDialog, QPushButton,
                               QLineEdit, QSpinBox, QMessageBox)
from PySide6.QtCore import Qt, Signal
from core.base_window import BaseWindow, BaseDialog
from core.functions import get_this_week
import datetime
from math import floor


class TaskDialog(BaseDialog):
    on_save_signal = Signal(dict)
    on_delete_signal = Signal()

    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle('任务')

        self.layout_ = QVBoxLayout(self)

        self.name_label = QLabel('任务名称:')
        self.name_edit = QLineEdit()
        if task:
            self.name_edit.setText(task.get('name', ''))

        self.required_label = QLabel('所需次数:')
        self.required_spin = QSpinBox()
        self.required_spin.setRange(0, 2147483647)
        if task:
            self.required_spin.setValue(task.get('required', 1))

        self.layout_.addWidget(self.name_label)
        self.layout_.addWidget(self.name_edit)
        self.layout_.addWidget(self.required_label)
        self.layout_.addWidget(self.required_spin)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        self.save_button = QPushButton('保存')
        self.save_button.clicked.connect(self.on_save)

        if task:
            self.delete_button = QPushButton('删除')
            self.delete_button.setStyleSheet("background-color: #CC0000; color: #FFFFFF;")
            self.delete_button.clicked.connect(self.on_delete)
            self.button_layout.addWidget(self.delete_button)
    
        self.button_layout.addWidget(self.save_button)
        self.layout_.addLayout(self.button_layout)

    def on_save(self):
        self.on_save_signal.emit(self.get_task_data())
        self.close()

    def on_delete(self):
        reply = QMessageBox.question(self, '删除任务', '确认删除任务吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.on_delete_signal.emit()
            self.close()

    def get_task_data(self):
        return {
            'name': self.name_edit.text(),
            'completed': self.task.get('completed', 0) if self.task else 0,
            'required': self.required_spin.value()
        }


class TaskItem(QWidget):
    task_updated = Signal()
    task_deleted = Signal()
    
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
        self.name_label.setStyleSheet("QLabel:hover { background-color: rgba(255, 255, 255, 0.05); }")
        self.name_label.mousePressEvent = self.on_name_clicked
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

        self.progress_label = QLabel(self.progress_text)
        self.progress_label.setStyleSheet("font-size: 14px; color: #888888;")

        self.progress_widget = QWidget()
        self.progress_widget.setObjectName('progress_widget')
        self.progress_layout = QHBoxLayout(self.progress_widget)
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addWidget(self.progress_label)
        
        self.progress_widget.setStyleSheet("""
            #progress_widget:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.progress_widget.mousePressEvent = self.on_progress_clicked

        self.layout_.addWidget(self.progress_widget)

    def on_progress_clicked(self, event):
        self.completed, ok = QInputDialog.getInt(self, '修改进度', 
            f'请输入完成数量:',
            value=self.completed)

        if ok:
            self.task['completed'] = self.completed
            self.progress_percent = (self.completed / self.required) * 100 if self.required > 0 else 100
            self.progress_bar.setValue(int(self.progress_percent))
            self.progress_label.setText(f'{self.completed}/{self.required}')
            self.task_updated.emit()
    
    def on_name_clicked(self, event):
        dialog = TaskDialog(self.task, self)
        dialog.on_save_signal.connect(self.on_dialog_save)
        dialog.on_delete_signal.connect(self.on_dialog_delete)

        dialog.show()
    
    def on_dialog_delete(self):
        self.task_deleted.emit()
    
    def on_dialog_save(self, data):
        self.task['name'] = data['name']
        self.task['required'] = data['required']
        self.name_label.setText(data['name'])
        self.required = data['required']
        self.progress_percent = (self.completed / self.required) * 100 if self.required > 0 else 100
        self.progress_bar.setValue(int(self.progress_percent))
        self.progress_label.setText(f'{self.completed}/{self.required}')
        self.task_updated.emit()
    

class TaskWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('任务列表')
        self.setMinimumSize(600, 400)

        self.week_displayed = floor(get_this_week(start_date=datetime.datetime(2026, 5, 11, 4, 0, 0))) + 1
        self.tasks = []
        self.load_tasks()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.header = QLabel(f'第{self.week_displayed}周')
        self.header.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        self.main_layout.addWidget(self.header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        self.task_items = []
        for task in self.tasks:
            task_item = TaskItem(task)
            task_item.task_updated.connect(self.on_task_updated)
            task_item.task_deleted.connect(self.on_task_deleted)
            self.task_items.append(task_item)
            self.content_layout.addWidget(task_item)

        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setFixedHeight(20)

        self.total_progress_widget = QWidget()
        self.total_progress_layout = QHBoxLayout(self.total_progress_widget)
        self.total_progress_layout.addWidget(self.total_progress_bar)
        self.main_layout.addWidget(self.total_progress_widget)

        self.button_layout = QHBoxLayout()

        self.button_layout.addStretch()

        self.add_button = QPushButton('添加任务')
        self.add_button.clicked.connect(self.on_add_task)
        self.button_layout.addWidget(self.add_button)

        self.open_folder_button = QPushButton('打开文件夹')
        self.open_folder_button.clicked.connect(self.open_folder)
        self.button_layout.addWidget(self.open_folder_button)

        self.main_layout.addLayout(self.button_layout)

        self.update_total_progress()

    def load_tasks(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data', str(self.week_displayed))
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            self.tasks = json.load(f)

    def save_tasks(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data', str(self.week_displayed))
        json_path = os.path.join(data_dir, 'tasks.json')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=4)

    def update_total_progress(self):
        total_percent = 0
        if self.task_items:
            for task in self.task_items:
                total_percent += task.progress_percent
            total_percent = total_percent / len(self.task_items)
        
        self.total_progress_bar.setValue(int(total_percent))

    def open_folder(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data', str(self.week_displayed))
        os.makedirs(data_dir, exist_ok=True)
        if sys.platform == 'win32': # 限 Windows
            os.startfile(data_dir)
        else:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(data_dir))

    def on_task_updated(self):
        self.save_tasks()
        self.update_total_progress()

    def on_task_deleted(self):
        sender = self.sender()
        if sender in self.task_items:
            index = self.task_items.index(sender)
            self.task_items.remove(sender)
            self.tasks.pop(index)
            sender.deleteLater()
            self.save_tasks()
            self.update_total_progress()
    
    def on_add_task(self):
        dialog = TaskDialog(parent=self)
        dialog.on_save_signal.connect(self.on_dialog_create)
        dialog.show()
    
    def on_dialog_create(self, data):
        if data['name'].strip():
            self.tasks.append(data)
            task_item = TaskItem(data)
            task_item.task_updated.connect(self.on_task_updated)
            task_item.task_deleted.connect(self.on_task_deleted)
            self.task_items.append(task_item)
            self.content_layout.insertWidget(len(self.task_items), task_item)
            self.save_tasks()
            self.update_total_progress()