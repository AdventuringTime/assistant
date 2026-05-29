from datetime import datetime

from core.base_window import BaseWindow
from core.functions import get_today, block_signals
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QMessageBox)
from PySide6.QtCore import QDateTime, QDate, QTime
from core.widgets import SettingItemWidget


def _get_date(time):
    """
    从时间对象中提取日期的年、月、日

    Parameters:
        time (datetime): 时间对象

    Returns:
        tuple: (year, month, day)
    """
    schedule_date = get_today(time)

    year = schedule_date.year
    month = schedule_date.month
    day = schedule_date.day

    return year, month, day


class ScheduleEditorWindow(BaseWindow):
    """日程编辑窗口，用于创建或编辑日程项"""

    def __init__(self, parent, schedule_item=None, schedule_id=None, *, year=None, month=None, day=None):
        """
        初始化日程编辑窗口

        Parameters:
            parent (QWidget): 父窗口
            schedule_item (dict, optional): 现有日程数据（编辑模式），默认为None（新建模式）
            schedule_id (int, optional): 日程ID，默认为None
            year (int, optional): 新建日程时的默认年
            month (int, optional): 新建日程时的默认月
            day (int, optional): 新建日程时的默认日
        """
        super().__init__(parent)
        self.schedule_item = schedule_item or {}  # a if a else b
        self.is_new_schedule = schedule_item is None

        if schedule_item:
            self.year, self.month, self.day = _get_date(datetime.strptime(schedule_item["start_time"], "%Y-%m-%d %H:%M"))
        else:
            self.year, self.month, self.day = year, month, day
        self.id = schedule_id

        self.init_ui()
        self.load_schedule_data()

        self.start_time_editor.input_field.dateTimeChanged.connect(self.on_start_time_changed)
        self.end_time_editor.input_field.dateTimeChanged.connect(self.on_end_time_changed)

    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("日程项")
        self.setMinimumSize(500, 400)

        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 主布局
        main_layout = QVBoxLayout(self.central_widget)

        # 创建日程项编辑器
        self.title_editor = SettingItemWidget("标题", "text", "新日程")
        self.type_editor = SettingItemWidget("类型", "type", ["其他", "会议", "娱乐", "活动", "课程"])
        self.start_time_editor = SettingItemWidget("开始时间", "datetime")
        self.end_time_editor = SettingItemWidget("结束时间", "datetime")
        self.location_editor = SettingItemWidget("地点", "text")
        self.repetition_editor = SettingItemWidget("重复", "type", ["无", "每天", "每周"])
        self.description_editor = SettingItemWidget("描述", "textarea")

        # 添加日程项到主布局
        main_layout.addWidget(self.title_editor)
        main_layout.addWidget(self.type_editor)
        main_layout.addWidget(self.start_time_editor)
        main_layout.addWidget(self.end_time_editor)
        main_layout.addWidget(self.location_editor)
        main_layout.addWidget(self.repetition_editor)
        main_layout.addWidget(self.description_editor)
        main_layout.addStretch()

        # 按钮布局
        button_layout = QHBoxLayout()

        if not self.is_new_schedule:
            self.delete_button = QPushButton("删除")
            self.delete_button.clicked.connect(self.delete_schedule)
            self.delete_button.setStyleSheet("background-color: #ff6b6b; color: white;")
            button_layout.addWidget(self.delete_button)

        button_layout.addStretch()

        if not self.is_new_schedule:
            self.saveas_button = QPushButton("保存副本")
            self.saveas_button.clicked.connect(lambda: self.save_schedule(copy=True))
            button_layout.addWidget(self.saveas_button)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_schedule)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

    def load_schedule_data(self):
        """
        加载日程数据到表单控件

        如果是编辑模式，从 schedule_item 中读取数据并填充到各个编辑器；
        如果是新建模式，设置默认的开始和结束时间。
        """
        if self.schedule_item:
            title = self.schedule_item.get("title")
            if title:
                self.title_editor.set_value(title)

            schedule_type = self.schedule_item.get("type")
            if schedule_type is not None:
                self.type_editor.set_value(schedule_type)  # 默认为0（其他）

            start_time_str = self.schedule_item.get("start_time")
            if start_time_str:
                self.start_time = QDateTime.fromString(start_time_str, "yyyy-MM-dd HH:mm")
                self.start_time_editor.set_value(self.start_time)

            end_time_str = self.schedule_item.get("end_time")
            if end_time_str:
                self.end_time = QDateTime.fromString(end_time_str, "yyyy-MM-dd HH:mm")
                self.end_time_editor.set_value(self.end_time)

            if self.start_time and self.end_time:
                self.duration = self.start_time.secsTo(self.end_time)

            location = self.schedule_item.get("location")
            if location:
                self.location_editor.set_value(location)

            repetition = self.schedule_item.get("repetition")
            if repetition is not None:
                self.repetition_editor.set_value(repetition)  # 默认为0（无）

            description = self.schedule_item.get("description")
            if description:
                self.description_editor.set_value(description)

        else:
            # 若无日程数据，设置默认开始与结束时间
            if (self.year is not None
                and self.month is not None
                and self.day is not None
            ):
                current_time = QDateTime(QDate(self.year, self.month, self.day), QTime.currentTime())
                # 处理跨天逻辑（凌晨4点前视为前一天）
                if current_time.time().hour() < 4:
                    current_time = current_time.addDays(1)
            else:
                current_time = QDateTime.currentDateTime()
            self.start_time = current_time.addSecs(3600)  # 加1小时
            self.start_time.setTime(QTime(self.start_time.time().hour(), 0))  # 分钟归零
            self.start_time_editor.set_value(self.start_time)
            self.end_time = self.start_time.addSecs(3600)  # 默认持续1小时
            self.end_time_editor.set_value(self.end_time)
            self.duration = self.start_time.secsTo(self.end_time)

    def on_end_time_changed(self, new_end_time):
        """
        结束时间改变时的处理，当结束时间改变时重新计算时长

        Parameters:
            new_end_time (QDateTime): 新的结束时间
        """
        self.end_time = new_end_time
        self.duration = self.start_time.secsTo(new_end_time)

    def on_start_time_changed(self, new_start_time):
        """
        开始时间改变时的处理，自动调整结束时间以保持时长不变

        Parameters:
            new_start_time (QDateTime): 新的开始时间
        """
        self.start_time = new_start_time
        self.end_time = new_start_time.addSecs(self.duration)
        with block_signals([self.end_time_editor.input_field]):
            self.end_time_editor.set_value(self.end_time)

    def save_schedule(self, copy=False):
        """
        保存日程数据

        Parameters:
            copy (bool): 是否保存为副本（不删除原日程），默认为False
        """
        title = self.title_editor.get_value().strip()
        if not title:
            title = "新日程"

        # 验证时间：结束时间不能早于开始时间
        if self.duration < 0:
            reply = QMessageBox.question(self, "保存日程",
                                    "结束时间早于开始时间，是否继续保存？",
                                    QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.No:
                return

        self.year_new, self.month_new, self.day_new = _get_date(self.start_time.toPython())

        # 计算新的ID（从事件当天凌晨4点到开始时间的分钟数）
        start_time = self.start_time.time()
        self.id_new = int(((start_time.hour() * 60 + start_time.minute()) - 240) % 1440)

        schedule_type = self.type_editor.get_value()

        start_time_str = self.start_time.toString("yyyy-MM-dd HH:mm")
        end_time_str = self.end_time.toString("yyyy-MM-dd HH:mm")

        location = self.location_editor.get_value().strip()
        if not location:
            location = None

        repetition = self.repetition_editor.get_value()

        description = self.description_editor.get_value().strip()
        if not description:
            description = None

        # 构建日程数据
        self.schedule_data = {
            "title": title,
            "type": schedule_type,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "location": location,
            "repetition": repetition,
            "description": description
        }

        # 调用父窗口的保存方法
        self.parent().window().save_schedule_from_editor(self, copy=copy)

        # 关闭窗口
        self.close()

    def delete_schedule(self):
        """删除当前日程（需用户确认）"""
        reply = QMessageBox.question(self, "确认删除",
                                   "确认删除？",
                                   QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Yes)

        if reply == QMessageBox.StandardButton.Yes:
            # 调用父窗口的删除方法
            self.parent().window().delete_schedule_from_editor(self)

            # 关闭窗口
            self.close()