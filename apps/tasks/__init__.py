import sys
import json
import os
from PySide6.QtWidgets import (QWidget, QLabel, QProgressBar, QVBoxLayout,
                               QScrollArea, QHBoxLayout, QInputDialog, QPushButton,
                               QLineEdit, QDoubleSpinBox, QMessageBox, QSpinBox,
                               QTextEdit, QSizePolicy, QListWidget, QDialog)
from PySide6.QtCore import Qt, Signal, QEvent, QTimer, QUrl
from PySide6.QtGui import QFont
from PySide6.QtGui import QDesktopServices

from core.base_window import BaseWindow, BaseDialog


class SortDialog(BaseDialog):
    def __init__(self, parent, children, title="排序"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.children = children

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        layout.addWidget(self.list_widget)

        for child in self.children:
            self.list_widget.addItem(child['name'])

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
        self.result = None
        super().reject()


class TaskDialog(BaseDialog):
    on_save_signal = Signal(dict)
    on_delete_signal = Signal()

    def __init__(self, task=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.setWindowTitle('任务')
        self.setModal(True)

        self.layout_ = QVBoxLayout(self)

        self.name_label = QLabel('任务名称:')
        self.name_edit = QLineEdit()
        if task:
            self.name_edit.setText(task.get('name', ''))
        self.layout_.addWidget(self.name_label)
        self.layout_.addWidget(self.name_edit)

        self.description_label = QLabel('任务描述:')
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)
        if task:
            self.description_edit.setPlainText(task.get('description', ''))
        self.layout_.addWidget(self.description_label)
        self.layout_.addWidget(self.description_edit)

        self.required_label = QLabel('所需次数:')
        self.required_spin = QDoubleSpinBox(decimals=2)
        self.required_spin.setRange(0.0, 1e15)
        if task:
            self.required_spin.setValue(task.get('required', 1.0))
        else:
            self.required_spin.setValue(1.0)
        self.required_spin.installEventFilter(self)
        self.layout_.addWidget(self.required_label)
        self.layout_.addWidget(self.required_spin)

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

    def on_convert_path(self):
        """将文件路径转换为file://链接"""
        path = self.link_edit.text().strip()

        if ((not '://' in path) and # 这种已经是链接了
            ('\\' in path or '/' in path)):
            # 转换为file://链接
            # 处理Windows路径
            path = path.replace('\\', '/')
            if not path.startswith('/'):
                path = '/' + path
            file_url = 'file://' + path
            self.link_edit.setText(file_url)
    
    def get_task_data(self):
        data = {
            'name': self.name_edit.text(),
            'description': self.description_edit.toPlainText(),
            'completed': self.task.get('completed', 0.0) if self.task else 0.0,
            'required': self.required_spin.value()
        }
        link = self.link_edit.text().strip()
        if link:
            data['link'] = link
        return data

    def eventFilter(self, obj, event):
        if obj == self.required_spin and event.type() == QEvent.Type.FocusIn:
            QTimer.singleShot(0, self.required_spin.selectAll)
            return False
        return super().eventFilter(obj, event)


class TaskItem(QWidget):
    task_updated = Signal()
    task_deleted = Signal()
    tracking_changed = Signal(int)

    def __init__(self, task, id_, is_tracking=False, parent=None):
        super().__init__(parent)
        self.task = task
        self.id_ = id_
        self.is_tracking = is_tracking

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if is_tracking:
            self.setStyleSheet("""
                TaskItem {
                    background-color: rgba(255, 255, 255, 0.2);
                }
                TaskItem:hover {
                    background-color: rgba(255, 255, 255, 0.28);
                }
            """)
        else:
            self.setStyleSheet("""
                TaskItem:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)

        self.layout_ = QVBoxLayout(self)

        self.top_layout = QHBoxLayout()

        self.name_label = QLabel(self.task.get('name', ''))
        self.name_label.setWordWrap(True)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        font = QFont()
        font.setPointSize(14)
        self.name_label.setFont(font)
        self.top_layout.addWidget(self.name_label)

        self.go_button = QPushButton('前往')
        self.go_button.clicked.connect(self.on_go_clicked)
        self.top_layout.addWidget(self.go_button)
        self.go_button.setVisible(is_tracking and bool(self.task.get('link')))

        self.edit_button = QPushButton('编辑')
        self.edit_button.clicked.connect(self.on_edit_clicked)
        self.top_layout.addWidget(self.edit_button)

        self.track_button = QPushButton('开始追踪' if not is_tracking else '停止追踪')
        self.track_button.clicked.connect(self.on_track_clicked)
        self.top_layout.addWidget(self.track_button)

        self.layout_.addLayout(self.top_layout)

        self.description_label = QLabel(self.task.get('description', ''))
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-size: 15px; color: #AAAAAA;")
        self.layout_.addWidget(self.description_label)
        if not self.description_label.text():
            self.description_label.hide()

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

    def set_tracking(self, is_tracking):
        self.is_tracking = is_tracking
        if is_tracking:
            self.track_button.setText('停止追踪')
            self.setStyleSheet("""
                TaskItem {
                    background-color: rgba(255, 255, 255, 0.2);
                }
                TaskItem:hover {
                    background-color: rgba(255, 255, 255, 0.3);
                }
            """)
        else:
            self.track_button.setText('开始追踪')
            self.setStyleSheet("""
                TaskItem:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)
        self.go_button.setVisible(is_tracking and bool(self.task.get('link')))

    def on_go_clicked(self):
        link = self.task.get('link', '')
        if not link:
            return
        url = QUrl(link)
        QDesktopServices.openUrl(url) # 执行失败无异常抛出，无需 try-except

    def on_track_clicked(self):
        self.tracking_changed.emit(self.id_)

    def update_progress_percent(self):
        """更新进度条和进度标签"""
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
        self.progress_bar.setValue(int(self.progress_percent))

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

    def on_edit_clicked(self, event):
        dialog = TaskDialog(self.task, self)
        dialog.on_save_signal.connect(self.on_dialog_save)
        dialog.on_delete_signal.connect(self.on_dialog_delete)

        dialog.show()

    def on_dialog_delete(self):
        self.task_deleted.emit()

    def on_dialog_save(self, data):
        self.task.clear()
        self.task.update(data)
        self.name_label.setText(data['name'])
        self.description_label.setText(data['description'])
        if self.description_label.text():
            self.description_label.show()
        else:
            self.description_label.hide()
        self.required = data['required']
        self.update_progress_percent()
        self.go_button.setVisible(self.is_tracking and bool(self.task.get('link')))
        self.task_updated.emit()


class TaskWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('任务')
        self.setMinimumSize(600, 400)
        self.resize(1000, 800)

        self.tasks = []
        self.tracking_task_id = None
        self.load_tasks()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.header = QLabel('任务')
        self.header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        self.header.setMargin(5)
        self.main_layout.addWidget(self.header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        self.task_items = []
        self.content_layout.addStretch()
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)



        self.button_layout = QHBoxLayout()

        self.button_layout.addStretch()

        self.sort_button = QPushButton("排序")
        self.sort_button.clicked.connect(self.open_sort_dialog)
        self.button_layout.addWidget(self.sort_button)

        self.add_button = QPushButton('添加任务')
        self.add_button.clicked.connect(self.on_add_task)
        self.button_layout.addWidget(self.add_button)

        self.main_layout.addLayout(self.button_layout)

        self.refresh_ui()

    def open_sort_dialog(self):
        if not self.tasks:
            return

        dialog = SortDialog(self, self.tasks, "排序")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.tracking_task_id = None # 排序后暂时移除追踪
            self.tasks = dialog.result
            self.save_tasks()
            self.refresh_ui()

    def load_tasks(self):
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        json_path = os.path.join(data_dir, 'tasks.json')

        if not os.path.exists(json_path):
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            self.tasks = data['tasks']
            self.tracking_task_id = data.get('tracking_task_id', None)

    def save_tasks(self):
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
        for item in self.task_items:
            item.deleteLater()
        self.task_items.clear()

        for id_, task in enumerate(self.tasks):
            is_tracking = (self.tracking_task_id == id_)
            task_item = TaskItem(task, id_, is_tracking)
            task_item.task_updated.connect(self.on_task_updated)
            task_item.task_deleted.connect(self.on_task_deleted)
            task_item.tracking_changed.connect(self.on_tracking_changed)
            self.task_items.append(task_item)
            self.content_layout.insertWidget(id_, task_item)

    def on_task_updated(self):
        self.save_tasks()

    def on_task_deleted(self):
        sender = self.sender()
        if sender in self.task_items:
            index = self.task_items.index(sender)
            if self.tracking_task_id == index:
                self.tracking_task_id = None
            elif self.tracking_task_id is not None and self.tracking_task_id > index:
                self.tracking_task_id -= 1
            del self.tasks[index]
            self.save_tasks()
            self.refresh_ui()

    def on_add_task(self):
        dialog = TaskDialog(parent=self)
        dialog.on_save_signal.connect(self.on_dialog_create)
        dialog.show()

    def on_dialog_create(self, data):
        if data['name'].strip():
            self.tasks.append(data)
            self.save_tasks()
            self.refresh_ui()

    def on_tracking_changed(self, index):
        old_index = self.tracking_task_id

        if self.tracking_task_id == index:
            self.tracking_task_id = None
            self.task_items[index].set_tracking(False)
        else:
            self.tracking_task_id = index
            if old_index is not None:
                self.task_items[old_index].set_tracking(False)
            self.task_items[index].set_tracking(True)

        self.save_tasks()