from PySide6.QtWidgets import QSpinBox
from PySide6.QtWidgets import QCheckBox
from glom import glom, Assign
import json
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QListWidget, QListWidgetItem, QFrame, QLineEdit,
                              QScrollArea, QStackedWidget)

from core.base_window import BaseWindow


bool_map = {0: False, 1: None, 2: True}


class SettingItemWidget(QWidget):
    """单个设置项窗口组件"""
    
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        
        item_layout = QHBoxLayout(self)
        
        # 项标签
        label = QLabel(self.item_data["label"])
        label.setFixedWidth(80)
        item_layout.addWidget(label)
        
        # 获取当前值
        current_value = self.get_field_value(self.item_data)
        
        if self.item_data["type"] == "text":
            # 输入框
            input_field = QLineEdit(current_value)
            input_field.textChanged.connect(lambda text, field_data=self.item_data: 
                self.on_setting_changed(field_data, text))
            item_layout.addWidget(input_field)
        elif self.item_data["type"] == "bool":
            # 复选框
            checkbox = QCheckBox()
            checkbox.setChecked(current_value)
            checkbox.stateChanged.connect(lambda state, field_data=self.item_data: 
                self.on_setting_changed(field_data, state))
            item_layout.addWidget(checkbox)
        elif self.item_data["type"] == "int":
            # 整数输入框
            spinbox = QSpinBox()
            spinbox.setRange(int(self.item_data.get("min")), int(self.item_data.get("max")))
            spinbox.setValue(int(current_value))
            spinbox.valueChanged.connect(lambda value, field_data=self.item_data: 
                self.on_setting_changed(field_data, value))
            item_layout.addWidget(spinbox)
        else:
            raise ValueError(f"未知类型: {self.item_data['type']}")

    def get_json_value(self, data, json_path):
        """使用glom根据JSON路径获取值"""
        return glom(data, json_path)
    
    def set_json_value(self, data, json_path, value):
        """使用glom根据JSON路径设置值"""
        glom(data, Assign(json_path, value))
            
    def get_field_value(self, field):
        """获取字段的当前值"""
        file_path = field["path"]
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self.get_json_value(data, field["json_path"])
        return field.get("default")
    
    def save_field_value(self, field, value):
        """保存字段值到对应文件"""
        file_path = field["path"]
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 读取现有数据
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 处理布尔值
        if field["type"] == "bool":
            value = bool_map[value]

        # 更新数据
        self.set_json_value(data, field["json_path"], value)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def on_setting_changed(self, field, value):
        """设置项改变事件"""
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
            # 使用新的SettingItemWidget类
            item_widget = SettingItemWidget(item)
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
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        content_layout.addWidget(title_label)
        
        # 子类别
        subcategories = self.category_data[1]
        for subcategory in subcategories:
            # 使用新的SettingsSubcategoryWidget类
            subcategory_widget = SettingSubcategoryWidget(subcategory)
            content_layout.addWidget(subcategory_widget)
        
        # 添加弹性空间
        content_layout.addStretch()

class SettingsWindow(BaseWindow):
    """设置窗口类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_data = self.load_settings()

        self.setWindowTitle("设置")
        self.setMinimumSize(600, 400)
        
        # 创建中心widget
        container = QWidget()
        self.setCentralWidget(container)
        container.setStyleSheet("""
            QScrollArea, QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
        """)
        
        # 主布局
        main_layout = QHBoxLayout(container)
        
        # 左侧类别列表
        self.category_scroll_area = QScrollArea()
        self.category_scroll_area.setWidgetResizable(True)
        self.category_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.category_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.category_scroll_area.setFixedWidth(180)

        self.category_list = QListWidget()
        self.category_list.currentRowChanged.connect(self.on_category_changed)
        self.category_scroll_area.setWidget(self.category_list)
        
        # 右侧设置内容区域
        self.stacked_widget = QStackedWidget()
        # 预先创建所有类别的设置页面
        self.create_category_pages()
        # 添加类别到列表
        for i, category in enumerate(self.settings_data):
            item = QListWidgetItem(category[0])  # 类别名称在第一个元素
            self.category_list.addItem(item)
                
        # 添加到主布局
        main_layout.addWidget(self.category_scroll_area)
        main_layout.addWidget(self.stacked_widget)
        
        # 默认选择第一个类别
        if self.settings_data:
            self.category_list.setCurrentRow(0)
            self.stacked_widget.setCurrentIndex(0)
    
    def load_settings(self):
        """加载设置数据"""
        settings_path = os.path.join(os.path.dirname(__file__), "items.json")
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_category_pages(self):
        """预先创建所有类别的设置页面"""
        for idx, category in enumerate(self.settings_data):
            # 创建滚动区域和内容窗口
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            # 使用新的SettingsContentWidget类
            content_widget = SettingCategoryWidget(category)
            
            scroll_area.setWidget(content_widget)
            self.stacked_widget.addWidget(scroll_area)
    
    def on_category_changed(self, row):
        """类别切换事件"""
        if row >= 0:
            self.stacked_widget.setCurrentIndex(row)
