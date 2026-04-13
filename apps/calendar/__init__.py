import json
import os
import time
import datetime

from sortedcontainers import SortedDict
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QScrollArea, QPushButton
from PySide6.QtCore import Qt

from core.base_window import BaseWindow
from core.functions import get_today
from .schedule_editor import ScheduleEditorWindow


data_dir = os.path.join(os.path.dirname(__file__), "data")
file_path = os.path.join(data_dir, "schedules.json")

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
        
        self.layout = QVBoxLayout(self)

        self.title_label = QLabel(schedule_item["title"])
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        self.title_label.setWordWrap(True)
        self.layout.addWidget(self.title_label)

        if "start_time" and "end_time" in schedule_item and schedule_item["start_time"] and schedule_item["end_time"]:
            self.time_label = QLabel(f"{schedule_item['start_time']} - {schedule_item['end_time']}")
            self.time_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.layout.addWidget(self.time_label)
        
        if "location" in schedule_item and schedule_item["location"]:
            self.location_label = QLabel(schedule_item['location'])
            self.location_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.layout.addWidget(self.location_label)

        if "description" in schedule_item and schedule_item["description"]:
            self.description_label = QLabel(schedule_item["description"])
            self.description_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.description_label.setWordWrap(True)
            self.layout.addWidget(self.description_label)

    def mousePressEvent(self, event):
         # 打开日程编辑窗口
         editor = ScheduleEditorWindow(self, self.schedule_item, self.schedule_id)
         editor.show()
        
class CalendarWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.schedules = self.load_schedules()
        self.init_ui()

    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("日程")
        self.setMinimumSize(600, 400)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
       
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.scroll_area.setWidget(self.container)
        self.setCentralWidget(self.scroll_area)

        self.create_floating_button()

        self.refresh_schedules()

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

    def open_new_schedule(self):
        """打开新增日程窗口"""
        editor = ScheduleEditorWindow(self)
        editor.show()

    def load_schedules(self):
        """从文件加载日程数据"""
        if os.path.exists(file_path):
            # 若文件读取失败，应报错
            with open(file_path, 'r', encoding='utf-8') as f:
                return SortedDict(json.load(f))
        return SortedDict()

    def refresh_schedules(self):
        """刷新日程显示"""
        # 清空现有布局（包括所有widget和stretch）
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 重新加载数据
        self.schedules = self.load_schedules()
        
        # 添加日程项
        for schedule_id, schedule in self.schedules.items():
            self.layout.addWidget(ScheduleItemWidget(schedule, schedule_id))

        # 添加stretch，确保日程项在顶部，空白在底部
        self.layout.addStretch()
    
    def save_schedule(self, schedule_editor):
        """保存日程到文件"""
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)

        year_old = str(schedule_editor.year).zfill(4) if schedule_editor.year else None
        month_old = str(schedule_editor.month).zfill(2) if schedule_editor.month else None
        day_old = str(schedule_editor.day).zfill(2) if schedule_editor.day else None
        id_old = schedule_editor.id if schedule_editor.id else None

        year_new = str(schedule_editor.year_new).zfill(4)
        month_new = str(schedule_editor.month_new).zfill(2)
        day_new = str(schedule_editor.day_new).zfill(2)
        id_new = schedule_editor.id_new

        # 尝试删除旧日程
        if (year_old
                and year_old in self.schedules
                and month_old in self.schedules[year_old]
                and day_old in self.schedules[year_old][month_old]
                and id_old in self.schedules[year_old][month_old][day_old]
            ):
            del self.schedules[year_old][month_old][day_old][id_old]
        
        # 初始化数据结构
        if year_new not in self.schedules:
            self.schedules[year_new] = {}
        if month_new not in self.schedules[year_new]:
            self.schedules[year_new][month_new] = {}
        if day_new not in self.schedules[year_new][month_new]:
            self.schedules[year_new][month_new][day_new] = []
        
        # 添加日程
        id_new = str(schedule_editor.id_new)
        if id_new in self.schedules[year_new][month_new][day_new]:
            seen = 0
            while str(f"{id_new}_{seen}") in self.schedules[year_new][month_new][day_new]:
                seen += 1
            id_new = f"{id_new}_{seen}"
        
        self.schedules[year_new][month_new][day_new][id_new] = schedule_editor.schedule_data

        if not self.schedules[year_old][month_old][day_old]:
            del self.schedules[year_old][month_old][day_old]
            if not self.schedules[year_old][month_old]:
                del self.schedules[year_old][month_old]
                if not self.schedules[year_old]:
                    del self.schedules[year_old]        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dict(self.schedules), f, ensure_ascii=False, indent=4)
        
        # 刷新显示
        self.refresh_schedules()
    
    def delete_schedule(self, schedule_editor):
        """从文件中删除日程"""
        year_old = str(schedule_editor.year).zfill(4) if schedule_editor.year else None
        month_old = str(schedule_editor.month).zfill(2) if schedule_editor.month else None
        day_old = str(schedule_editor.day).zfill(2) if schedule_editor.day else None
        id_old = schedule_editor.id if schedule_editor.id else None

        # 删除日程
        if (year_old and month_old and day_old and id_old and
                year_old in self.schedules and
                month_old in self.schedules[year_old] and
                day_old in self.schedules[year_old][month_old] and
                id_old in self.schedules[year_old][month_old][day_old]
        ):
            del self.schedules[year_old][month_old][day_old][id_old]
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dict(self.schedules), f, ensure_ascii=False, indent=4)
        
        # 刷新显示
        self.refresh_schedules()