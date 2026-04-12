import time
from core.base_window import BaseDialog
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QTextEdit, QPushButton, QDialog,
                              QDateTimeEdit, QMessageBox)
from PySide6.QtCore import QDateTime, Qt
from PySide6.QtGui import QFont
import json
import os
from sortedcontainers import SortedDict


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


# 数据文件路径
data_dir = os.path.join(os.path.dirname(__file__), "data")
file_path = os.path.join(data_dir, "schedules.json")

class ScheduleEditorWindow(BaseDialog):
    """日程编辑窗口"""

    def __init__(self, schedule_item=None, schedule_id=None, parent=None):
        super().__init__(parent)
        self.schedule_item = schedule_item or {} # a if a else b
        self.schedule_id = schedule_id or None
        self.is_new_schedule = schedule_item is None
        
        self.init_ui()
        self.load_schedule_data()
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("日程项")
        self.setMinimumSize(500, 400)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
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
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        if not self.is_new_schedule:
            self.delete_button = QPushButton("删除")
            self.delete_button.clicked.connect(self.delete_schedule)
            self.delete_button.setStyleSheet("background-color: #ff6b6b; color: white;")
            button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
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
        if start_time:
            end_time = self.end_time_editor.get_value()
            # 验证时间
            if end_time:
                
                if start_time > end_time:
                    reply = QMessageBox.question(self, "保存日程", 
                                            "结束时间早于开始时间，是否继续保存？",
                                            QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
                    if reply == QMessageBox.StandardButton.No:
                        return
            else:
                end_time = start_time
        
            start_time_str = start_time.toString("yyyy-MM-dd HH:mm")
            end_time_str = end_time.toString("yyyy-MM-dd HH:mm")
        else:
            start_time_str = None
            end_time_str = None
        
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
        
        # 保存到文件
        self.save_to_file()
        
        # 发送信号或保存数据
        self.accept()
    
    def delete_schedule(self):
        """删除日程"""
        reply = QMessageBox.question(self, "确认删除", 
                                   "确认删除？",
                                   QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_from_file()
            self.accept()
    
    def save_to_file(self):
        """保存日程数据到文件"""
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
        
        if self.schedule_id:
            # 更新日程
            schedules[self.schedule_id] = self.schedule_data
        else:
            # 初始化ID
            self.schedule_id = int(time.time())
            # 去重
            while self.schedule_id in schedules:
                self.schedule_id += 1

            # 添加新日程
            schedules[self.schedule_id] = self.schedule_data

        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dict(schedules), f, ensure_ascii=False, indent=4, sort_keys=True)
    
    def delete_from_file(self):
        """从文件中删除日程"""
        if not self.schedule_id:
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            schedules = json.load(f)
        
        # 删除日程
        del schedules[self.schedule_id]
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, ensure_ascii=False, indent=4)