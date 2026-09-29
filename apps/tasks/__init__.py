import sys
import json
import os
import re
from PySide6.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout,
                               QScrollArea, QHBoxLayout, QInputDialog, QPushButton,
                               QLineEdit, QDoubleSpinBox, QMessageBox, QSpinBox,
                               QTextEdit, QSizePolicy, QListWidget, QDialog, QComboBox,
                               QDateEdit, QCheckBox)
from PySide6.QtCore import Qt, Signal, QEvent, QTimer, QUrl, QDate


def _get_unique_task_name(name, existing_names):
    """
    生成唯一的任务名，避免与已有未完成任务重复

    规则：
    - 如果任务名已存在且是 -N 格式（如 task-1），先尝试移除 -N 后缀
    - 如果仍重复或不是 -N 格式，依次尝试添加 -1、-2 等后缀

    Parameters:
        name (str): 原始任务名
        existing_names (set): 已有任务名集合

    Returns:
        str: 唯一的任务名
    """
    if name not in existing_names:
        return name

    # 尝试移除 -N 后缀（如果任务名本来就是 -N 格式）
    match = re.match(r'^(.*)-(\d+)$', name)
    if match:
        base_name = match.group(1)
        if base_name not in existing_names:
            return base_name
        # 从 base_name 开始尝试加后缀
        name = base_name

    # 依次尝试添加 -1、-2 等后缀
    counter = 1
    while True:
        new_name = f"{name}-{counter}"
        if new_name not in existing_names:
            return new_name
        counter += 1


from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtGui import QDesktopServices

from core.base_objects import BaseWindow, BaseDialog, DeleteButton
from core.functions import get_today
from core.settings_manager import SettingsManager


def _hex_to_rgb(hex_color):
    """
    将十六进制颜色值转换为RGB元组

    Parameters:
        hex_color (str): 十六进制颜色值，如 "#FFCC00"

    Returns:
        tuple: (r, g, b) 形式的RGB值
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_subtasks_first_line(task):
    """
    获取子任务的第一行文本，兼容新旧字段（description和subtasks）

    Parameters:
        task (dict): 任务数据字典

    Returns:
        str: 子任务的第一行文本
    """
    subtasks = task.get('subtasks', task.get('description', ''))
    if subtasks:
        # 只返回第一行
        return subtasks.split('\n')[0].strip()
    return ''


class SortDialog(BaseDialog):
    """排序对话框，支持拖拽排序任务列表"""

    def __init__(self, parent, names, title="排序"):
        """
        初始化排序对话框

        Parameters:
            parent (QWidget): 父窗口
            names (list): 待排序的任务名列表
            title (str, optional): 对话框标题，默认为"排序"
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.names = names

        layout = QVBoxLayout(self)

        # 创建可拖拽排序的列表
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        layout.addWidget(self.list_widget)

        # 添加任务名称到列表
        for name in self.names:
            self.list_widget.addItem(name)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

        self.result = None

    def accept(self):
        """确认排序，按列表顺序返回任务名"""
        self.result = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        super().accept()

    def reject(self):
        """取消排序，返回None"""
        self.result = None
        super().reject()


class TaskDialog(BaseDialog):
    """任务编辑对话框，支持创建、编辑、复制和删除任务"""

    on_save_signal = Signal(dict)      # 保存任务信号
    on_save_copy_signal = Signal(dict) # 保存副本信号
    on_delete_signal = Signal()        # 删除任务信号

    def __init__(self, task=None, name='', parent=None):
        """
        初始化任务编辑对话框

        Parameters:
            task (dict, optional): 待编辑的任务数据，None表示新建任务
            name (str, optional): 待编辑的任务名，默认为空
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.task = task
        self.setWindowTitle('任务')
        self.setModal(True)

        self.layout_ = QVBoxLayout(self)

        # 任务名称
        self.name_label = QLabel('任务名称:')
        self.name_edit = QLineEdit()
        if name:
            self.name_edit.setText(name)
        self.layout_.addWidget(self.name_label)
        self.layout_.addWidget(self.name_edit)

        # 任务类型（支线/主线）
        self.type_label = QLabel('任务类型:')
        self.type_combo = QComboBox()
        self.type_combo.addItems(['支线', '主线'])
        if task:
            self.type_combo.setCurrentIndex(task.get('type', 0))
        self.layout_.addWidget(self.type_label)
        self.layout_.addWidget(self.type_combo)

        # 子任务
        self.subtasks_label = QLabel('子任务（每行一个）:')
        self.subtasks_edit = QTextEdit()
        self.subtasks_edit.setFixedHeight(80)
        if task:
            # 兼容旧字段
            self.subtasks_edit.setPlainText(task.get('subtasks', task.get('description', '')))
        self.layout_.addWidget(self.subtasks_label)
        self.layout_.addWidget(self.subtasks_edit)

        # 所需完成次数
        self.required_label = QLabel('所需次数:')
        self.required_spin = QDoubleSpinBox(decimals=2)
        self.required_spin.setRange(0.0, 1e15)
        if task:
            self.required_spin.setValue(task.get('required', 1.0))
        else:
            self.required_spin.setValue(1.0)
        self.layout_.addWidget(self.required_label)
        self.layout_.addWidget(self.required_spin)

        # 截止日期（可选）
        self.deadline_layout = QHBoxLayout()
        self.deadline_label = QLabel('截止日期（可选）:')
        self.deadline_checkbox = QCheckBox()
        self.deadline_edit = QDateEdit()
        self.deadline_edit.setDisplayFormat('yyyy-MM-dd')
        self.deadline_edit.setCalendarPopup(True)

        self.deadline_layout.addWidget(self.deadline_label)
        self.deadline_layout.addStretch()
        self.deadline_layout.addWidget(self.deadline_checkbox)
        self.layout_.addLayout(self.deadline_layout)
        self.layout_.addWidget(self.deadline_edit)

        self.deadline_edit.hide()

        if task:
            deadline = task.get('deadline')
            if deadline:
                self.deadline_checkbox.setChecked(True)
                self.deadline_edit.show()
                self.deadline_edit.setDate(QDate.fromString(deadline, 'yyyy-MM-dd'))
            else:
                today = get_today()
                self.deadline_edit.setDate(QDate(today.year, today.month, today.day))
        else:
            today = get_today()
            self.deadline_edit.setDate(QDate(today.year, today.month, today.day))
        self.deadline_checkbox.stateChanged.connect(self.on_deadline_checkbox_changed)

        # 预计完成日期（可选）
        self.estimated_time_layout = QHBoxLayout()
        self.estimated_time_label = QLabel('预计完成日期（可选）:')
        self.estimated_time_checkbox = QCheckBox()
        self.estimated_time_edit = QDateEdit()
        self.estimated_time_edit.setDisplayFormat('yyyy-MM-dd')
        self.estimated_time_edit.setCalendarPopup(True)

        self.estimated_time_layout.addWidget(self.estimated_time_label)
        self.estimated_time_layout.addStretch()
        self.estimated_time_layout.addWidget(self.estimated_time_checkbox)
        self.layout_.addLayout(self.estimated_time_layout)
        self.layout_.addWidget(self.estimated_time_edit)

        self.estimated_time_edit.hide()

        if task:
            estimated_time = task.get('estimated_time')
            if estimated_time:
                self.estimated_time_checkbox.setChecked(True)
                self.estimated_time_edit.show()
                self.estimated_time_edit.setDate(QDate.fromString(estimated_time, 'yyyy-MM-dd'))
            else:
                today = get_today()
                self.estimated_time_edit.setDate(QDate(today.year, today.month, today.day))
        else:
            today = get_today()
            self.estimated_time_edit.setDate(QDate(today.year, today.month, today.day))
        self.estimated_time_checkbox.stateChanged.connect(self.on_estimated_time_checkbox_changed)

        # 链接（支持文件路径转换）
        self.link_label = QLabel('链接:')
        self.link_edit = QLineEdit()
        if task:
            self.link_edit.setText(task.get('link', ''))

        self.link_layout = QHBoxLayout()
        self.link_layout.addWidget(self.link_edit)

        self.convert_button = QPushButton('识别路径')
        self.convert_button.clicked.connect(self.on_convert_path)
        self.link_layout.addWidget(self.convert_button)

        self.layout_.addWidget(self.link_label)
        self.layout_.addLayout(self.link_layout)

        # 按钮布局
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        # 编辑模式显示删除和保存副本按钮
        if task:
            self.delete_button = DeleteButton('删除')
            self.delete_button.clicked.connect(self.on_delete)
            self.button_layout.addWidget(self.delete_button)

            self.save_copy_button = QPushButton('保存副本')
            self.save_copy_button.clicked.connect(self.on_save_copy)
            self.button_layout.addWidget(self.save_copy_button)

        self.save_button = QPushButton('保存')
        self.save_button.clicked.connect(self.on_save)
        self.save_button.setDefault(True)
        self.button_layout.addWidget(self.save_button)

        self.layout_.addLayout(self.button_layout)

        # 安装事件过滤器，实现输入框聚焦时全选
        self.required_spin.installEventFilter(self)
        self.link_edit.installEventFilter(self)

    def on_save(self):
        """保存任务，发出保存信号并关闭对话框"""
        self.on_save_signal.emit(self.get_task_data())
        self.close()

    def on_save_copy(self):
        """保存任务副本，发出保存副本信号并关闭对话框"""
        self.on_save_copy_signal.emit(self.get_task_data())
        self.close()

    def on_delete(self):
        """删除任务，需用户确认"""
        reply = QMessageBox.question(self, '删除任务', '删除任务？',
                    QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            self.on_delete_signal.emit()
            self.close()

    def on_convert_path(self):
        """将文件路径转换为file://链接格式"""
        path = self.link_edit.text().strip()

        if ((not '://' in path) and  # 已经是链接则不转换
            ('\\' in path or '/' in path)):
            # 转换为file://链接
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            file_url = 'file://' + path
            self.link_edit.setText(file_url)

    def on_deadline_checkbox_changed(self, state):
        """处理截止日期复选框状态变化"""
        if state == 2:
            self.deadline_edit.show()
        elif state == 0:
            self.deadline_edit.hide()

    def on_estimated_time_checkbox_changed(self, state):
        """处理预计完成日期复选框状态变化"""
        if state == 2:
            self.estimated_time_edit.show()
        elif state == 0:
            self.estimated_time_edit.hide()

    def get_task_data(self):
        """
        获取当前表单中的任务数据

        Returns:
            dict: 任务数据字典
        """
        data = {
            'name': self.name_edit.text(),
            'type': self.type_combo.currentIndex(),
            'subtasks': self.subtasks_edit.toPlainText(),
            'completed': self.task.get('completed', 0.0) if self.task else 0.0,
            'required': self.required_spin.value()
        }
        if self.deadline_checkbox.isChecked():
            deadline = self.deadline_edit.date().toString('yyyy-MM-dd')
            data['deadline'] = deadline
        if self.estimated_time_checkbox.isChecked():
            estimated_time = self.estimated_time_edit.date().toString('yyyy-MM-dd')
            data['estimated_time'] = estimated_time
        link = self.link_edit.text().strip()
        if link:
            data['link'] = link
        return data

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
                QTimer.singleShot(0, self.on_select_all_required)
            elif obj == self.link_edit:
                QTimer.singleShot(0, self.on_select_all_link)
        return super().eventFilter(obj, event)

    def on_select_all_required(self):
        """延迟选择 required_spin 的全部内容"""
        try:
            if self.required_spin:
                self.required_spin.selectAll()
        except RuntimeError:
            # 控件已被删除，忽略
            pass

    def on_select_all_link(self):
        """延迟选择 link_edit 的全部内容"""
        try:
            if self.link_edit:
                self.link_edit.selectAll()
        except RuntimeError:
            # 控件已被删除，忽略
            pass


class TaskItem(QWidget):
    """任务项部件，显示单个任务的详细信息和操作按钮"""

    task_updated = Signal()           # 任务更新信号
    task_deleted = Signal()           # 任务删除信号
    task_copy_created = Signal(dict)  # 任务副本创建信号
    tracking_changed = Signal(str)    # 追踪状态改变信号
    task_completed = Signal(str)      # 任务完成信号
    task_saved = Signal(dict)         # 任务保存信号

    def __init__(self, task, name, is_tracking=False, is_completed=False, parent=None):
        """
        初始化任务项部件

        Parameters:
            task (dict): 任务数据字典
            name (str): 任务名
            is_tracking (bool, optional): 是否正在追踪，默认为False
            is_completed (bool, optional): 是否在已完成列表中，默认为False
            parent (QWidget, optional): 父控件
        """
        super().__init__(parent)
        self.task = task
        self.name = name
        self.is_tracking = is_tracking
        self.is_completed = is_completed
        self.task_type = task.get('type', 0)

        # 任务类型颜色：主线黄色，支线绿色
        self.color_main = '#FFCC00'
        self.color_branch = '#00CC66'
        if self.task_type == 0:
            self.current_color = self.color_branch
        elif self.task_type == 1:
            self.current_color = self.color_main

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # 主布局
        self.layout_ = QHBoxLayout(self)

        # 左侧颜色指示条
        self.line_widget = QWidget()
        self.line_widget.setFixedWidth(4)
        self.line_widget.setStyleSheet(f"background-color: {self.current_color};")
        self.layout_.addWidget(self.line_widget)

        # 内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        # 顶部布局（标题和按钮）
        self.top_layout = QHBoxLayout()

        self.name_label = QLabel(self.name)
        self.name_label.setWordWrap(True)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        font = QFont()
        font.setPointSize(14)
        self.name_label.setFont(font)
        # 已完成任务显示暗色
        if self.is_completed:
            self.name_label.setStyleSheet("color: #808080; text-decoration: line-through;")
        self.top_layout.addWidget(self.name_label)

        # 完成按钮（追踪模式下且满足条件时显示）
        self.complete_button = QPushButton('完成')
        self.complete_button.clicked.connect(self.on_complete_clicked)
        self.top_layout.addWidget(self.complete_button)

        # 前往按钮（追踪模式下显示）
        self.go_button = QPushButton('前往')
        self.go_button.clicked.connect(self.on_go_clicked)
        self.top_layout.addWidget(self.go_button)

        # 删除按钮（已完成任务显示）
        self.delete_button = DeleteButton('删除')
        self.delete_button.clicked.connect(self.delete_task)
        self.top_layout.addWidget(self.delete_button)

        # 编辑按钮
        self.edit_button = QPushButton('编辑')
        self.edit_button.clicked.connect(self.on_edit_clicked)
        self.top_layout.addWidget(self.edit_button)

        # 追踪按钮
        self.track_button = QPushButton('开始追踪' if not is_tracking else '停止追踪')
        self.track_button.clicked.connect(self.on_track_clicked)
        self.top_layout.addWidget(self.track_button)

        self.content_layout.addLayout(self.top_layout)

        # 子任务（显示第一行）
        self.subtask_label = QLabel(get_subtasks_first_line(self.task))
        self.subtask_label.setWordWrap(True)
        self.subtask_label.setStyleSheet("font-size: 15px; color: #808080;")
        self.content_layout.addWidget(self.subtask_label)

        # 截止日期（如果有）
        self.deadline_label = QLabel()
        self.deadline_label.setWordWrap(True)
        self.deadline_label.setStyleSheet("font-size: 15px; color: #808080;")
        self.content_layout.addWidget(self.deadline_label)

        # 预计完成日期（如果有）
        self.estimated_time_label = QLabel()
        self.estimated_time_label.setWordWrap(True)
        self.estimated_time_label.setStyleSheet("font-size: 15px; color: #808080;")
        self.content_layout.addWidget(self.estimated_time_label)

        # 进度信息
        self.completed = self.task.get('completed', 0.0)
        self.required = self.task.get('required', 1.0)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(20)

        # 进度标签
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-size: 14px; color: #808080;")

        # 进度区域（可点击修改进度）
        self.progress_widget = QWidget()
        self.progress_widget.setObjectName('progress_widget')
        self.progress_layout = QHBoxLayout(self.progress_widget)
        self.progress_layout.addWidget(self.progress_bar)
        self.progress_layout.addWidget(self.progress_label)

        self.progress_widget.setStyleSheet("""
            #progress_widget:hover {
                background-color: rgba(255, 255, 255, 0.03);
            }
        """)
        self.progress_widget.mousePressEvent = self.set_completed_from_input

        self.content_layout.addWidget(self.progress_widget)
        self.layout_.addWidget(self.content_widget)

        # 集中初始化各组件数值和可见性等状态，避免窗口闪烁
        self.update_style()
        self.update_progress_percent()
        self.update_buttons_visibility()
        if not self.subtask_label.text():
            self.subtask_label.hide()

        deadline = self.task.get('deadline')
        if deadline:
            self.deadline_label.setText(f'截止日期: {deadline}')
        else:
            self.deadline_label.hide()

        estimated_time = self.task.get('estimated_time')
        if estimated_time:
            self.estimated_time_label.setText(f'预计完成日期: {estimated_time}')
        else:
            self.estimated_time_label.hide()

    def update_style(self):
        """根据追踪状态更新样式"""
        if self.is_tracking:
            r, g, b = _hex_to_rgb(self.current_color)
            self.setStyleSheet(f"""
                TaskItem {{
                    background-color: rgba({r}, {g}, {b}, 0.25);
                }}
            """)
        else:
            self.setStyleSheet("")

    def update_buttons_visibility(self):
        """更新按钮可见性"""
        required = self.task.get('required')
        completed = self.task.get('completed')
        self.complete_button.setVisible(self.is_tracking and not self.is_completed and (required <= 0 or completed >= required))
        self.go_button.setVisible(self.is_tracking and bool(self.task.get('link')))
        self.delete_button.setVisible(self.is_completed)

    def set_tracking(self, is_tracking):
        """
        设置追踪状态

        Parameters:
            is_tracking (bool): 是否追踪
        """
        self.is_tracking = is_tracking
        if is_tracking:
            self.track_button.setText('停止追踪')
        else:
            self.track_button.setText('开始追踪')
        self.update_style()
        self.update_buttons_visibility()

    def on_complete_clicked(self):
        """触发任务完成信号"""
        self.task_completed.emit(self.name)

    def on_go_clicked(self):
        """打开任务关联的链接"""
        link = self.task.get('link', '')
        if not link:
            return
        url = QUrl(link)
        QDesktopServices.openUrl(url)

    def on_track_clicked(self):
        """触发追踪状态改变信号"""
        self.tracking_changed.emit(self.name)

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

        # 确保进度值在有效范围内
        progress_value = int(self.progress_percent)
        if progress_value < 0:
            progress_value = 0
        elif progress_value > 100:
            progress_value = 100
        self.progress_bar.setValue(progress_value)

    def set_completed_from_input(self, event=None):
        """通过输入对话框修改完成数量，仅响应鼠标左键点击"""
        if event is not None and event.button() != Qt.MouseButton.LeftButton:
            return
        self.completed, ok = QInputDialog.getDouble(self, '修改进度',
            f'请输入完成数量:',
            value=self.completed,
            decimals=2)

        if ok:
            self.task['completed'] = self.completed
            self.update_progress_percent()
            self.update_buttons_visibility()
            self.task_updated.emit()

    def on_edit_clicked(self, event):
        """打开任务编辑对话框"""
        dialog = TaskDialog(self.task, self.name, self)
        dialog.on_save_signal.connect(self.on_dialog_save)
        dialog.on_save_copy_signal.connect(self.on_dialog_save_copy)
        dialog.on_delete_signal.connect(self.delete_task)
        dialog.show()

    def on_dialog_save_copy(self, data):
        """处理保存副本操作"""
        self.task_copy_created.emit(data)

    def delete_task(self):
        """删除任务"""
        self.task_deleted.emit()

    def on_dialog_save(self, data):
        """处理保存操作，把任务数据交给任务窗口"""
        self.task_saved.emit(data)


class TaskDataManager:
    """任务数据管理类，单例模式，管理所有任务数据"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(TaskDataManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.tasks = {}
        self.todo_names = []
        self.completed_names = []
        self.tracking_task_name = None
        self._initialized = True
        self.load_tasks()

    @staticmethod
    def _repair_names(task_dict, todo_names, completed_names):
        """
        修正顺序列表与任务数据不一致的情况

        任务数据中有、顺序列表中没有的任务追加到未完成顺序列表尾部；
        顺序列表中有、任务数据中没有的任务名从顺序列表中移除；
        同时存在于两个顺序列表中的任务名只保留在未完成顺序列表

        Parameters:
            task_dict (dict): 以任务名为键的任务数据
            todo_names (list): 未完成任务的顺序列表
            completed_names (list): 已完成任务的顺序列表

        Returns:
            tuple: 修正后的 (未完成顺序列表, 已完成顺序列表)
        """
        listed_names = set(todo_names) | set(completed_names)
        todo_names = todo_names + [name for name in task_dict if name not in listed_names]
        todo_names = [name for name in todo_names if name in task_dict]
        completed_names = [name for name in completed_names
                           if name in task_dict and name not in set(todo_names)]
        return todo_names, completed_names

    def replace_task(self, old_name, new_name, data):
        """
        替换任务：删除原任务及其数据，以新任务名写入新任务数据

        顺序列表中的位置、所在列表（未完成或已完成）与追踪任务名保持一致

        Parameters:
            old_name (str): 原任务名
            new_name (str): 新任务名
            data (dict): 新的任务数据
        """
        if self.tasks.pop(old_name) is None:
            return

        self.tasks[new_name] = data

        for names in (self.todo_names, self.completed_names):
            if old_name in names:
                names[names.index(old_name)] = new_name
                break

        if self.tracking_task_name == old_name:
            self.tracking_task_name = new_name

    def remove_task(self, name):
        """
        按任务名删除任务（未完成或已完成），若追踪该任务则同时停止追踪

        Parameters:
            name (str): 任务名
        """
        if self.tasks.pop(name, None) is None:
            return

        for names in (self.todo_names, self.completed_names):
            if name in names:
                names.remove(name)
                break

        if self.tracking_task_name == name:
            self.tracking_task_name = None

    def load_tasks(self):
        """从文件加载任务数据"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.tasks = data.get('tasks', {})
        self.todo_names, self.completed_names = self._repair_names(
            self.tasks, data.get('todo_names', []), data.get('completed_names', []))
        self.tracking_task_name = data.get('tracking_task_name', None)

    def save_tasks(self):
        """保存任务数据到文件"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        json_path = os.path.join(data_dir, 'tasks.json')

        data = {
            'tasks': self.tasks,
            'todo_names': self.todo_names,
            'completed_names': self.completed_names,
            'tracking_task_name': self.tracking_task_name
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

_data_manager = TaskDataManager()


class FloatingWidget(QWidget):
    """悬浮窗口部件，显示当前追踪任务的进度信息"""

    clicked = Signal()  # 点击信号

    def __init__(self, parent=None):
        """
        初始化悬浮窗口

        Parameters:
            parent (QWidget, optional): 父控件
        """
        super().__init__(parent)
        # 设置窗口标志：无边框、始终在底部、工具窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                           Qt.WindowType.WindowStaysOnBottomHint |
                           Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._settings = SettingsManager()

        # 在不启用点击设置完成次数时，穿透点击
        if not self._settings.get_value("tasks.floating_widget.click_to_set_completed", True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowTransparentForInput)

        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)

        # 背景部件
        self.background_widget = QWidget()
        self.background_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.background_widget.setObjectName("FloatingBackground")

        self.content_layout = QVBoxLayout(self.background_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 24)

        # 标题标签（任务名称和进度）
        self.top_label = QLabel()
        self.top_label.setStyleSheet("font-size: 36px; color: #FFFFFF;")
        self.top_label.setWordWrap(True)
        self.content_layout.addWidget(self.top_label)

        # 描述标签
        self.bottom_label = QLabel()
        self.bottom_label.setStyleSheet("font-size: 24px; color: #DDDDDD;")
        self.bottom_label.setWordWrap(True)
        self.content_layout.addWidget(self.bottom_label)

        self.layout_.addWidget(self.background_widget)
        self.adjustSize()

    def mousePressEvent(self, event):
        """点击悬浮窗口时发出信号"""
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_content(self, name, completed, required, subtask, color):
        """
        设置悬浮窗口的内容

        Parameters:
            name (str): 任务名称
            completed (float): 已完成数量
            required (float): 所需数量
            subtask (str): 当前子任务
            color (str): 任务类型颜色（十六进制）
        """
        # 计算进度文本
        if required == 0.0:
            progress_text = '(已完成)'
        elif required == 1.0:
            if completed == 0.0:
                progress_text = ''
            elif completed == 1.0:
                progress_text = '(已完成)'
            else:
                progress_text = f'({completed * 100:g}%)'
        else:
            progress_text = f'({completed}/{required})'

        self.top_label.setText(f"{name}{progress_text}")
        self.bottom_label.setText(subtask)
        self.bottom_label.setVisible(bool(subtask.strip()))

        # 设置背景颜色
        r, g, b = _hex_to_rgb(color)
        self.background_widget.setStyleSheet(f"""
            #FloatingBackground {{
                background-color: rgba({r}, {g}, {b}, 0.5);
            }}
        """)
        self.adjustSize()


class TaskWindow(BaseWindow):
    """任务管理窗口，提供任务列表的查看、编辑、排序和追踪功能"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
    # 只要实例存在，就激活并返回该实例（无论是否最小化或可见）
        if cls._instance is not None:
            # 如果窗口最小化，恢复正常状态
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
        # 避免重复初始化
        if TaskWindow._initialized:
            return
        super().__init__(parent)

        self.setWindowTitle('任务')
        self.setMinimumSize(600, 400)
        self.resize(1000, 800)

        self.data_manager = _data_manager
        self.floating_widget = None

        # 主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 标题
        self.header = QLabel('任务')
        self.header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        self.header.setMargin(5)
        self.main_layout.addWidget(self.header)

        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        self.task_items = {}
        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)

        # 按钮布局
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        self.sort_button = QPushButton("排序")
        self.sort_button.clicked.connect(self.open_sort_dialog)
        self.button_layout.addWidget(self.sort_button)

        self.add_button = QPushButton('添加任务')
        self.add_button.clicked.connect(self.on_add_task)
        self.button_layout.addWidget(self.add_button)

        self.main_layout.addLayout(self.button_layout)

        # 初始化UI和悬浮窗口
        self.refresh_ui()
        self.update_floating_widget()
        TaskWindow._instance = self
        TaskWindow._initialized = True

    def open_sort_dialog(self):
        """打开任务排序对话框"""
        if not self.data_manager.todo_names:
            return

        dialog = SortDialog(self, self.data_manager.todo_names, "排序")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data_manager.todo_names = dialog.result
            self.refresh_ui()

    def _create_task_item(self, task, name, is_tracking=False, is_completed=False):
        """
        创建任务项并连接信号

        Parameters:
            task (dict): 任务数据
            name (str): 任务名
            is_tracking (bool, optional): 是否正在追踪该任务，默认False
            is_completed (bool, optional): 是否已完成该任务，默认False
        """
        task_item = TaskItem(task, name, is_tracking, is_completed)
        task_item.task_updated.connect(self.on_task_updated)
        task_item.task_saved.connect(self.on_task_saved)
        task_item.task_deleted.connect(self.on_task_deleted)
        task_item.task_copy_created.connect(self.on_creation_via_dialog)
        task_item.tracking_changed.connect(self.on_tracking_changed)
        task_item.task_completed.connect(self.on_task_completed)
        self.task_items[name] = task_item
        self.content_layout.insertWidget(len(self.task_items) - 1, task_item)

    def refresh_ui(self):
        """刷新任务列表UI"""
        # 清除现有任务项
        for task_item in self.task_items.values():
            task_item.deleteLater()
        self.task_items.clear()

        # 显示待办任务
        for name in self.data_manager.todo_names:
            is_tracking = (self.data_manager.tracking_task_name == name)
            self._create_task_item(self.data_manager.tasks[name], name, is_tracking, False)

        # 显示已完成任务（在待办任务后面）
        for name in self.data_manager.completed_names:
            is_tracking = (self.data_manager.tracking_task_name == name)
            self._create_task_item(self.data_manager.tasks[name], name, is_tracking, True)

    def on_task_updated(self):
        """任务更新后的处理"""
        self.update_floating_widget()

    def on_task_deleted(self):
        """任务删除后的处理"""
        sender = self.sender()
        if sender.name in self.task_items:
            self.data_manager.remove_task(sender.name)
            self.refresh_ui()
            self.update_floating_widget()

    def _get_task_name(self, name, old_name=None):
        """
        规范化任务名并与所有任务去重

        Parameters:
            name (str): 待处理的任务名，为空时使用"未命名任务"
            old_name (str, optional): 原任务名，不参与去重，默认为None

        Returns:
            str: 唯一任务名
        """
        existing_names = set(self.data_manager.tasks)
        if old_name is not None:
            existing_names.discard(old_name)
        return _get_unique_task_name(name.strip() or '未命名任务', existing_names)

    def on_task_saved(self, data):
        """
        任务编辑保存后的处理

        Parameters:
            data (dict): 任务数据
        """
        old_name = self.sender().name
        name = self._get_task_name(data.pop('name', ''), old_name)

        self.data_manager.replace_task(old_name, name, data)

        self.refresh_ui()
        self.update_floating_widget()

    def on_task_completed(self, name):
        """
        任务完成后的处理

        Parameters:
            name (str): 任务名
        """
        task = self.data_manager.tasks[name]

        # 已完成任务的任务名加上"-已完成"后缀并与所有任务去重
        completed_name = _get_unique_task_name(f"{name}-已完成", set(self.data_manager.tasks))
        completed_task = dict(task)
        self.data_manager.tasks[completed_name] = completed_task
        self.data_manager.completed_names.append(completed_name)

        # 获取子任务内容
        subtasks = task.get('subtasks', task.get('description', ''))
        lines = [line.strip() for line in subtasks.split('\n') if line.strip()]

        if len(lines) > 1:
            # 子任务不仅一行，移除第一行
            remaining_lines = lines[1:]
            task['subtasks'] = '\n'.join(remaining_lines)
            task['completed'] = 0.0
            task['required'] = 1.0
        else:
            # 子任务只有一行或没有，删除此任务
            self.data_manager.remove_task(name)

        # 重新加载列表
        self.refresh_ui()
        self.update_floating_widget()

    def on_add_task(self):
        """打开添加任务对话框"""
        dialog = TaskDialog(parent=self)
        dialog.on_save_signal.connect(self.on_creation_via_dialog)
        dialog.show()

    def on_creation_via_dialog(self, data):
        """
        通过对话框创建新任务

        Parameters:
            data (dict): 任务数据
        """
        name = self._get_task_name(data.pop('name', ''))
        self.data_manager.tasks[name] = data
        self.data_manager.todo_names.append(name)

        self.refresh_ui()

    def update_floating_widget(self):
        """更新悬浮窗口显示当前追踪任务"""
        name = self.data_manager.tracking_task_name
        if name in self.data_manager.tasks:
            task = self.data_manager.tasks[name]

            task_type = task.get('type', 0)
            color = '#00CC66' if task_type == 0 else '#FFCC00'

            completed = task.get('completed', 0.0)
            required = task.get('required', 1.0)
            subtask = get_subtasks_first_line(task)

            if not self.floating_widget:
                self.floating_widget = FloatingWidget()
                self.floating_widget.clicked.connect(self.on_floating_clicked)

            self.floating_widget.set_content(name, completed, required, subtask, color)
            self.set_floating_position()
            self.floating_widget.show()
        else:
            if self.floating_widget:
                self.floating_widget.hide()

    def on_floating_clicked(self):
        """悬浮窗口点击处理，打开进度修改对话框"""
        item = self.task_items.get(self.data_manager.tracking_task_name)
        if item:
            item.set_completed_from_input()

    def set_floating_position(self):
        """设置悬浮窗口位置（屏幕右上角）"""
        if self.floating_widget:
            screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
            x = screen_geometry.width() - self.floating_widget.width() - 50
            y = 50
            self.floating_widget.move(x, y)

    def on_tracking_changed(self, name):
        """
        追踪状态改变处理

        Parameters:
            name (str): 任务名
        """
        old_name = self.data_manager.tracking_task_name

        if old_name == name:
            # 停止追踪当前任务
            self.data_manager.tracking_task_name = None
        else:
            # 开始追踪新任务
            self.data_manager.tracking_task_name = name

        old_item = self.task_items.get(old_name) if old_name else None
        if old_item:
            old_item.set_tracking(False)

        new_item = self.task_items.get(self.data_manager.tracking_task_name)
        if new_item:
            new_item.set_tracking(True)

        self.update_floating_widget()

    def closeEvent(self, event):
        """
        关闭窗口时，保存任务并重置单例标志

        Parameters:
            event (QCloseEvent): 关闭事件
        """
        self.data_manager.save_tasks()
        if self.floating_widget:
            self.floating_widget.close()
        super().closeEvent(event)
        # 重置单例标志，允许下次重新创建
        TaskWindow._instance = None
        TaskWindow._initialized = False