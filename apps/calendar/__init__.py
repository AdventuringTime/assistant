from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QScrollArea

from core.base_window import BaseWindow


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
        self.show_schedule(self.schedule_item) # TODO: 点击后打开日程窗口
        
class CalendarWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.schedules = self.load_schedules() #TODO: 从数据库加载日程
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

        for schedule in self.schedules:
            self.layout.addWidget(ScheduleItemWidget(schedule))
