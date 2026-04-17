from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                               QLineEdit, QTextEdit, QDateTimeEdit, QComboBox,
                               QCheckBox, QSpinBox)
from PySide6.QtCore import QDateTime
from glom import glom, Assign
import json
import os


class SettingItemWidget(QWidget):
    """通用设置项编辑组件，支持多种输入类型"""
    
    def __init__(self, label, field_type, placeholder=None, parent=None):
        """
        初始化设置项组件
        
        Args:
            label (str): 标签文本
            field_type (str): 字段类型，支持："text", "textarea", "datetime", "type", "bool", "int"
            placeholder (str/list of str): 占位符文本；如果为"type"，在这里输入各类型的显示文本
            config_data (dict): 配置数据（用于设置应用）
            parent: 父组件
        """
        super().__init__(parent)
        self.field_type = field_type
        
        item_layout = QHBoxLayout(self)
        
        # 项标签
        label_widget = QLabel(label)
        label_widget.setFixedWidth(80)
        label_widget.setWordWrap(True)
        item_layout.addWidget(label_widget)
        
        # 根据类型创建不同的输入控件
        if field_type == "text":
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText(placeholder)
            item_layout.addWidget(self.input_field)
        elif field_type == "textarea":
            self.input_field = QTextEdit()
            self.input_field.setPlaceholderText(placeholder)
            self.input_field.setMaximumHeight(100)
            item_layout.addWidget(self.input_field)
        elif field_type == "datetime":
            self.input_field = QDateTimeEdit()
            self.input_field.setCalendarPopup(True)
            item_layout.addWidget(self.input_field)
        elif field_type == "type":
            self.input_field = QComboBox()
            if placeholder:
                for value, text in enumerate(placeholder):
                    self.input_field.addItem(text, value)
            item_layout.addWidget(self.input_field)
        elif field_type == "bool":
            self.input_field = QCheckBox()
            item_layout.addWidget(self.input_field)
        elif field_type == "int":
            self.input_field = QSpinBox()
            item_layout.addWidget(self.input_field)
        else:
            raise ValueError(f"未知字段类型: {field_type}")
    
    def get_value(self):
        """获取输入值"""
        if self.field_type == "text":
            return self.input_field.text()
        elif self.field_type == "textarea":
            return self.input_field.toPlainText()
        elif self.field_type == "datetime":
            return self.input_field.dateTime()
        elif self.field_type == "type":
            return self.input_field.currentData()
        elif self.field_type == "bool":
            return self.input_field.isChecked()
        elif self.field_type == "int":
            return self.input_field.value()
    
    def set_value(self, value):
        """设置输入值"""
        if self.field_type == "text":
            self.input_field.setText(value)
        elif self.field_type == "textarea":
            self.input_field.setText(value)
        elif self.field_type == "datetime":
            self.input_field.setDateTime(value)
        elif self.field_type == "type":
            self.input_field.setCurrentIndex(value)
        elif self.field_type == "bool":
            self.input_field.setChecked(value)
        elif self.field_type == "int":
            self.input_field.setValue(value)
    
class SettingItemWidget_Config(SettingItemWidget):
    """配置项窗口组件"""
    def __init__(self, label, field_type, placeholder="", config_data=None, parent=None):
        super().__init__(label, field_type, placeholder, parent)

        self.config_data = config_data

        if field_type == "text":
            current_value = self.get_field_value(config_data)
            if current_value:
                self.input_field.setText(current_value)

            self.input_field.textChanged.connect(lambda text: 
                self.on_setting_changed(config_data, text))
            
        elif field_type == "textarea":
            current_value = self.get_field_value(config_data)
            if current_value:
                self.input_field.setText(current_value)

            self.input_field.textChanged.connect(lambda text: 
                self.on_setting_changed(config_data, text))
            
        elif field_type == "datetime":
            current_value = self.get_field_value(config_data)
            if current_value:
                current_value = QDateTime.fromString(current_value, "yyyy-MM-dd hh:mm:ss")
                self.input_field.setDateTime(current_value)

            self.input_field.dateTimeChanged.connect(lambda dt: 
                self.on_setting_changed(config_data, dt.toString("yyyy-MM-dd hh:mm:ss")))
            
        elif field_type == "type":
            current_value = self.get_field_value(config_data)
            if current_value:
                self.input_field.setCurrentIndex(current_value)

            self.input_field.currentIndexChanged.connect(lambda index: 
                self.on_setting_changed(config_data, index))

        elif field_type == "bool":
            current_value = self.get_field_value(config_data)
            if current_value:
                self.input_field.setChecked(current_value)

            self.input_field.stateChanged.connect(lambda state: 
                self.on_setting_changed(config_data, state))

        elif field_type == "int":
            min_val = config_data.get("min", 0)
            max_val = config_data.get("max", 100)
            self.input_field.setRange(int(min_val), int(max_val))

            current_value = self.get_field_value(config_data)
            if current_value:
                self.input_field.setValue(int(current_value))

            self.input_field.valueChanged.connect(lambda value: 
                self.on_setting_changed(config_data, value))
        
        else:
            raise ValueError(f"未知字段类型: {field_type}")
    
    def get_json_value(self, data, json_path):
        """使用glom根据JSON路径获取值"""
        return glom(data, json_path)
    
    def set_json_value(self, data, json_path, value):
        """使用glom根据JSON路径设置值"""
        glom(data, Assign(json_path, value))
    
    def get_field_value(self, field):
        """获取字段的当前值（配置数据模式）"""
        file_path = field["path"]
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self.get_json_value(data, field["json_path"])
        return field.get("default")
    
    def save_field_value(self, field, value):
        """保存字段值到对应文件（配置数据模式）"""
        file_path = field["path"]
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 读取现有数据
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}

        # 处理布尔值
        if field["type"] == "bool":
            bool_map = {0: False, 1: None, 2: True}
            value = bool_map.get(value, value)

        # 更新数据
        self.set_json_value(data, field["json_path"], value)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def on_setting_changed(self, field, value):
        """设置项改变事件（配置数据模式）"""
        self.save_field_value(field, value)

class SettingSubcategoryWidget(QWidget):
    """设置子类别窗口组件"""
    
    def __init__(self, subcategory_data, parent=None):
        super().__init__(parent)
        self.subcategory_data = subcategory_data
        
        subcategory_layout = QVBoxLayout(self)
        
        # 子类别标签
        subcategory_name = self.subcategory_data[0]
        subcategory_label = QLabel(subcategory_name)
        subcategory_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        subcategory_layout.addWidget(subcategory_label)
        
        # 设置项
        items = self.subcategory_data[1]
        for item in items:
            # 使用SettingItemWidget_Config类，传递配置数据
            item_widget = SettingItemWidget_Config(
                label=item["label"], 
                field_type=item["type"], 
                config_data=item
            )
            subcategory_layout.addWidget(item_widget)

class SettingCategoryWidget(QWidget):
    """设置内容窗口组件"""
    
    def __init__(self, category_data, parent=None):
        super().__init__(parent)
        self.category_data = category_data

        content_layout = QVBoxLayout(self)
        
        # 添加类别标题
        category_name = self.category_data[0]
        title_label = QLabel(category_name)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        content_layout.addWidget(title_label)
        
        # 子类别
        subcategories = self.category_data[1]
        for subcategory in subcategories:
            # 使用新的SettingsSubcategoryWidget类
            subcategory_widget = SettingSubcategoryWidget(subcategory)
            content_layout.addWidget(subcategory_widget)
        
        # 添加弹性空间
        content_layout.addStretch()
