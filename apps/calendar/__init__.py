from PySide6.QtWidgets import (QLabel, QWidget, QHBoxLayout, QVBoxLayout,
                               QScrollArea, QPushButton, QDateEdit, QDialog,
                               QTextEdit, QMessageBox, QDialogButtonBox)
from PySide6.QtCore import Qt, QDate, QEvent, QDateTime

from core.base_objects import BaseWindow
from .calendar_schedule_manager import CalendarSchedulesManager
from core.functions import get_today
from .schedule_editor import ScheduleEditorWindow


class PlaceLabel(QLabel):
    """地点标签，支持链接悬停和点击事件拦截"""

    def __init__(self, text, parent=None):
        """
        初始化地点标签

        Parameters:
            text (str): 显示文本，如果以 https:// 开头则作为链接处理
            parent (QWidget, optional): 父控件，默认为None
        """
        if text.startswith("https://"):
            super().__init__(f'<a href="{text}">{text}</a>', parent)
        else:
            super().__init__(text, parent)
        self.setMouseTracking(True)
        self.is_hovering_link = False
        self.setOpenExternalLinks(True)
        self.linkHovered.connect(self.onLinkHovered)

    def onLinkHovered(self, link):
        """
        链接悬停状态改变时的处理

        Parameters:
            link (str): 悬停的链接地址，空字符串表示离开链接
        """
        if link:
            # 鼠标进入链接
            self.is_hovering_link = True

            # 安装事件过滤器到父控件，阻止事件传递
            if self.parent():
                self.parent().installEventFilter(self)
        else:
            # 鼠标离开链接
            self.is_hovering_link = False

            # 移除事件过滤器，恢复事件传递
            if self.parent():
                self.parent().removeEventFilter(self)

    def eventFilter(self, obj, event):
        """
        事件过滤器：拦截父控件的鼠标事件

        当悬停在链接上时，拦截鼠标事件并转发给当前标签处理，
        防止父控件（如日程项）误触发点击事件。

        Parameters:
            obj (QObject): 事件源对象
            event (QEvent): 事件对象

        Returns:
            bool: 是否拦截事件
        """
        if self.is_hovering_link and obj == self.parent():
            # 当悬停在链接上时，拦截所有鼠标事件
            if event.type() in [QEvent.Type.MouseButtonPress,
                               QEvent.Type.MouseButtonRelease,
                               QEvent.Type.MouseButtonDblClick,
                               QEvent.Type.MouseMove]:
                # 将事件转发给当前标签处理
                self.mousePressEvent(event)
                return True  # 拦截事件，不让父控件处理

        return super().eventFilter(obj, event)

class ScheduleItemWidget(QWidget):
    """日程项部件，显示单个日程的详细信息"""

    def __init__(self, schedule_item, schedule_id=None, parent=None):
        """
        初始化日程项部件

        Parameters:
            schedule_item (dict): 日程数据字典
            schedule_id (int, optional): 日程ID，默认为None
            parent (QWidget, optional): 父控件，默认为None
        """
        super().__init__(parent)
        self.schedule_item = schedule_item
        self.schedule_id = schedule_id

        # 设置悬停效果样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            ScheduleItemWidget:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)

        self.layout_ = QVBoxLayout(self)

        # 标题
        self.title_label = QLabel(schedule_item["title"])
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        self.title_label.setWordWrap(True)
        self.layout_.addWidget(self.title_label)

        # 时间
        if "start_time" and "end_time" in schedule_item and schedule_item["start_time"] and schedule_item["end_time"]:
            self.time_label = QLabel(f"{schedule_item['start_time']} - {schedule_item['end_time']}")
            self.time_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.layout_.addWidget(self.time_label)

        # 地点（支持链接）
        if "location" in schedule_item and schedule_item["location"]:
            self.location_label = PlaceLabel(schedule_item['location'])
            self.location_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.location_label.setWordWrap(True)
            self.layout_.addWidget(self.location_label)

        # 类型和重复信息
        if "type" in schedule_item or ("repetition" in schedule_item and schedule_item["repetition"] != 0):
            self.type_repetition_widget = QWidget()
            self.type_repetition_layout = QHBoxLayout(self.type_repetition_widget)
            self.layout_.addWidget(self.type_repetition_widget)

        if "type" in schedule_item:
            self.type_label = QLabel(
                "类型：{}".format(
                    ["其他", "会议", "娱乐", "活动", "课程"]
                    [schedule_item["type"]]
                )
            )
            self.type_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.type_repetition_layout.addWidget(self.type_label)

        if "repetition" in schedule_item and schedule_item["repetition"] != 0:
            self.repetition_label = QLabel(
                "重复：{}".format(
                    ["无", "每天", "每周"]
                    [schedule_item["repetition"]]
                )
            )
            self.repetition_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.type_repetition_layout.addWidget(self.repetition_label)

    def mousePressEvent(self, event):
        """
        鼠标点击事件，打开日程编辑窗口

        Parameters:
            event (QMouseEvent): 鼠标事件
        """
        editor = ScheduleEditorWindow(self, self.schedule_item, self.schedule_id)
        editor.show()

class ScheduleImportDialog(QDialog):
    """日程文本导入对话框"""

    def __init__(self, parent, year, month, day):
        super().__init__(parent)
        self.year = year
        self.month = month
        self.day = day

        self.setWindowTitle("通过文本导入")
        self.setMinimumSize(400, 300)

        # 创建布局
        layout = QVBoxLayout(self)

        # 添加文本编辑框
        self.import_text_edit = QTextEdit()
        self.import_text_edit.setPlaceholderText("标题: [title]\n地点: [place]\n开始: [start time, yyyy-m-d h:m]\n结束: [end time, yyyy-m-d h:m]\n其他内容: [other contents]")
        layout.addWidget(self.import_text_edit)

        # 添加标准按钮框
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.handle_import)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)

    def handle_import(self):
        """处理文本导入"""
        text = self.import_text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "请输入导入内容")
            return

        # 解析文本
        schedule_data = {}
        lines = text.strip().split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("标题:"):
                schedule_data["title"] = line[3:].strip()
            elif line.startswith("地点:"):
                schedule_data["location"] = line[3:].strip()
            elif line.startswith("开始:"):
                schedule_data["start_time"] = line[3:].strip()
            elif line.startswith("结束:"):
                schedule_data["end_time"] = line[3:].strip()
            elif line.startswith("说明:"):
                # "说明:" 是最后一项，之后的所有内容（包括换行）都属于描述
                description = line[3:].strip()
                # 追加剩余所有行
                for line in lines[i+1:]:
                    description += "\n" + line
                schedule_data["description"] = description
                break

        # 打开日程编辑器并设置内容（使用CalendarWindow作为父窗口）
        editor = ScheduleEditorWindow(self.parent())

        # 设置标题
        if "title" in schedule_data:
            editor.title_editor.set_value(schedule_data["title"])

        # 设置地点
        if "location" in schedule_data:
            editor.location_editor.set_value(schedule_data["location"])

        # 设置开始时间
        if "start_time" in schedule_data:
            q_start_time = QDateTime.fromString(schedule_data["start_time"], "yyyy/M/d HH:mm")
            if q_start_time.isValid():
                editor.start_time_editor.set_value(q_start_time)
                editor.start_time = q_start_time
            elif schedule_data["start_time"]:
                QMessageBox.warning(self, "警告", "开始时间格式错误")

        # 设置结束时间
        if "end_time" in schedule_data:
            q_end_time = QDateTime.fromString(schedule_data["end_time"], "yyyy/M/d HH:mm")
            if q_end_time.isValid():
                editor.end_time_editor.set_value(q_end_time)
                editor.end_time = q_end_time
            elif schedule_data["end_time"]:
                QMessageBox.warning(self, "警告", "结束时间格式错误")

        # 重新计算时长
        if hasattr(editor, 'start_time') and hasattr(editor, 'end_time'):
            editor.duration = editor.start_time.secsTo(editor.end_time)

        # 设置描述
        if "description" in schedule_data:
            editor.description_editor.set_value(schedule_data["description"])

        editor.show()

        # 关闭对话框
        self.close()

class CalendarWindow(BaseWindow):
    """日历窗口，提供日程的查看、创建和编辑功能"""

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
        初始化日历窗口

        Parameters:
            parent (QWidget, optional): 父窗口，默认为None
        """
        if CalendarWindow._initialized:
            return
        super().__init__(parent)
        self.schedule_manager = CalendarSchedulesManager()

        self.setWindowTitle("日程")
        self.setMinimumSize(600, 400)

        # 主容器
        self.container = QWidget()
        self.setCentralWidget(self.container)

        self.container_layout = QVBoxLayout(self.container)

        # 日期选择器
        self.date_selector = QDateEdit(self.container)
        self.date_selector.setFixedHeight(30)
        self.date_selector.setCalendarPopup(True)
        self.container_layout.addWidget(self.date_selector)

        # 滚动区域用于显示日程列表
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.container_layout.addWidget(self.scroll_area)

        # 创建底部按钮布局
        self.create_bottom_buttons()

        # 连接信号
        self.date_selector.dateChanged.connect(self.on_date_changed)

        # 设置初始日期为今天
        today = get_today()
        self.date_selector.setDate(QDate(today.year, today.month, today.day))
        CalendarWindow._instance = self
        CalendarWindow._initialized = True

    def closeEvent(self, event):
        """
        窗口关闭时触发，将内存中的所有脏数据一次性写入磁盘。

        Parameters:
            event (QCloseEvent): 关闭事件
        """
        self.schedule_manager.flush_to_disk()
        super().closeEvent(event)
        CalendarWindow._instance = None
        CalendarWindow._initialized = False

    def create_bottom_buttons(self):
        """创建底部按钮布局"""
        # 创建底部按钮容器
        self.bottom_button_widget = QWidget()
        self.bottom_button_layout = QHBoxLayout(self.bottom_button_widget)

        # 添加拉伸，使按钮靠右
        self.bottom_button_layout.addStretch()

        # 添加导入按钮
        self.import_button = QPushButton("通过文本导入")
        self.import_button.clicked.connect(self.open_import_dialog)
        self.bottom_button_layout.addWidget(self.import_button)

        # 添加日程按钮
        self.add_button = QPushButton("添加日程")
        self.add_button.clicked.connect(self.open_new_schedule)
        self.bottom_button_layout.addWidget(self.add_button)

        # 添加到主布局
        self.container_layout.addWidget(self.bottom_button_widget)

    def open_import_dialog(self):
        """打开文本导入对话框"""
        dialog = ScheduleImportDialog(self, self.year_displayed, self.month_displayed, self.day_displayed)
        dialog.show()

    def on_date_changed(self, date):
        """
        日期选择改变时的处理

        Parameters:
            date (QDate): 新选择的日期
        """
        self.year_displayed = date.year()
        self.month_displayed = date.month()
        self.day_displayed = date.day()

        self.refresh_schedules()

    def open_new_schedule(self):
        """打开新增日程编辑窗口"""
        editor = ScheduleEditorWindow(
            self,
            year=self.year_displayed,
            month=self.month_displayed,
            day=self.day_displayed
        )
        editor.show()

    def refresh_schedules(self):
        """刷新当前显示日期的日程列表"""
        # 清空现有布局（包括所有widget和stretch）
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新加载数据
        self.schedules = self.schedule_manager.get_schedules(self.year_displayed, self.month_displayed, self.day_displayed)

        # 添加日程项
        for schedule_id, schedule in self.schedules.items():
            self.scroll_layout.addWidget(ScheduleItemWidget(schedule, schedule_id))

        # 添加stretch，确保日程项在顶部，空白在底部
        self.scroll_layout.addStretch()

    def save_schedule_from_editor(self, schedule_editor, copy=False):
        """
        从日程编辑器保存日程。

        Parameters:
            schedule_editor: 日程编辑器窗口实例。
            copy: 是否复制旧日程，默认False。
        """
        self.save_schedule(
            schedule_data=schedule_editor.schedule_data,
            year_new=schedule_editor.year_new,
            month_new=schedule_editor.month_new,
            day_new=schedule_editor.day_new,
            id_new=schedule_editor.id_new,
            year_old=schedule_editor.year,
            month_old=schedule_editor.month,
            day_old=schedule_editor.day,
            id_old=schedule_editor.id,
            copy=copy
        )

    def save_schedule(
            self,
            schedule_data,
            year_new, month_new, day_new, id_new,
            year_old=None, month_old=None, day_old=None, id_old=None,
            copy=False
        ):
        """
        保存日程到文件。

        Parameters:
            schedule_data: 日程数据字典。
            year_new: 新日期的年份。
            month_new: 新日期的月份。
            day_new: 新日期的日期。
            id_new: 新日程的id。
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
            copy: 是否复制旧日程，默认False。
        """
        self.schedule_manager.save_schedule(
            schedule_data,
            year_new, month_new, day_new, id_new,
            year_old, month_old,
            day_old,
            id_old,
            copy
        )

        if (self.year_displayed == year_new
            and self.month_displayed == month_new
            and self.day_displayed == day_new
        ):
            self.refresh_schedules()

    def delete_schedule_from_editor(self, schedule_editor):
        """
        从日程编辑器删除日程。

        Parameters:
            schedule_editor: 日程编辑器窗口实例。
        """
        self.delete_schedule(
            schedule_editor.year,
            schedule_editor.month,
            schedule_editor.day,
            schedule_editor.id
        )

    def delete_schedule(self, year_old, month_old, day_old, id_old):
        """
        从文件中删除日程。

        Parameters:
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
        """
        flag = self.schedule_manager.delete_schedule(year_old, month_old, day_old, id_old)
        if flag:
            return

        if (self.year_displayed == year_old
            and self.month_displayed == month_old
            and self.day_displayed == day_old
        ):
            self.refresh_schedules()