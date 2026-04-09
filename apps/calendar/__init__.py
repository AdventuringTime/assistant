from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QScrollArea

from core.base_window import BaseWindow
from .schedule_editor import ScheduleEditorWindow


class ScheduleItemWidget(QWidget):
    def __init__(self, schedule_item, parent=None):
        super().__init__(parent)
        self.schedule_item = schedule_item

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
        editor = ScheduleEditorWindow(self.schedule_item, self)
        if editor.exec() == ScheduleEditorWindow.DialogCode.Accepted:
            # 如果日程被保存或删除，通知父窗口更新
            if hasattr(self.window(), 'refresh_schedules'):
                self.window().refresh_schedules()
        
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
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

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
        for schedule in self.schedules:
            self.layout.addWidget(ScheduleItemWidget(schedule))