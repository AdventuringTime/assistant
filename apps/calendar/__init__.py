import json
import os
import time
import datetime

from sortedcontainers import SortedDict
from PySide6.QtWidgets import (QLabel, QWidget, QVBoxLayout, QScrollArea,
                               QPushButton, QDateEdit)
from PySide6.QtCore import Qt, QDate, QEvent

from core.base_window import BaseWindow
from core.functions import get_today
from .schedule_editor import ScheduleEditorWindow


data_dir = "apps/calendar/data"

class PlaceLabel(QLabel):
    def __init__(self, text, parent=None):
        if text.startswith("https://"):
            super().__init__(f'<a href="{text}">{text}</a>', parent)
        else:
            super().__init__(text, parent)
        self.setMouseTracking(True)
        self.is_hovering_link = False
        self.setOpenExternalLinks(True)
        self.linkHovered.connect(self.onLinkHovered)

    def onLinkHovered(self, link):
        """当悬停状态改变时调用"""
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
        """事件过滤器：拦截父控件的事件"""
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
    def __init__(self, schedule_item, schedule_id=None, parent=None):
        super().__init__(parent)
        self.schedule_item = schedule_item
        self.schedule_id = schedule_id

        # 设置悬停效果样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            ScheduleItemWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.layout_ = QVBoxLayout(self)

        self.title_label = QLabel(schedule_item["title"])
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        self.title_label.setWordWrap(True)
        self.layout_.addWidget(self.title_label)

        if "start_time" and "end_time" in schedule_item and schedule_item["start_time"] and schedule_item["end_time"]:
            self.time_label = QLabel(f"{schedule_item['start_time']} - {schedule_item['end_time']}")
            self.time_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.layout_.addWidget(self.time_label)
        
        if "location" in schedule_item and schedule_item["location"]:
            self.location_label = PlaceLabel(schedule_item['location'])
            self.location_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.location_label.setWordWrap(True)
            self.layout_.addWidget(self.location_label)

        if "description" in schedule_item and schedule_item["description"]:
            self.description_label = QLabel(schedule_item["description"])
            self.description_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.description_label.setWordWrap(True)
            self.layout_.addWidget(self.description_label)

    def mousePressEvent(self, event):
         # 打开日程编辑窗口
         editor = ScheduleEditorWindow(self, self.schedule_item, self.schedule_id)
         editor.show()
        
class CalendarWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("日程")
        self.setMinimumSize(600, 400)

        self.container = QWidget()
        self.setCentralWidget(self.container)

        self.container_layout = QVBoxLayout(self.container)

        self.date_selector = QDateEdit(self.container)
        self.date_selector.setFixedHeight(30)
        self.date_selector.setCalendarPopup(True)
        self.container_layout.addWidget(self.date_selector)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.container_layout.addWidget(self.scroll_area)
       
        self.create_floating_button()

        self.date_selector.dateChanged.connect(self.on_date_changed)
        today = get_today()
        self.date_selector.setDate(QDate(today.year, today.month, today.day))

    def create_floating_button(self):
        """创建右下角悬浮按钮"""
        # 创建悬浮按钮
        self.floating_button = QPushButton("+", self)
        self.floating_button.setFixedSize(60, 60)
        self.floating_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border-radius: 30px;
                font-size: 24px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """)
        
        # 设置按钮位置（右下角，距离边缘20px）
        self.floating_button.move(self.width() - 80, self.height() - 80)
        
        # 连接点击事件
        self.floating_button.clicked.connect(self.open_new_schedule)
        
        # 设置按钮始终在最前面
        self.floating_button.raise_()

    def resizeEvent(self, event):
        """窗口大小改变事件，保持按钮在右下角"""
        super().resizeEvent(event)
        if hasattr(self, 'floating_button'):
            self.floating_button.move(self.width() - 80, self.height() - 80)

    def on_date_changed(self, date):
        """日期改变时的处理函数"""
        self.year_displayed = date.year()
        self.month_displayed = date.month()
        self.day_displayed = date.day()

        self.refresh_schedules()

    def open_new_schedule(self):
        """打开新增日程窗口"""
        editor = ScheduleEditorWindow(
            self,
            year=self.year_displayed,
            month=self.month_displayed,
            day=self.day_displayed
        )
        editor.show()

    def load_schedules(self, year, month, day):
        """从文件加载日程数据"""
        file_path = os.path.join(data_dir, str(year), str(month), str(day) + ".json")
        if os.path.exists(file_path):
            # 若文件读取失败，应报错
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def refresh_schedules(self):
        """刷新日程显示"""
        # 清空现有布局（包括所有widget和stretch）
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新加载数据
        self.schedules = self.load_schedules(self.year_displayed, self.month_displayed, self.day_displayed)
        
        # 添加日程项
        for schedule_id, schedule in self.schedules.items():
            self.scroll_layout.addWidget(ScheduleItemWidget(schedule, schedule_id))

        # 添加stretch，确保日程项在顶部，空白在底部
        self.scroll_layout.addStretch()

    def save_schedule(self, schedule_editor, copy=False):
        """
            保存日程到文件。

            :param schedule_editor: 日程编辑器窗口实例。
        """
        year_new = schedule_editor.year_new
        month_new = schedule_editor.month_new
        day_new = schedule_editor.day_new
        id_new = schedule_editor.id_new
        
        # 读取日程
        file_path = os.path.join(data_dir, str(year_new), str(month_new), str(day_new) + ".json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                schedules = SortedDict(json.load(f))
        else:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            schedules = SortedDict()
        
        # 添加日程
        id_new = str(schedule_editor.id_new)
        if id_new in schedules:
            seen = 0
            while (str(f"{id_new}_{str(seen).zfill(3)}") in schedules or
                   (copy and (schedule_editor.year == year_new
                    and schedule_editor.month == month_new
                    and schedule_editor.day == day_new
                    and schedule_editor.id == id_new
            ))):
                seen += 1
            id_new = f"{id_new}_{str(seen).zfill(3)}"
        
        schedules[id_new] = schedule_editor.schedule_data

        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dict(schedules), f, ensure_ascii=False, indent=4)
        
        # 如果旧日程与新日程id不同，尝试删除旧日程
        if not copy and (schedule_editor.year != year_new
            or schedule_editor.month != month_new
            or schedule_editor.day != day_new
            or schedule_editor.id != id_new
        ):
            self.delete_schedule(schedule_editor)

        if (self.year_displayed == year_new
            and self.month_displayed == month_new
            and self.day_displayed == day_new
        ):
            self.refresh_schedules()
    
    def delete_schedule(self, schedule_editor):
        """
            从文件中删除日程。

            :param schedule_editor: 日程编辑器窗口实例。
        """
        year_old = schedule_editor.year
        month_old = schedule_editor.month
        day_old = schedule_editor.day
        id_old = schedule_editor.id

        # 检查文件是否存在
        if not year_old:
            return
        file_path = os.path.join(data_dir, str(year_old), str(month_old), str(day_old) + ".json")
        if not os.path.exists(file_path):
            return

        # 删除日程
        with open(file_path, 'r', encoding='utf-8') as f:
            schedules = json.load(f)
        if id_old in schedules:
            del schedules[id_old]
        
        # 保存文件；如果日程被清空，删除文件
        if schedules:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(schedules, f, ensure_ascii=False, indent=4)
        else:
            os.remove(file_path)

        if (self.year_displayed == year_old
            and self.month_displayed == month_old
            and self.day_displayed == day_old
        ):
            self.refresh_schedules()