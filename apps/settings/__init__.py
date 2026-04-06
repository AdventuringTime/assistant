from glom import glom, Assign
import json
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QListWidget, QListWidgetItem, QFrame, QLineEdit,
                              QScrollArea, QStackedWidget)

from core.base_window import BaseWindow


class SettingsWindow(BaseWindow):
    """设置窗口类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_data = self.load_settings()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle("设置")
        self.setMinimumSize(600, 400)
        
        # 创建中心widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("""
            QScrollArea, QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
        """)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
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
        settings_path = os.path.join(os.path.dirname(__file__), "data", "settings.json")
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_category_pages(self):
        """预先创建所有类别的设置页面"""
        for idx, category in enumerate(self.settings_data):
            category_name = category[0]  # 类别名称
            subcategories = category[1]  # 子类别列表
            
            # 创建滚动区域和内容窗口
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            
            # 添加类别标题
            title_label = QLabel(category_name)
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
            content_layout.addWidget(title_label)
            
            # 子类别
            for subcategory in subcategories:
                subcategory_name = subcategory[0]  # 子类别名称
                items = subcategory[1]  # 设置项列表
                
                # 子类别标签
                subcategory_label = QLabel(subcategory_name)
                subcategory_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
                content_layout.addWidget(subcategory_label)
                
                # 设置项
                for item in items:
                    # 创建水平布局容器widget
                    field_widget = QWidget()
                    field_layout = QHBoxLayout(field_widget)
                    
                    # 项标签
                    label = QLabel(item["label"] + ":")
                    label.setFixedWidth(80)
                    field_layout.addWidget(label)
                    
                    # 获取当前值
                    current_value = self.get_field_value(item)
                    
                    if item["type"] == "text":
                        # 输入框
                        input_field = QLineEdit(current_value)
                        input_field.textChanged.connect(lambda text, field_data=item: 
                            self.on_setting_changed(field_data, text))
                        field_layout.addWidget(input_field)
                    else:
                        raise ValueError(f"未知类型: {item['type']}")
                    
                    content_layout.addWidget(field_widget)
            
            # 添加弹性空间
            content_layout.addStretch()
            
            scroll_area.setWidget(content_widget)
            self.stacked_widget.addWidget(scroll_area)
    
    def on_category_changed(self, row):
        """类别切换事件"""
        if row >= 0:
            self.stacked_widget.setCurrentIndex(row)
    
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
        
        # 更新数据
        self.set_json_value(data, field["json_path"], value)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def on_setting_changed(self, field, value):
        """设置项改变事件"""
        self.save_field_value(field, value)