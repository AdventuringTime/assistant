from sortedcontainers import SortedDict
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QScrollArea

from core.base_window import BaseWindow
from .schedule_editor import ScheduleEditorWindow


import json
import os
import time

data_dir = os.path.join(os.path.dirname(__file__), "data")
file_path = os.path.join(data_dir, "schedules.json")

class ScheduleItemWidget(QWidget):
    def __init__(self, schedule_item, schedule_id=None, parent=None):
        super().__init__(parent)
        self.schedule_item = schedule_item
        self.schedule_id = schedule_id

        self.layout = QVBoxLayout(self)

        self.title_label = QLabel(schedule_item["title"])
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.title_label.setWordWrap(True)
        self.layout.addWidget(self.title_label)

        if "start_time" and "end_time" in schedule_item:
            self.time_label = QLabel(f"{schedule_item['start_time']} - {schedule_item['end_time']}")
            self.time_label.setStyleSheet("font-size: 14px;")
            self.layout.addWidget(self.time_label)
        
        if "location" in schedule_item:
            self.location_label = QLabel(schedule_item['location'])
            self.location_label.setStyleSheet("font-size: 14px;")
            self.layout.addWidget(self.location_label)

        if "description" in schedule_item:
            self.description_label = QLabel(schedule_item["description"])
            self.description_label.setStyleSheet("font-size: 14px;")
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

        self.refresh_schedules()

    def load_schedules(self):
        """从文件加载日程数据"""
        import json
        import os
        
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        file_path = os.path.join(data_dir, "schedules.json")
        
        if os.path.exists(file_path):
            # 若文件读取失败，应报错
            with open(file_path, 'r', encoding='utf-8') as f:
                return SortedDict(json.load(f))
        return SortedDict()

    def refresh_schedules(self):
        """刷新日程显示"""
        # 清空现有布局
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 重新加载数据
        self.schedules = self.load_schedules()
        
        # 添加日程项
        for schedule_id, schedule in self.schedules.items():
            self.layout.addWidget(ScheduleItemWidget(schedule, schedule_id))
    
    def save_schedule(self, schedule_id, schedule_data):
        """保存日程到文件"""
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 读取现有数据
        if os.path.exists(file_path):
            # 若文件存在但读取失败将报错，防止数据丢失
            with open(file_path, 'r', encoding='utf-8') as f: 
                schedules = json.load(f)
        else:
            schedules = {}
        schedules = SortedDict(schedules)
        
        if schedule_id:
            # 更新日程
            schedules[schedule_id] = schedule_data
        else:
            # 初始化ID
            schedule_id = int(time.time())
            # 去重
            while schedule_id in schedules:
                schedule_id += 1

            # 添加新日程
            schedules[schedule_id] = schedule_data

        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dict(schedules), f, ensure_ascii=False, indent=4, sort_keys=True)
        
        # 刷新显示
        self.refresh_schedules()
    
    def delete_schedule(self, schedule_id):
        """从文件中删除日程"""
        if not schedule_id:
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            schedules = json.load(f)
        
        # 删除日程
        if schedule_id in schedules:
            del schedules[schedule_id]
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, ensure_ascii=False, indent=4)
        
        # 刷新显示
        self.refresh_schedules()