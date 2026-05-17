import sys
import json
import os
from PySide6.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout,
                               QScrollArea, QHBoxLayout, QInputDialog, QPushButton,
                               QLineEdit, QDoubleSpinBox, QMessageBox, QSpinBox)
from PySide6.QtCore import Qt, Signal, QEvent, QTimer
from PySide6.QtGui import QIcon

from core.base_window import BaseWindow, BaseDialog
from core.functions import get_this_week, get_today
import datetime
from math import floor


icon = QIcon('apps/peer_tutor_2026/assets/icon.ico')

class TaskDialog(BaseDialog):
    on_save_signal = Signal(dict)
    on_delete_signal = Signal()

    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle('任务')
        self.setWindowIcon(icon)
        self.setModal(True)

        self.layout_ = QVBoxLayout(self)

        self.name_label = QLabel('任务名称:')
        self.name_edit = QLineEdit()
        if task:
            self.name_edit.setText(task.get('name', ''))
        self.layout_.addWidget(self.name_label)
        self.layout_.addWidget(self.name_edit)

        self.required_label = QLabel('所需次数:')
        self.required_spin = QDoubleSpinBox(decimals=2)
        self.required_spin.setRange(0.0, 1e15)
        if task:
            self.required_spin.setValue(task.get('required', 1.0))
        self.required_spin.lineEdit().installEventFilter(self)
        self.layout_.addWidget(self.required_label)
        self.layout_.addWidget(self.required_spin)

        self.weight_label = QLabel('权重:')
        self.weight_spin = QSpinBox()
        self.weight_spin.setRange(1, 2147483647)
        if task:
            self.weight_spin.setValue(task.get('weight', 100))
        else:
            self.weight_spin.setValue(100)
        self.layout_.addWidget(self.weight_label)
        self.layout_.addWidget(self.weight_spin)

        self.button_layout = QHBoxLayout()

        self.button_layout.addStretch()

        if task:
            self.delete_button = QPushButton('删除')
            self.delete_button.setStyleSheet("background-color: #CC0000; color: #FFFFFF;")
            self.delete_button.clicked.connect(self.on_delete)
            self.button_layout.addWidget(self.delete_button)

        self.save_button = QPushButton('保存')
        self.save_button.clicked.connect(self.on_save)
        self.save_button.setDefault(True)
        self.button_layout.addWidget(self.save_button)

        self.layout_.addLayout(self.button_layout)

    def on_save(self):
        self.on_save_signal.emit(self.get_task_data())
        self.close()

    def on_delete(self):
        reply = QMessageBox.question(self, '删除任务', '删除任务？',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.on_delete_signal.emit()
            self.close()

    def get_task_data(self):
        return {
            'name': self.name_edit.text(),
            'completed': self.task.get('completed', 0.0) if self.task else 0.0,
            'required': self.required_spin.value(),
            'weight': self.weight_spin.value()
        }

    def eventFilter(self, obj, event):
        if obj == self.required_spin and event.type() == QEvent.Type.FocusIn:
            QTimer.singleShot(0, self.required_spin.selectAll)
            return False
        return super().eventFilter(obj, event)


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
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
            }
            QLabel:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.name_label.mousePressEvent = self.on_name_clicked
        self.layout_.addWidget(self.name_label)

        self.completed = self.task.get('completed', 0.0)
        self.required = self.task.get('required', 1.0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(20)

        self.progress_label = QLabel()
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

        self.update_progress_percent()

    def update_progress_percent(self):
        """更新进度条和进度标签"""
        if self.required == 0.0:
            self.progress_label.setText('已完成')
            self.progress_percent = 100
        elif self.required == 1.0:
            self.progress_percent = self.completed * 100
            if self.completed == 1.0:
                self.progress_label.setText('未完成')
            elif self.completed == 1.0:
                self.progress_label.setText('已完成')
            else:
                self.progress_label.setText(f'{self.completed}/{self.required}')
        else:
            self.progress_label.setText(f'{self.completed}/{self.required}')
            self.progress_percent = (self.completed / self.required) * 100

        progress_value = int(self.progress_percent)
        if progress_value < 0:
            progress_value = 0
        elif progress_value > 100:
            progress_value = 100
        self.progress_bar.setValue(progress_value)

    def on_progress_clicked(self, event):
        self.completed, ok = QInputDialog.getDouble(self, '修改进度',
            f'请输入完成数量:',
            value=self.completed,
            decimals=2)

        if ok:
            self.task['completed'] = self.completed
            self.update_progress_percent()
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
        self.task['weight'] = data['weight']
        self.name_label.setText(data['name'])
        self.required = data['required']
        self.update_progress_percent()
        self.task_updated.emit()


class TaskWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('芙芙伴学')
        self.setWindowIcon(icon)
        self.setMinimumSize(600, 400)

        self.this_week_num = floor(get_this_week(
            start_date=datetime.datetime(2026, 5, 11, 4, 0, 0))) + 1
        self.week_displayed = self.this_week_num
        self.is_showing_this_week = True
        self.tasks = []
        self.task_items = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.header = QLabel()
        self.header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        self.header.setMargin(5)
        self.main_layout.addWidget(self.header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setFixedHeight(20)

        self.total_progress_label = QLabel('0%')
        self.total_progress_label.setStyleSheet("font-size: 15px; color: #888888;")

        self.total_progress_widget = QWidget()
        self.total_progress_layout = QHBoxLayout(self.total_progress_widget)
        self.total_progress_layout.addWidget(self.total_progress_bar)
        self.total_progress_layout.addWidget(self.total_progress_label)
        self.main_layout.addWidget(self.total_progress_widget)

        self.button_layout = QHBoxLayout()

        self.week_switch_button = QPushButton('上周')
        self.week_switch_button.clicked.connect(self.toggle_week)
        self.button_layout.addWidget(self.week_switch_button)

        self.button_layout.addStretch()

        self.add_button = QPushButton('添加任务')
        self.add_button.clicked.connect(self.on_add_task)
        self.button_layout.addWidget(self.add_button)

        self.open_yesterday_folder_button = QPushButton('打开昨日文件夹')
        self.open_yesterday_folder_button.clicked.connect(self.open_yesterday_folder)
        self.button_layout.addWidget(self.open_yesterday_folder_button)

        self.open_today_folder_button = QPushButton('打开今日文件夹')
        self.open_today_folder_button.clicked.connect(self.open_today_folder)
        self.button_layout.addWidget(self.open_today_folder_button)

        self.open_folder_button = QPushButton('打开此周文件夹')
        self.open_folder_button.clicked.connect(self.open_this_week_folder)
        self.button_layout.addWidget(self.open_folder_button)

        self.main_layout.addLayout(self.button_layout)

        self.load_and_display_tasks()

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
        total_weight = 0
        if self.task_items:
            for task in self.task_items:
                weight = task.task.get('weight', 100)
                total_percent += task.progress_percent * weight
                total_weight += weight

            total_percent = total_percent / total_weight # 前文代码注意确保 total_weight 不为 0

        progress_value = int(total_percent)
        if progress_value < 0:
            progress_value = 0
        elif progress_value > 100:
            progress_value = 100
        self.total_progress_bar.setValue(progress_value)
        self.total_progress_label.setText(f'{int(total_percent)}%')

    @staticmethod
    def _open_folder_of_dir(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        if sys.platform == 'win32': # 限 Windows
            os.startfile(data_dir)
        else:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(data_dir))

    def open_this_week_folder(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data',
                                str(self.week_displayed))
        self._open_folder_of_dir(data_dir)

    @staticmethod
    def open_folder_of_the_day(dt: datetime.datetime):
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        week = floor(get_this_week(dt=dt,
            start_date=datetime.datetime(2026, 5, 11, 4, 0, 0))) + 1
        dt_date = get_today(dt) # 处理跨天问题

        data_dir = os.path.join(os.path.dirname(__file__), 'data',
                                str(week), days_of_week[dt_date.weekday()])
        TaskWindow._open_folder_of_dir(data_dir)

    @staticmethod
    def open_today_folder():
        TaskWindow.open_folder_of_the_day(datetime.datetime.now())

    @staticmethod
    def open_yesterday_folder():
        TaskWindow.open_folder_of_the_day(datetime.datetime.now() - datetime.timedelta(days=1))

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
            self.content_layout.insertWidget(len(self.task_items) - 1, task_item)
            self.save_tasks()
            self.update_total_progress()

    def toggle_week(self):
        if self.is_showing_this_week:
            self.week_displayed = self.this_week_num - 1
            self.week_switch_button.setText('本周')
        else:
            self.week_displayed = self.this_week_num
            self.week_switch_button.setText('上周')
        self.is_showing_this_week = not self.is_showing_this_week
        self.load_and_display_tasks()

    def load_and_display_tasks(self):
        for item in self.task_items:
            item.deleteLater()
        self.task_items.clear()
        self.tasks.clear()
        self.load_tasks()
        for task in self.tasks:
            task_item = TaskItem(task)
            task_item.task_updated.connect(self.on_task_updated)
            task_item.task_deleted.connect(self.on_task_deleted)
            self.task_items.append(task_item)
            self.content_layout.insertWidget(len(self.task_items) - 1, task_item)
        self.header.setText(f'第{self.week_displayed}周')
        self.update_total_progress()