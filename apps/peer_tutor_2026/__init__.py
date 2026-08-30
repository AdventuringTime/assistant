import base64
import json
import os
import threading

from PySide6.QtCore import (QBuffer, QEvent, QIODevice, QMetaObject, QObject,
                            Q_RETURN_ARG, Qt, QThread, QTimer, Signal, Slot)
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFrame, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QSpinBox,
                               QTabWidget, QVBoxLayout, QWidget)
from PySide6.QtGui import QIcon, QGuiApplication

from core.base_objects import BaseWindow, BaseDialog, DeleteButton
from core.functions import get_this_week, get_today, block_signals
import datetime
from math import floor


def get_icon():
    """获取窗口图标（惰性加载，避免无 GUI 环境导入模块时崩溃）"""
    return QIcon('apps/peer_tutor_2026/assets/icon.ico')


class TaskDataManager:
    """任务数据管理类，单例模式，管理所有周的任务数据"""

    _instance = None
    WEEK_START_DATE = datetime.datetime(2026, 5, 11, 4, 0, 0)  # 与 TaskWidget.WEEK_START_DATE 保持一致

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(TaskDataManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._tasks = {}  # {week_num: [tasks_list]}
        self.modified_weeks = set()  # 记录被修改的周
        self._initialized = True

    def get_current_week_num(self, dt=None):
        """
        计算当前周数

        Parameters:
            dt (datetime.datetime, optional): 输入的时间，默认使用当前时间

        Returns:
            int: 周数（从1开始）
        """
        return floor(get_this_week(dt=dt, start_date=self.WEEK_START_DATE)) + 1

    def inherit_tasks_from_last_week_if_not_exist(self, week):
        """
        如果指定周的任务数据不存在，则从上一周继承任务（重置完成次数）

        Parameters:
            week (int): 周数
        """
        data_dir = os.path.join(os.path.dirname(__file__), 'data', str(week))
        json_path = os.path.join(data_dir, 'tasks.json')

        if os.path.exists(json_path):
            return

        last_week_dir = os.path.join(os.path.dirname(__file__), 'data', str(week - 1))
        last_week_json_path = os.path.join(last_week_dir, 'tasks.json')
        if os.path.exists(last_week_json_path):
            os.makedirs(data_dir, exist_ok=True)
            with open(last_week_json_path, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            for task in tasks:
                task['completed'] = 0.0
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=4)

    def get_tasks(self, week):
        """
        获取指定周的任务数据
        
        Parameters:
            week (int): 周数
        """
        if week in self._tasks:
            return self._tasks[week]

        data_dir = os.path.join(os.path.dirname(__file__), 'data', str(week))
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            self._tasks[week] = []
            return self._tasks[week]

        with open(json_path, 'r', encoding='utf-8') as f:
            self._tasks[week] = json.load(f)
        return self._tasks[week]

    def save_tasks(self):
        """保存所有被修改过的周的任务数据"""
        for week in self.modified_weeks:
            if week in self._tasks:
                data_dir = os.path.join(os.path.dirname(__file__), 'data', str(week))
                os.makedirs(data_dir, exist_ok=True)
                json_path = os.path.join(data_dir, 'tasks.json')

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(self._tasks[week], f, ensure_ascii=False, indent=4)

        self.modified_weeks.clear()

    def mark_modified(self, week):
        """
        标记指定周的数据已被修改

        Parameters:
            week (int): 周数
        """
        self.modified_weeks.add(week)


class ExpensesDataManager:
    """流水数据管理类，单例模式，管理所有流水数据"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ExpensesDataManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 加载流水数据
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        expenses_path = os.path.join(data_dir, 'expenses.json')

        if os.path.exists(expenses_path):
            with open(expenses_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.expenses = data.get('expenses', {})
                self.target = data.get('target', 0.0)
        else:
            self.expenses = {}
            self.target = 0.0

        self._initialized = True

    def save_expenses_data(self):
        """保存流水数据"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)

        expenses_path = os.path.join(data_dir, 'expenses.json')

        data = {
            'target': self.target,
            'expenses': self.expenses
        }

        with open(expenses_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

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
        self.setWindowIcon(get_icon())
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
        self.weight_spin.setRange(0, 2147483647)
        if task:
            self.weight_spin.setValue(task.get('weight', 100))
        else:
            self.weight_spin.setValue(100)
        self.layout_.addWidget(self.weight_label)
        self.layout_.addWidget(self.weight_spin)

        self.button_layout = QHBoxLayout()

        self.button_layout.addStretch()

        if task:
            self.delete_button = DeleteButton('删除')
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
            if self.completed == 0.0:
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
        通过输入对话框修改完成数量，仅响应鼠标左键点击

        Parameters:
            event (QMouseEvent): 鼠标点击事件
        """
        if event.button() != Qt.MouseButton.LeftButton:
            return
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

    WEEK_START_DATE = datetime.datetime(2026, 5, 11, 4, 0, 0)
    TARGET_DATE = datetime.datetime(2026, 12, 21, 4, 0, 0)
    TARGET_WEEK = floor(get_this_week(dt=TARGET_DATE, start_date=WEEK_START_DATE)) + 1  # 目标日期所在周

    def __init__(self, parent=None):
        super().__init__(parent)

        self.this_week_num = floor(get_this_week(
            start_date=TaskWidget.WEEK_START_DATE)) + 1
        self.week_displayed = self.this_week_num
        self.is_showing_this_week = True
        self.data_manager = TaskDataManager()
        self.task_items = []

        self.data_manager.inherit_tasks_from_last_week_if_not_exist(self.this_week_num)

        self.main_layout = QVBoxLayout(self)

        self.header = QLabel()
        self.header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        self.header.setMargin(5)
        self.main_layout.addWidget(self.header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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

        self.main_layout.addLayout(self.button_layout)

        self.load_and_display_tasks()

    def update_total_progress(self):
        """更新加权总进度显示"""
        total_percent = 0
        total_weight = 0
        if self.task_items:
            for task in self.task_items:
                weight = task.task.get('weight', 100)
                total_percent += task.progress_percent * weight
                total_weight += weight

            if total_weight > 0:
                total_percent = total_percent / total_weight
            else:
                total_percent = 100

        progress_value = int(total_percent)
        if progress_value < 0:
            progress_value = 0
        elif progress_value > 100:
            progress_value = 100
        self.total_progress_bar.setValue(progress_value)
        self.total_progress_label.setText(f'{int(total_percent)}%')

    def on_task_updated(self):
        """任务更新处理，标记数据已修改并更新总进度"""
        self.data_manager.mark_modified(self.week_displayed)
        self.update_total_progress()

    def on_task_deleted(self):
        """任务删除处理"""
        sender = self.sender()
        if sender in self.task_items:
            index = self.task_items.index(sender)
            self.task_items.remove(sender)
            self.data_manager.get_tasks(self.week_displayed).pop(index)
            sender.deleteLater()
            self.data_manager.mark_modified(self.week_displayed)
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
            self.data_manager.get_tasks(self.week_displayed).append(data)
            task_item = TaskItem(data)
            task_item.task_updated.connect(self.on_task_updated)
            task_item.task_deleted.connect(self.on_task_deleted)
            self.task_items.append(task_item)
            self.content_layout.insertWidget(len(self.task_items) - 1, task_item)
            self.data_manager.mark_modified(self.week_displayed)
            self.update_total_progress()

    @staticmethod
    def get_weeks_left(today=None):
        """
        计算距离目标日期还剩几周

        Parameters:
            today (datetime.datetime, optional): 起始时间，默认使用当前时间

        Returns:
            int: 剩余周数（目标所在周 - 当前所在周）
        """
        if today is None:
            today = datetime.datetime.now()
        current_week = floor(get_this_week(
            dt=today, start_date=TaskWidget.WEEK_START_DATE)) + 1
        return TaskWidget.TARGET_WEEK - current_week

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
        tasks = self.data_manager.get_tasks(self.week_displayed)
        for task in tasks:
            task_item = TaskItem(task)
            task_item.task_updated.connect(self.on_task_updated)
            task_item.task_deleted.connect(self.on_task_deleted)
            self.task_items.append(task_item)
            self.content_layout.insertWidget(len(self.task_items) - 1, task_item)
        weeks_left = self.get_weeks_left()
        if weeks_left > 0:
            self.header.setText(f'距离考研还有{weeks_left}周')
        else:
            self.header.setText(f'考研已过{-weeks_left}周')
        self.update_total_progress()

    def get_content_height(self):
        """
        获取任务列表内容所需的总高度

        Returns:
            int: 所有任务项的总高度（像素）
        """
        return self.content_widget.sizeHint().height()


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

        self.data_manager = ExpensesDataManager()

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
        circle1.setStyleSheet("border-radius: 20px; background-color: gray; color: white;")
        circle1.setText(str(self.days[0].day))
        font1 = circle1.font()
        font1.setPointSize(12)
        circle1.setFont(font1)
        circle1.clicked.connect(lambda: self.on_circle_clicked(0))

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)

        circle2 = QPushButton()
        circle2.setFixedSize(40, 40)
        circle2.setStyleSheet("border-radius: 20px; background-color: gray; color: white;")
        circle2.setText(str(self.days[1].day))
        font2 = circle2.font()
        font2.setPointSize(12)
        circle2.setFont(font2)
        circle2.clicked.connect(lambda: self.on_circle_clicked(1))

        line3 = QFrame()
        line3.setFrameShape(QFrame.Shape.HLine)
        line3.setFrameShadow(QFrame.Shadow.Sunken)

        circle3 = QPushButton()
        circle3.setFixedSize(40, 40)
        circle3.setStyleSheet("border-radius: 20px; background-color: gray; color: white;")
        circle3.setText(str(self.days[2].day))
        font3 = circle3.font()
        font3.setPointSize(12)
        circle3.setFont(font3)
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
        self.expense_spinbox.installEventFilter(self)

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
        self.target_spinbox.installEventFilter(self)

        row_layout.addWidget(label)
        row_layout.addWidget(self.target_spinbox)

        self.main_layout.addLayout(row_layout)

        self.update_target_spinbox_values()
        self.update_expense_spinbox_values()
        self.update_circle_colors()

        self.main_layout.addStretch()

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
            if obj == self.expense_spinbox:
                QTimer.singleShot(0, self.expense_spinbox.selectAll)
            elif obj == self.target_spinbox:
                QTimer.singleShot(0, self.target_spinbox.selectAll)
        return super().eventFilter(obj, event)

    def update_target_spinbox_values(self):
        """更新目标输入框数值"""
        with block_signals([self.target_spinbox]):
            self.target_spinbox.setValue(self.data_manager.target)

    def update_expense_spinbox_values(self):
        """更新实际消费输入框数值"""
        date_selected = self.days[self.selected_circle]
        year = str(date_selected.year)
        month = str(date_selected.month)
        day = str(date_selected.day)

        with block_signals([self.expense_spinbox]):
            if (year in self.data_manager.expenses
                and month in self.data_manager.expenses[year]
                and day in self.data_manager.expenses[year][month]
            ):
                self.expense_spinbox.setValue(self.data_manager.expenses[year][month][day])
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

        if (year in self.data_manager.expenses
            and month in self.data_manager.expenses[year]
            and day in self.data_manager.expenses[year][month]
        ):
            expense = self.data_manager.expenses[year][month][day]
        else:
            expense = 0.0

        circle = self.circles[circle_index]
        is_selected = (circle_index == self.selected_circle)

        if expense <= self.data_manager.target:
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

        if year not in self.data_manager.expenses:
            self.data_manager.expenses[year] = {}
        if month not in self.data_manager.expenses[year]:
            self.data_manager.expenses[year][month] = {}

        self.data_manager.expenses[year][month][day] = value
        self.update_circle_color(self.selected_circle)

    def on_target_changed(self, value):
        """
        目标变化时更新存储数据

        Parameters:
            value (float): 新的目标金额
        """
        self.data_manager.target = value
        self.update_circle_colors()


class FurinaWindow(BaseWindow):
    """芙芙伴学应用主窗口"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is not None:
            if cls._instance.isMinimized():
                cls._instance.showNormal()
            cls._instance.raise_()
            cls._instance.activateWindow()
            return cls._instance
        return super().__new__(cls)

    def __init__(self, parent=None):
        """
        初始化任务窗口

        Parameters:
            parent (QWidget, optional): 父窗口
        """
        if FurinaWindow._initialized:
            return
        super().__init__(parent)
        self.setWindowTitle('芙芙伴学')
        self.setWindowIcon(get_icon())
        self.setMinimumSize(600, 400)
        self._size_fitted = False  # 是否已按任务数量调整过窗口大小

        # self.tab_widget = QTabWidget()
        # self.setCentralWidget(self.tab_widget)
        #
        # self.task_widget = TaskWidget(self)
        # self.tab_widget.addTab(self.task_widget, '任务')
        #
        # self.expenses_widget = ExpensesWidget(self)
        # self.tab_widget.addTab(self.expenses_widget, '流水')

        self.task_widget = TaskWidget(self)
        self.setCentralWidget(self.task_widget)
        FurinaWindow._instance = self
        FurinaWindow._initialized = True

    def showEvent(self, event):
        """
        窗口显示事件，首次显示时根据任务数量动态调整窗口大小
        并将窗口移动到屏幕高度 5% 的位置

        Parameters:
            event (QShowEvent): 显示事件
        """
        if not self._size_fitted:
            self._size_fitted = True
            self._fit_size_to_tasks()
            self._move_to_screen_top()
        super().showEvent(event)

    def _move_to_screen_top(self):
        """
        将窗口移动到屏幕高度 5% 的位置（水平位置保持默认）

        说明:
            - 使用屏幕可用区域计算目标 y 坐标
            - 仅在窗口首次显示时调用，避免覆盖用户手动拖动的位置
        """
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            screen_height = screen.availableGeometry().height()
            self.move(self.x(), int(screen_height * 0.05))

    def _fit_size_to_tasks(self):
        """
        根据当前任务数量动态调整窗口高度，使默认大小能容纳所有任务项

        说明:
            - 高度由任务项实际尺寸动态计算，任务数量变化时无需修改代码
            - 窗口高度不低于 minimumSize 的最小高度限制
            - 窗口高度不超过屏幕可用高度的 90%，防止任务过多时超出屏幕
        """
        content_height = self.task_widget.get_content_height()
        other_height = self.height() - self.task_widget.scroll_area.viewport().height()
        new_height = other_height + content_height
        new_height = max(new_height, self.minimumHeight())
        screen = self.screen()
        if screen is not None:
            screen_height = screen.availableGeometry().height()
            new_height = min(new_height, int(screen_height * 0.9))
        self.resize(self.width(), new_height)

    def closeEvent(self, event):
        """
        关闭窗口时保存所有数据

        Parameters:
            event (QCloseEvent): 关闭事件
        """
        TaskDataManager().save_tasks()
        ExpensesDataManager().save_expenses_data()
        super().closeEvent(event)
        FurinaWindow._instance = None
        FurinaWindow._initialized = False


def _grab_window_pixmap():
    """
    截取芙芙伴学主窗口并返回 QPixmap（窗口无需打开，不复制到剪贴板）

    说明:
        - 窗口未创建时在后台创建实例渲染截图，完成后关闭实例
        - 窗口已存在时直接截取现有窗口，不改变其显示状态
        - 截图前临时调整滚动区域最小高度，确保所有任务项都包含在截图中
        - 必须由 GUI 主线程调用

    Returns:
        QPixmap: 窗口截图
    """
    is_new = FurinaWindow._instance is None
    window = FurinaWindow() if is_new else FurinaWindow._instance
    scroll_area = window.task_widget.scroll_area
    original_min_height = scroll_area.minimumHeight()
    try:
        content_height = window.task_widget.get_content_height()
        scroll_margin = scroll_area.frameWidth() * 2
        scroll_area.setMinimumHeight(content_height + scroll_margin)
        target_height = max(window.minimumSizeHint().height(),
                            window.minimumHeight())
        window.resize(window.width(), target_height)
        window.layout().activate()
        QApplication.processEvents()
        return window.grab()
    finally:
        scroll_area.setMinimumHeight(original_min_height)
        if is_new:
            window.close()


def capture_window_screenshot():
    """
    截取芙芙伴学主窗口截图并复制到剪贴板（窗口无需打开）

    说明:
        - 需在 GUI 主线程调用（如主页通知点击），复制结果到剪贴板
    """
    QApplication.clipboard().setPixmap(_grab_window_pixmap())


class ScreenshotBridge(QObject):
    """跨线程截图桥（单例），供后台线程安全获取主线程渲染的窗口截图"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        # 无论实例在哪创建，都移入 GUI 主线程，确保截图在事件循环中执行
        self.moveToThread(QApplication.instance().thread())
        self._initialized = True

    @Slot(result=str)
    def _grab_base64(self):
        """在主线程执行的槽：截取窗口并返回 base64 编码的 PNG 数据"""
        pixmap = _grab_window_pixmap()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, 'PNG')
        return base64.b64encode(bytes(buffer.data())).decode('ascii')


def get_window_screenshot_bytes() -> bytes:
    """
    截取芙芙伴学主窗口截图，返回 PNG 图片字节数据

    Returns:
        bytes: PNG 格式的图片数据
    """
    app = QApplication.instance()
    if app is None:
        raise RuntimeError('QApplication 未创建，无法截取窗口')
    if QThread.currentThread() is app.thread():
        return base64.b64decode(ScreenshotBridge()._grab_base64())
    result = QMetaObject.invokeMethod(
        ScreenshotBridge(),
        '_grab_base64',
        Qt.ConnectionType.BlockingQueuedConnection,
        Q_RETURN_ARG(str),
    )
    if result is None:
        raise RuntimeError('截图请求未能派发到主线程执行')
    return base64.b64decode(result)