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

        # 任务描述
        self.description_label = QLabel('任务描述:')
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)
        if task:
            self.description_edit.setPlainText(task.get('description', ''))
        self.layout_.addWidget(self.description_label)
        self.layout_.addWidget(self.description_edit)

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
            self.delete_button.setStyleSheet("background-color: #CC0000; color: #FFFFFF;")
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
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
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
            'description': self.description_edit.toPlainText(),
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
                QTimer.singleShot(0, self.required_spin.selectAll)
            elif obj == self.link_edit:
                QTimer.singleShot(0, self.link_edit.selectAll)
        return super().eventFilter(obj, event)


class TaskItem(QWidget):
    """任务项部件，显示单个任务的详细信息和操作按钮"""

    task_updated = Signal()           # 任务更新信号
    task_deleted = Signal()           # 任务删除信号
    task_copy_created = Signal(dict)  # 任务副本创建信号
    tracking_changed = Signal(int)    # 追踪状态改变信号

    def __init__(self, task, id_, is_tracking=False, parent=None):
        """
        初始化任务项部件

        Parameters:
            task (dict): 任务数据字典
            id_ (int): 任务索引ID
            is_tracking (bool, optional): 是否正在追踪，默认为False
            parent (QWidget, optional): 父控件
        """
        super().__init__(parent)
        self.task = task
        self.id_ = id_
        self.is_tracking = is_tracking
        self.task_type = task.get('type', 0)

        # 任务类型颜色：主线黄色，支线绿色
        self.color_main = '#FFCC00'
        self.color_branch = '#00CC66'
        if self.task_type == 0:
            self.current_color = self.color_branch
        elif self.task_type == 1:
            self.current_color = self.color_main

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.update_style()

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
        self.top_layout.addWidget(self.name_label)

        # 前往按钮（追踪模式下显示）
        self.go_button = QPushButton('前往')
        self.go_button.clicked.connect(self.on_go_clicked)
        self.top_layout.addWidget(self.go_button)
        self.go_button.setVisible(is_tracking and bool(self.task.get('link')))

        # 编辑按钮
        self.edit_button = QPushButton('编辑')
        self.edit_button.clicked.connect(self.on_edit_clicked)
        self.top_layout.addWidget(self.edit_button)

        # 追踪按钮
        self.track_button = QPushButton('开始追踪' if not is_tracking else '停止追踪')
        self.track_button.clicked.connect(self.on_track_clicked)
        self.top_layout.addWidget(self.track_button)

        self.content_layout.addLayout(self.top_layout)

        # 任务描述
        self.description_label = QLabel(self.task.get('description', ''))
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-size: 15px; color: #AAAAAA;")
        self.content_layout.addWidget(self.description_label)
        if not self.description_label.text():
            self.description_label.hide()

        # 进度信息
        self.completed = self.task.get('completed', 0.0)
        self.required = self.task.get('required', 1.0)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(20)

        # 进度标签
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-size: 14px; color: #888888;")

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

        self.update_progress_percent()

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
        self.go_button.setVisible(is_tracking and bool(self.task.get('link')))

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
            self.task_updated.emit()

    def on_edit_clicked(self, event):
        """打开任务编辑对话框"""
        dialog = TaskDialog(self.task, self)
        dialog.on_save_signal.connect(self.on_dialog_save)
        dialog.on_save_copy_signal.connect(self.on_dialog_save_copy)
        dialog.on_delete_signal.connect(self.on_dialog_delete)
        dialog.show()

    def on_dialog_save_copy(self, data):
        """处理保存副本操作"""
        self.task_copy_created.emit(data)

    def on_dialog_delete(self):
        """处理删除操作"""
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

        # 更新描述
        self.description_label.setText(data['description'])
        if self.description_label.text():
            self.description_label.show()
        else:
            self.description_label.hide()

        # 更新进度
        self.required = data['required']
        self.update_progress_percent()
        self.go_button.setVisible(self.is_tracking and bool(self.task.get('link')))
        self.task_updated.emit()


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

    def set_content(self, name, completed, required, description, color):
        """
        设置悬浮窗口的内容

        Parameters:
            name (str): 任务名称
            completed (float): 已完成数量
            required (float): 所需数量
            description (str): 任务描述
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
        self.bottom_label.setText(description)
        self.bottom_label.setVisible(bool(description.strip()))

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

    def __init__(self, parent=None):
        """
        初始化任务窗口

        Parameters:
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle('任务')
        self.setMinimumSize(600, 400)
        self.resize(1000, 800)

        # 任务数据和追踪状态
        self.tasks = []
        self.tracking_task_id = None
        self.floating_widget = None
        self.load_tasks()

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
            self.tasks = data['tasks']
            self.tracking_task_id = data.get('tracking_task_id', None)

    def save_tasks(self):
        """保存任务数据到文件"""
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)
        json_path = os.path.join(data_dir, 'tasks.json')

        data = {
            'tasks': self.tasks,
            'tracking_task_id': self.tracking_task_id
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def refresh_ui(self):
        """刷新任务列表UI"""
        # 清除现有任务项
        for item in self.task_items:
            item.deleteLater()
        self.task_items.clear()

        # 重新创建任务项
        for id_, task in enumerate(self.tasks):
            is_tracking = (self.tracking_task_id == id_)
            task_item = TaskItem(task, id_, is_tracking)
            task_item.task_updated.connect(self.on_task_updated)
            task_item.task_deleted.connect(self.on_task_deleted)
            task_item.task_copy_created.connect(self.on_creation_via_dialog)
            task_item.tracking_changed.connect(self.on_tracking_changed)
            self.task_items.append(task_item)
            self.content_layout.insertWidget(id_, task_item)

    def on_task_updated(self):
        """任务更新后的处理"""
        self.update_floating_widget()

    def on_task_deleted(self):
        """任务删除后的处理"""
        sender = self.sender()
        if sender in self.task_items:
            index = self.task_items.index(sender)
            # 更新追踪ID
            if self.tracking_task_id == index:
                self.tracking_task_id = None
            elif self.tracking_task_id is not None and self.tracking_task_id > index:
                self.tracking_task_id -= 1
            # 删除任务
            del self.tasks[index]
            self.refresh_ui()
            self.update_floating_widget()

    def on_add_task(self):
        """打开添加任务对话框"""
        dialog = TaskDialog(parent=self)
        dialog.on_save_signal.connect(self.on_creation_via_dialog)
        dialog.show()

    def on_creation_via_dialog(self, data):
        """通过对话框创建新任务"""
        if data['name'].strip():
            self.tasks.append(data)
            self.refresh_ui()

    def update_floating_widget(self):
        """更新悬浮窗口显示当前追踪任务"""
        if self.tracking_task_id is not None and 0 <= self.tracking_task_id < len(self.tasks):
            task = self.tasks[self.tracking_task_id]
            task_type = task.get('type', 0)
            color = '#00CC66' if task_type == 0 else '#FFCC00'

            completed = task.get('completed', 0.0)
            required = task.get('required', 1.0)
            name = task.get('name', '')
            description = task.get('description', '')

            if not self.floating_widget:
                self.floating_widget = FloatingWidget()
                self.floating_widget.clicked.connect(self.on_floating_clicked)

            self.floating_widget.set_content(name, completed, required, description, color)
            self.set_floating_position()
            self.floating_widget.show()
        else:
            if self.floating_widget:
                self.floating_widget.hide()

    def on_floating_clicked(self):
        """悬浮窗口点击处理，打开进度修改对话框"""
        if self.tracking_task_id is not None and 0 <= self.tracking_task_id < len(self.task_items):
            self.task_items[self.tracking_task_id].set_completed_from_input()

    def set_floating_position(self):
        """设置悬浮窗口位置（屏幕右上角）"""
        if self.floating_widget:
            screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
            x = screen_geometry.width() - self.floating_widget.width() - 50
            y = 50
            self.floating_widget.move(x, y)

    def on_tracking_changed(self, index):
        """追踪状态改变处理"""
        old_index = self.tracking_task_id

        if self.tracking_task_id == index:
            # 停止追踪当前任务
            self.tracking_task_id = None
            self.task_items[index].set_tracking(False)
        else:
            # 开始追踪新任务
            self.tracking_task_id = index
            if old_index is not None:
                self.task_items[old_index].set_tracking(False)
            self.task_items[index].set_tracking(True)

        self.update_floating_widget()

    def closeEvent(self, event):
        """
        关闭窗口事件处理

        Parameters:
            event (QCloseEvent): 关闭事件
        """
        self.save_tasks()
        if self.floating_widget:
            self.floating_widget.close()
        super().closeEvent(event)