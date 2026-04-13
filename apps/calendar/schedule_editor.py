from datetime import datetime

from core.base_window import BaseWindow
from core.functions import get_today
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QTextEdit, QPushButton,
                              QDateTimeEdit, QMessageBox)
from PySide6.QtCore import QDateTime


def _get_date(time):
    schedule_date = get_today(time)
    
    year = schedule_date.year
    month = schedule_date.month
    day = schedule_date.day

    return year, month, day

class ScheduleItemEditor(QWidget):
    """单个日程项编辑组件"""
    
    def __init__(self, label, field_type, placeholder="", parent=None):
        super().__init__(parent)
        self.field_type = field_type
        
        item_layout = QHBoxLayout(self)
        
        # 项标签
        label_widget = QLabel(label)
        label_widget.setFixedWidth(80)
        item_layout.addWidget(label_widget)
        
        # 根据类型创建不同的输入控件
        if field_type == "text":
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText(placeholder)
            item_layout.addWidget(self.input_field)
        elif field_type == "datetime":
            self.input_field = QDateTimeEdit()
            self.input_field.setCalendarPopup(True)
            self.input_field.setDateTime(QDateTime.currentDateTime())
            item_layout.addWidget(self.input_field)
        elif field_type == "textarea":
            self.input_field = QTextEdit()
            self.input_field.setPlaceholderText(placeholder)
            self.input_field.setMaximumHeight(100)
            item_layout.addWidget(self.input_field)
        else:
            raise ValueError(f"未知字段类型: {field_type}")
    
    def get_value(self):
        """获取输入值"""
        if self.field_type == "text":
            return self.input_field.text()
        elif self.field_type == "datetime":
            return self.input_field.dateTime()
        elif self.field_type == "textarea":
            return self.input_field.toPlainText()
    
    def set_value(self, value):
        """设置输入值"""
        if self.field_type == "text":
            self.input_field.setText(value)
        elif self.field_type == "datetime":
            self.input_field.setDateTime(value)
        elif self.field_type == "textarea":
            self.input_field.setText(value)


class ScheduleEditorWindow(BaseWindow):
    """日程编辑窗口"""

    def __init__(self, parent, schedule_item=None, schedule_id=None):
        super().__init__(parent)
        self.schedule_item = schedule_item or {} # a if a else b
        self.is_new_schedule = schedule_item is None

        if schedule_item:
            self.year, self.month, self.day = _get_date(datetime.strptime(schedule_item["start_time"], "%Y-%m-%d %H:%M"))
        else:
            self.year, self.month, self.day = None, None, None
        self.id = schedule_id
        
        self.init_ui()
        self.load_schedule_data()

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
        self.title_editor = ScheduleItemEditor("标题", "text", "新日程")
        self.start_time_editor = ScheduleItemEditor("开始时间", "datetime")
        self.end_time_editor = ScheduleItemEditor("结束时间", "datetime")
        self.location_editor = ScheduleItemEditor("地点", "text")
        self.description_editor = ScheduleItemEditor("描述", "textarea")
        
        # 添加日程项到主布局
        main_layout.addWidget(self.title_editor)
        main_layout.addWidget(self.start_time_editor)
        main_layout.addWidget(self.end_time_editor)
        main_layout.addWidget(self.location_editor)
        main_layout.addWidget(self.description_editor)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_schedule)
        
        if not self.is_new_schedule:
            self.delete_button = QPushButton("删除")
            self.delete_button.clicked.connect(self.delete_schedule)
            self.delete_button.setStyleSheet("background-color: #ff6b6b; color: white;")
            button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        
        main_layout.addLayout(button_layout)
        
    def load_schedule_data(self):
        """加载日程数据到表单"""
        if self.schedule_item:
            title = self.schedule_item.get("title")
            if title:
                self.title_editor.set_value(title)
            
            start_time_str = self.schedule_item.get("start_time")
            if start_time_str:
                start_time = QDateTime.fromString(start_time_str, "yyyy-MM-dd HH:mm")
                self.start_time_editor.set_value(start_time)
            
            end_time_str = self.schedule_item.get("end_time")
            if end_time_str:
                end_time = QDateTime.fromString(end_time_str, "yyyy-MM-dd HH:mm")
                self.end_time_editor.set_value(end_time)
            
            location = self.schedule_item.get("location")
            if location:
                self.location_editor.set_value(location)
            
            description = self.schedule_item.get("description")
            if description:
                self.description_editor.set_value(description)
    
    def save_schedule(self):
        """保存日程"""
        title = self.title_editor.get_value().strip()
        if not title:
            title = "新日程"
        
        start_time = self.start_time_editor.get_value()
        end_time = self.end_time_editor.get_value()
        if not start_time or not end_time:
            # 开始时间和结束时间必填
            QMessageBox.warning(self, "保存日程", "开始时间和结束时间不能为空")
            return
        # 验证时间
        if start_time > end_time:
            reply = QMessageBox.question(self, "保存日程", 
                                    "结束时间早于开始时间，是否继续保存？",
                                    QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.No:
                return
            
        self.year_new, self.month_new, self.day_new = _get_date(start_time.toPython())

        # 计算新的id
        current_time = start_time.time()
        self.id_new = int(((current_time.hour() * 60 + current_time.minute()) - 240) % 1440)

        start_time_str = start_time.toString("yyyy-MM-dd HH:mm")
        end_time_str = end_time.toString("yyyy-MM-dd HH:mm")

        location = self.location_editor.get_value().strip()
        if not location:
            location = None
        
        description = self.description_editor.get_value().strip()
        if not description:
            description = None
        
        # 构建日程数据
        self.schedule_data = {
            "title": title,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "location": location,
            "description": description
        }

        # 调用父窗口的保存方法
        self.parent().window().save_schedule(self)
        
        # 关闭窗口
        self.close()
    
    def delete_schedule(self):
        """删除日程"""
        reply = QMessageBox.question(self, "确认删除", 
                                   "确认删除？",
                                   QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)
        
        if reply == QMessageBox.StandardButton.Ok:
            # 调用父窗口的删除方法
            self.parent().window().delete_schedule(self)
            
            # 关闭窗口
            self.close()