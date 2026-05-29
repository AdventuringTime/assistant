import sys
import json
import os
from PySide6.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout,
                               QScrollArea, QHBoxLayout, QInputDialog, QPushButton,
                               QLineEdit, QDoubleSpinBox, QMessageBox, QSpinBox,
                               QTabWidget, QFrame)
from PySide6.QtCore import Qt, Signal, QEvent, QTimer
from PySide6.QtGui import QIcon

from core.base_window import BaseWindow, BaseDialog
from core.functions import get_this_week, get_today, block_signals
import datetime
from math import floor


icon = QIcon('apps/peer_tutor_2026/assets/icon.ico')

class TaskDialog(BaseDialog):
    """任务编辑对话框，支持创建和编辑任务"""

    on_save_signal = Signal(dict)  # 保存任务信号
    on_delete_signal = Signal()    # 删除任务信号

    def __init__(self, task=None, parent=None):
        """
        初始化任务编辑对话框

        Parameters:
            task (dict, optional): 待编辑的任务数据，None表示新建任务
            parent (QWidget, optional): 父窗口
        """
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
        else:
            self.required_spin.setValue(1.0)
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

        self.required_spin.installEventFilter(self)
        self.weight_spin.installEventFilter(self)

    def on_save(self):
        """保存任务，发出保存信号并关闭对话框"""
        self.on_save_signal.emit(self.get_task_data())
        self.close()

    def on_delete(self):
        """删除任务，需用户确认"""
        reply = QMessageBox.question(self, '删除任务', '删除任务？',
                    QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            self.on_delete_signal.emit()
            self.close()

    def get_task_data(self):
        """
        获取当前表单中的任务数据

        Returns:
            dict: 任务数据字典
        """
        return {
            'name': self.name_edit.text(),
            'completed': self.task.get('completed', 0.0) if self.task else 0.0,
            'required': self.required_spin.value(),
            'weight': self.weight_spin.value()
        }

    def eventFilter(self, obj, event):
        """
        事件过滤器，实现输入框聚焦时自动全选

        Parameters:
            obj (QObject): 事件源对象
            event (QEvent): 事件对象

        Returns:
            bool: 是否拦截事件
        """
        if event.type() == QEvent.Type.FocusIn:
            if obj == self.required_spin:
                QTimer.singleShot(0, self.required_spin.selectAll)
            if obj == self.weight_spin:
                QTimer.singleShot(0, self.weight_spin.selectAll)
        return super().eventFilter(obj, event)


class TaskItem(QWidget):
    """任务项部件，显示单个任务的详细信息和进度"""

    task_updated = Signal()  # 任务更新信号
    task_deleted = Signal()  # 任务删除信号

    def __init__(self, task, parent=None):
        """
        初始化任务项部件

        Parameters:
            task (dict): 任务数据字典
            parent (QWidget, optional): 父控件
        """
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
        """更新进度条和进度标签显示"""
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
        """
        通过输入对话框修改完成数量

        Parameters:
            event (QMouseEvent): 鼠标点击事件
        """
        self.completed, ok = QInputDialog.getDouble(self, '修改进度',
            f'请输入完成数量:',
            value=self.completed,
            decimals=2)

        if ok:
            self.task['completed'] = self.completed
            self.update_progress_percent()
            self.task_updated.emit()

    def on_name_clicked(self, event):
        """
        点击任务名称打开编辑对话框

        Parameters:
            event (QMouseEvent): 鼠标点击事件
        """
        dialog = TaskDialog(self.task, self)
        dialog.on_save_signal.connect(self.on_dialog_save)
        dialog.on_delete_signal.connect(self.on_dialog_delete)

        dialog.show()

    def on_dialog_delete(self):
        """处理删除操作"""
        self.task_deleted.emit()

    def on_dialog_save(self, data):
        """
        处理保存操作，更新任务数据

        Parameters:
            data (dict): 更新后的任务数据
        """
        self.task['name'] = data['name']
        self.task['required'] = data['required']
        self.task['weight'] = data['weight']
        self.name_label.setText(data['name'])
        self.required = data['required']
        self.update_progress_percent()
        self.task_updated.emit()


class TaskWidget(QWidget):
    """任务管理组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.this_week_num = floor(get_this_week(
            start_date=datetime.datetime(2026, 5, 11, 4, 0, 0))) + 1
        self.week_displayed = self.this_week_num
        self.is_showing_this_week = True
        self.tasks = []
        self.task_items = []

        self.inherit_tasks_from_last_week_if_not_exist()

        self.main_layout = QVBoxLayout(self)

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

    def inherit_tasks_from_last_week_if_not_exist(self):
        """如果本周任务不存在，则从上一周继承任务（重置完成次数）"""
        this_week_dir = os.path.join(os.path.dirname(__file__), 'data', str(self.this_week_num))
        this_week_json_path = os.path.join(this_week_dir, 'tasks.json')

        if os.path.exists(this_week_json_path):
            return

        last_week_dir = os.path.join(os.path.dirname(__file__), 'data', str(self.this_week_num - 1))
        last_week_json_path = os.path.join(last_week_dir, 'tasks.json')
        if os.path.exists(last_week_json_path):
            os.makedirs(this_week_dir, exist_ok=True)
            with open(last_week_json_path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            for task in tasks:
                task['completed'] = 0.0
            with open(this_week_json_path, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=4)

    def load_tasks(self):
        """从文件加载指定周的任务数据"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data', str(self.week_displayed))
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            self.tasks = json.load(f)

    def save_tasks(self):
        """保存当前周的任务数据到文件"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data', str(self.week_displayed))
        json_path = os.path.join(data_dir, 'tasks.json')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=4)

    def update_total_progress(self):
        """更新加权总进度显示"""
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
        """
        打开指定目录

        Parameters:
            data_dir (str): 目录路径
        """
        os.makedirs(data_dir, exist_ok=True)
        if sys.platform == 'win32': # 限 Windows
            os.startfile(data_dir)
        else:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(data_dir))

    def open_this_week_folder(self):
        """打开当前显示周的文件夹"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data',
                                str(self.week_displayed))
        self._open_folder_of_dir(data_dir)

    @staticmethod
    def open_folder_of_the_day(dt: datetime.datetime):
        """
        打开指定日期对应的文件夹

        Parameters:
            dt (datetime.datetime): 日期时间对象
        """
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        week = floor(get_this_week(dt=dt,
            start_date=datetime.datetime(2026, 5, 11, 4, 0, 0))) + 1
        dt_date = get_today(dt) # 处理跨天问题

        data_dir = os.path.join(os.path.dirname(__file__), 'data',
                                str(week), days_of_week[dt_date.weekday()])
        TaskWidget._open_folder_of_dir(data_dir)

    @staticmethod
    def open_today_folder():
        """打开今日文件夹"""
        TaskWidget.open_folder_of_the_day(datetime.datetime.now())

    @staticmethod
    def open_yesterday_folder():
        """打开昨日文件夹"""
        TaskWidget.open_folder_of_the_day(datetime.datetime.now() - datetime.timedelta(days=1))

    def on_task_updated(self):
        """任务更新处理，保存任务并更新总进度"""
        self.save_tasks()
        self.update_total_progress()

    def on_task_deleted(self):
        """任务删除处理"""
        sender = self.sender()
        if sender in self.task_items:
            index = self.task_items.index(sender)
            self.task_items.remove(sender)
            self.tasks.pop(index)
            sender.deleteLater()
            self.save_tasks()
            self.update_total_progress()

    def on_add_task(self):
        """添加新任务"""
        dialog = TaskDialog()
        dialog.on_save_signal.connect(self.on_dialog_create)
        dialog.show()

    def on_dialog_create(self, data):
        """
        创建新任务处理

        Parameters:
            data (dict): 新任务数据
        """
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
        """切换显示本周/上周任务"""
        if self.is_showing_this_week:
            self.week_displayed = self.this_week_num - 1
            self.week_switch_button.setText('本周')
        else:
            self.week_displayed = self.this_week_num
            self.week_switch_button.setText('上周')
        self.is_showing_this_week = not self.is_showing_this_week
        self.load_and_display_tasks()

    def load_and_display_tasks(self):
        """加载并显示任务列表"""
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


class ExpensesWidget(QWidget):
    """流水管理组件"""

    def __init__(self, parent=None):
        """
        初始化流水管理组件
        
        Parameters:
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)

        self.today = get_today(datetime.datetime.now())
        # 前天昨天今天
        self.days = [self.today + datetime.timedelta(days=i) for i in range(-2, 1)]
        
        self.target = 0.0
        self.expenses = {}

        self.selected_circle = 2

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        self.main_layout.addStretch()

        # 进度行
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(0)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)

        circle1 = QPushButton()
        circle1.setFixedSize(40, 40)
        circle1.setStyleSheet("border-radius: 20px; background-color: gray;")
        circle1.clicked.connect(lambda: self.on_circle_clicked(0))

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)

        circle2 = QPushButton()
        circle2.setFixedSize(40, 40)
        circle2.setStyleSheet("border-radius: 20px; background-color: gray;")
        circle2.clicked.connect(lambda: self.on_circle_clicked(1))

        line3 = QFrame()
        line3.setFrameShape(QFrame.Shape.HLine)
        line3.setFrameShadow(QFrame.Shadow.Sunken)

        circle3 = QPushButton()
        circle3.setFixedSize(40, 40)
        circle3.setStyleSheet("border-radius: 20px; background-color: gray;")
        circle3.clicked.connect(lambda: self.on_circle_clicked(2))

        self.circles = [circle1, circle2, circle3]

        line4 = QFrame()
        line4.setFrameShape(QFrame.Shape.HLine)
        line4.setFrameShadow(QFrame.Shadow.Sunken)
        line4.setStyleSheet("border-top: 2px dashed #888888;")

        progress_layout.addWidget(line1, 2)
        progress_layout.addWidget(circle1)
        progress_layout.addWidget(line2, 3)
        progress_layout.addWidget(circle2)
        progress_layout.addWidget(line3, 3)
        progress_layout.addWidget(circle3)
        progress_layout.addWidget(line4, 2)

        self.main_layout.addLayout(progress_layout)

        # 实际消费行
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel('实际消费')
        label.setStyleSheet("font-size: 14px; color: #FFFFFF;")

        self.expense_spinbox = QDoubleSpinBox()
        self.expense_spinbox.setFixedWidth(150)
        self.expense_spinbox.setDecimals(2)
        self.expense_spinbox.setRange(-1e10, 1e10)
        self.expense_spinbox.valueChanged.connect(self.on_expense_changed)

        row_layout.addWidget(label)
        row_layout.addWidget(self.expense_spinbox)

        self.main_layout.addLayout(row_layout)

        # 目标行
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel('目标')
        label.setStyleSheet("font-size: 14px; color: #FFFFFF;")

        self.target_spinbox = QDoubleSpinBox()
        self.target_spinbox.setFixedWidth(150)
        self.target_spinbox.setDecimals(2)
        self.target_spinbox.setRange(-1e10, 1e10)
        self.target_spinbox.valueChanged.connect(self.on_target_changed)

        row_layout.addWidget(label)
        row_layout.addWidget(self.target_spinbox)

        self.main_layout.addLayout(row_layout)

        self.load_data()
        self.update_target_spinbox_values()
        self.update_expense_spinbox_values()
        self.update_circle_colors()

        self.main_layout.addStretch()

    def load_data(self):
        """加载存储的数据"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        expenses_path = os.path.join(data_dir, 'expenses.json')

        if os.path.exists(expenses_path):
            with open(expenses_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.expenses = data.get('expenses', {})
                self.target = data.get('target', 0.0)

    def update_target_spinbox_values(self):
        """更新目标输入框数值"""
        with block_signals([self.target_spinbox]):
            self.target_spinbox.setValue(self.target)
        
    def update_expense_spinbox_values(self):
        """更新实际消费输入框数值"""
        date_selected = self.days[self.selected_circle]
        year = str(date_selected.year)
        month = str(date_selected.month)
        day = str(date_selected.day)
        
        with block_signals([self.expense_spinbox]):
            if year in self.expenses and month in self.expenses[year] and day in self.expenses[year][month]:
                self.expense_spinbox.setValue(self.expenses[year][month][day])
            else:
                self.expense_spinbox.setValue(0.0)

    def update_circle_color(self, circle_index):
        """
        根据对应日期的消费情况更新指定圆形的颜色
        
        Parameters:
            circle_index (int): 要更新颜色的圆形索引（0-2，对应前天、昨天、今天）
        """
        year = str(self.days[circle_index].year)
        month = str(self.days[circle_index].month)
        day = str(self.days[circle_index].day)
        
        if year in self.expenses and month in self.expenses[year] and day in self.expenses[year][month]:
            expense = self.expenses[year][month][day]
        else:
            expense = 0.0
        
        circle = self.circles[circle_index]
        is_selected = (circle_index == self.selected_circle)
        
        if expense <= self.target:
            if is_selected:
                circle.setStyleSheet("""
                    QPushButton {
                        border-radius: 20px; 
                        background-color: #008000;
                        border: 2px solid #00b000;
                    }
                    QPushButton:hover {
                        background-color: #00d000;
                        border: none;
                    }
                    QPushButton:pressed {
                        background-color: #006000;
                        border: none;
                    }
                """)
            else:
                circle.setStyleSheet("""
                    QPushButton {
                        border-radius: 20px; 
                        background-color: #008000;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #00d000;
                    }
                    QPushButton:pressed {
                        background-color: #006000;
                    }
                """)
        else:
            if is_selected:
                circle.setStyleSheet("""
                    QPushButton {
                        border-radius: 20px; 
                        background-color: #800000;
                        border: 2px solid #b00000;
                    }
                    QPushButton:hover {
                        background-color: #d00000;
                        border: none;
                    }
                    QPushButton:pressed {
                        background-color: #600000;
                        border: none;
                    }
                """)
            else:
                circle.setStyleSheet("""
                    QPushButton {
                        border-radius: 20px; 
                        background-color: #800000;
                        border: none;
                    }
                    QPushButton:hover {
                        background-color: #d00000;
                    }
                    QPushButton:pressed {
                        background-color: #600000;
                    }
                """)

    def update_circle_colors(self):
        """更新所有圆形的颜色"""
        for circle_index in range(3):
            self.update_circle_color(circle_index)

    def save_data(self):
        """保存数据到文件"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        expenses_path = os.path.join(data_dir, 'expenses.json')

        data = {
            'target': self.target,
            'expenses': self.expenses
        }
        
        with open(expenses_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def on_circle_clicked(self, index):
        """
        点击圆形时切换选中状态并更新输入框
        
        Parameters:
            index (int): 被点击的圆形索引（0-2，对应前天、昨天、今天）
        """
        old_index = self.selected_circle
        self.selected_circle = index
        self.update_expense_spinbox_values()
        self.update_circle_color(old_index)
        self.update_circle_color(index)

    def on_expense_changed(self, value):
        """
        实际消费变化时更新存储数据
        
        Parameters:
            value (float): 新的消费金额
        """
        date_selected = self.days[self.selected_circle]
        year = str(date_selected.year)
        month = str(date_selected.month)
        day = str(date_selected.day)
        
        if year not in self.expenses:
            self.expenses[year] = {}
        if month not in self.expenses[year]:
            self.expenses[year][month] = {}
        
        self.expenses[year][month][day] = value
        self.update_circle_color(self.selected_circle)
        self.save_data()

    def on_target_changed(self, value):
        """
        目标变化时更新存储数据
        
        Parameters:
            value (float): 新的目标金额
        """
        self.target = value
        self.update_circle_colors()
        self.save_data()


class FurinaWindow(BaseWindow):
    """芙芙伴学应用主窗口"""

    def __init__(self, parent=None):
        """
        初始化任务窗口

        Parameters:
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle('芙芙伴学')
        self.setWindowIcon(icon)
        self.setMinimumSize(600, 400)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.task_widget = TaskWidget(self)
        self.tab_widget.addTab(self.task_widget, '任务')

        self.expenses_widget = ExpensesWidget(self)
        self.tab_widget.addTab(self.expenses_widget, '流水')