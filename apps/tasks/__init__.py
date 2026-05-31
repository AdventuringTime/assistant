import sys
import json
import os
from PySide6.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout,
                               QScrollArea, QHBoxLayout, QInputDialog, QPushButton,
                               QLineEdit, QDoubleSpinBox, QMessageBox, QSpinBox,
                               QTextEdit, QSizePolicy, QListWidget, QDialog, QComboBox)
from PySide6.QtCore import Qt, Signal, QEvent, QTimer, QUrl
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtGui import QDesktopServices

from core.base_window import BaseWindow, BaseDialog


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

    def __init__(self, parent, children, title="排序"):
        """
        初始化排序对话框

        Parameters:
            parent (QWidget): 父窗口
            children (list): 待排序的任务列表，每个元素包含 'name' 键
            title (str, optional): 对话框标题，默认为"排序"
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.children = children

        layout = QVBoxLayout(self)

        # 创建可拖拽排序的列表
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        layout.addWidget(self.list_widget)

        # 添加任务名称到列表
        for child in self.children:
            self.list_widget.addItem(child['name'])

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
        """确认排序，根据列表顺序重新排列任务"""
        new_order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = item.text()
            for child in self.children:
                if child['name'] == name and child not in new_order:
                    new_order.append(child)
                    break
        self.result = new_order
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
        self.setModal(True)

        self.layout_ = QVBoxLayout(self)

        # 任务名称
        self.name_label = QLabel('任务名称:')
        self.name_edit = QLineEdit()
        if task:
            self.name_edit.setText(task.get('name', ''))
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
            self.delete_button = QPushButton('删除')
            self.delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #CC0000;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #FF3333;
                }
                QPushButton:pressed {
                    background-color: #990000;
                }
            """)
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
    tracking_changed = Signal(int)    # 追踪状态改变信号
    task_completed = Signal(int)      # 任务完成信号

    def __init__(self, task, id_, is_tracking=False, is_completed=False, parent=None):
        """
        初始化任务项部件

        Parameters:
            task (dict): 任务数据字典
            id_ (int): 任务索引ID
            is_tracking (bool, optional): 是否正在追踪，默认为False
            is_completed (bool, optional): 是否在已完成列表中，默认为False
            parent (QWidget, optional): 父控件
        """
        super().__init__(parent)
        self.task = task
        self.id_ = id_
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

        self.name_label = QLabel(self.task.get('name', ''))
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
        self.delete_button = QPushButton('删除')
        self.delete_button.clicked.connect(self.delete_task)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #641A1A;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #6B2020;
            }
            QPushButton:pressed {
                background-color: #4A1515;
            }
        """)
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
                background-color: rgba(255, 255, 255, 0.05);
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

    def update_style(self):
        """根据追踪状态更新样式"""
        r, g, b = _hex_to_rgb(self.current_color)
        if self.is_tracking:
            self.setStyleSheet(f"""
                TaskItem {{
                    background-color: rgba({r}, {g}, {b}, 0.15);
                }}
                TaskItem:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.22);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                TaskItem:hover {{
                    background-color: rgba({r}, {g}, {b}, 0.08);
                }}
            """)

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
        self.task_completed.emit(self.id_)

    def on_go_clicked(self):
        """打开任务关联的链接"""
        link = self.task.get('link', '')
        if not link:
            return
        url = QUrl(link)
        QDesktopServices.openUrl(url)

    def on_track_clicked(self):
        """触发追踪状态改变信号"""
        self.tracking_changed.emit(self.id_)

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
        """通过输入对话框修改完成数量"""
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
        dialog = TaskDialog(self.task, self)
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
        """处理保存操作，更新任务数据"""
        self.task.clear()
        self.task.update(data)
        self.name_label.setText(data['name'])

        # 更新任务类型和颜色
        new_type = data.get('type', 0)
        if new_type != self.task_type:
            self.task_type = new_type
            if self.task_type == 0:
                self.current_color = self.color_branch
            elif self.task_type == 1:
                self.current_color = self.color_main
            self.line_widget.setStyleSheet(f"background-color: {self.current_color};")
            self.update_style()

        # 更新子任务（只显示第一行）
        self.subtask_label.setText(get_subtasks_first_line(self.task))
        if self.subtask_label.text():
            self.subtask_label.show()
        else:
            self.subtask_label.hide()

        # 更新进度
        self.required = data['required']
        self.update_progress_percent()
        self.update_buttons_visibility()
        self.task_updated.emit()


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
        self.tasks = []
        self.completed_tasks = []
        self.tracking_task_id = None
        self._initialized = True
        self.load_tasks()

    def load_tasks(self):
        """从文件加载任务数据"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.tasks = data.get('tasks', [])
            self.completed_tasks = data.get('completed_tasks', [])
            self.tracking_task_id = data.get('tracking_task_id', None)

    def save_tasks(self):
        """保存任务数据到文件"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        json_path = os.path.join(data_dir, 'tasks.json')

        data = {
            'tasks': self.tasks,
            'completed_tasks': self.completed_tasks,
            'tracking_task_id': self.tracking_task_id
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


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
                progress_text = f'({completed}/{required})'
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

    _instance = None          # 单例实例
    _initialized = False      # 防止重复初始化

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
        TaskWindow._instance = self
        TaskWindow._initialized = True

        self.setWindowTitle('任务')
        self.setMinimumSize(600, 400)
        self.resize(1000, 800)

        # 使用数据管理器
        self.data_manager = TaskDataManager()
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

        self.task_items = []
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

    def open_sort_dialog(self):
        """打开任务排序对话框"""
        if not self.tasks:
            return

        dialog = SortDialog(self, self.tasks, "排序")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 排序后暂时移除追踪
            if self.tracking_task_id is not None:
                self.on_tracking_changed(self.tracking_task_id)
            self.tasks = dialog.result
            self.refresh_ui()

    def load_tasks(self):
        """从文件加载任务数据"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.tasks = data.get('tasks', [])
            self.completed_tasks = data.get('completed_tasks', [])
            self.tracking_task_id = data.get('tracking_task_id', None)

    def save_tasks(self):
        """保存任务数据到文件"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        json_path = os.path.join(data_dir, 'tasks.json')

        data = {
            'tasks': self.tasks,
            'completed_tasks': self.completed_tasks,
            'tracking_task_id': self.tracking_task_id
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _create_task_item(self, task, id_, is_tracking=False, is_completed=False):
        """
        创建任务项并连接信号
        
        Parameters:
            task (dict): 任务数据
            id_ (int): 任务项在列表中的ID
            is_tracking (bool, optional): 是否正在追踪该任务，默认False
            is_completed (bool, optional): 是否已完成该任务，默认False
        """
        task_item = TaskItem(task, id_, is_tracking, is_completed)
        task_item.task_updated.connect(self.on_task_updated)
        task_item.task_deleted.connect(self.on_task_deleted)
        task_item.task_copy_created.connect(self.on_creation_via_dialog)
        task_item.tracking_changed.connect(self.on_tracking_changed)
        task_item.task_completed.connect(self.on_task_completed)
        self.task_items.append(task_item)
        self.content_layout.insertWidget(len(self.task_items) - 1, task_item)

    def refresh_ui(self):
        """刷新任务列表UI"""
        # 清除现有任务项
        for item in self.task_items:
            item.deleteLater()
        self.task_items.clear()

        # 显示待办任务
        for id_, task in enumerate(self.data_manager.tasks):
            is_tracking = (self.data_manager.tracking_task_id == id_)
            self._create_task_item(task, id_, is_tracking, False)

        # 显示已完成任务（在待办任务后面）
        for id_old, task in enumerate(self.data_manager.completed_tasks):
            id_ = len(self.data_manager.tasks) + id_old
            is_tracking = (self.data_manager.tracking_task_id == id_)
            self._create_task_item(task, id_, is_tracking, True)

    def on_task_updated(self):
        """任务更新后的处理"""
        self.update_floating_widget()

    def remove_task(self, display_index):
        """
        删除任务并更新追踪ID
        
        Parameters:
            display_index (int): 任务项在显示列表中的索引
        """
        if display_index < len(self.data_manager.tasks):
            # 删除待办任务
            del self.data_manager.tasks[display_index]
        else:
            # 删除已完成任务
            completed_index = display_index - len(self.data_manager.tasks)
            del self.data_manager.completed_tasks[completed_index]

        # 更新追踪ID
        if self.data_manager.tracking_task_id == display_index:
            self.data_manager.tracking_task_id = None
        elif self.data_manager.tracking_task_id is not None and self.data_manager.tracking_task_id > display_index:
            self.data_manager.tracking_task_id -= 1

    def on_task_deleted(self):
        """任务删除后的处理"""
        sender = self.sender()
        if sender in self.task_items:
            display_index = self.task_items.index(sender)
            self.remove_task(display_index)
            self.refresh_ui()
            self.update_floating_widget()

    def on_task_completed(self, index):
        """
        任务完成后的处理
        
        Parameters:
            index (int): 任务项在列表中的索引
        """
        task = self.data_manager.tasks[index]
        
        # 将任务追加到已完成任务列表
        self.data_manager.completed_tasks.append(task.copy())
        
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
            self.remove_task(index)
        
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
        if data['name'].strip():
            self.data_manager.tasks.append(data)
            self.refresh_ui()

    def update_floating_widget(self):
        """更新悬浮窗口显示当前追踪任务"""
        if self.data_manager.tracking_task_id is not None:
            if self.data_manager.tracking_task_id < len(self.data_manager.tasks):
                # 追踪待办任务
                task = self.data_manager.tasks[self.data_manager.tracking_task_id]
            else:
                # 追踪已完成任务
                completed_index = self.data_manager.tracking_task_id - len(self.data_manager.tasks)
                task = self.data_manager.completed_tasks[completed_index]

            task_type = task.get('type', 0)
            color = '#00CC66' if task_type == 0 else '#FFCC00'

            completed = task.get('completed', 0.0)
            required = task.get('required', 1.0)
            name = task.get('name', '')
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
        if self.data_manager.tracking_task_id is not None and 0 <= self.data_manager.tracking_task_id < len(self.task_items):
            self.task_items[self.data_manager.tracking_task_id].set_completed_from_input()

    def set_floating_position(self):
        """设置悬浮窗口位置（屏幕右上角）"""
        if self.floating_widget:
            screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
            x = screen_geometry.width() - self.floating_widget.width() - 50
            y = 50
            self.floating_widget.move(x, y)

    def on_tracking_changed(self, index):
        """
        追踪状态改变处理
        
        Parameters:
            index (int): 任务项在列表中的索引
        """
        old_index = self.data_manager.tracking_task_id

        if self.data_manager.tracking_task_id == index:
            # 停止追踪当前任务
            self.data_manager.tracking_task_id = None
            self.task_items[index].set_tracking(False)
        else:
            # 开始追踪新任务
            self.data_manager.tracking_task_id = index
            if old_index is not None:
                self.task_items[old_index].set_tracking(False)
            self.task_items[index].set_tracking(True)

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