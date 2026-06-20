import json
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QHBoxLayout,
                              QListWidget, QListWidgetItem,
                              QScrollArea, QStackedWidget)

from core.base_objects import BaseWindow
from core.widgets import SettingCategoryWidget
from core.settings_manager import SettingsManager


class SettingsWindow(BaseWindow):
    """设置窗口类，提供设置界面的管理和显示"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is not None:
            if cls._instance.isMinimized():
                cls._instance.showNormal()
            cls._instance.raise_()
            cls._instance.activateWindow()
            return cls._instance
        return super().__new__(cls)

    def __init__(self, parent=None):
        """
        初始化设置窗口

        Parameters:
            parent (QWidget, optional): 父窗口，默认为None
        """
        if SettingsWindow._initialized:
            return
        super().__init__(parent)
        self.settings_data = self.load_settings()

        self.setWindowTitle("设置")
        self.setMinimumSize(600, 400)

        # 创建中心widget
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.container.setStyleSheet("""
            QScrollArea, QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
        """)

        # 主布局（左侧类别列表 + 右侧设置内容）
        main_layout = QHBoxLayout(self.container)

        # 左侧类别列表
        self.category_scroll_area = QScrollArea()
        self.category_scroll_area.setWidgetResizable(True)
        self.category_scroll_area.setFixedWidth(180)

        self.category_list = QListWidget()
        self.category_list.currentRowChanged.connect(self.on_category_changed)
        self.category_scroll_area.setWidget(self.category_list)

        # 右侧设置内容区域（使用堆叠窗口实现页面切换）
        self.stacked_widget = QStackedWidget()
        # 预先创建所有类别的设置页面
        self.create_category_pages()
        # 添加类别到列表
        for i, category in enumerate(self.settings_data):
            self.category_list.addItem(category[0])  # 类别名称在第一个元素

        # 添加到主布局
        main_layout.addWidget(self.category_scroll_area)
        main_layout.addWidget(self.stacked_widget)

        # 默认选择第一个类别
        if self.settings_data:
            self.category_list.setCurrentRow(0)
            self.stacked_widget.setCurrentIndex(0)
        SettingsWindow._instance = self
        SettingsWindow._initialized = True

    def load_settings(self):
        """
        从JSON文件加载设置数据

        Returns:
            list: 设置数据列表，每个元素包含类别名称和子类别设置项
        """
        settings_path = os.path.join(os.path.dirname(__file__), "items.json")
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_category_pages(self):
        """预先创建所有类别的设置页面，并添加到堆叠窗口中"""
        for idx, category in enumerate(self.settings_data):
            # 创建滚动区域和内容窗口
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)

            # 使用SettingCategoryWidget类创建设置内容
            content_widget = SettingCategoryWidget(category)

            scroll_area.setWidget(content_widget)
            self.stacked_widget.addWidget(scroll_area)

    def on_category_changed(self, row):
        """
        类别切换事件处理

        Parameters:
            row (int): 新选中的类别索引
        """
        if row >= 0:
            self.stacked_widget.setCurrentIndex(row)

    def closeEvent(self, event):
        """
        关闭事件处理

        Parameters:
            event (QCloseEvent): 关闭事件对象
        """
        # 保存当前设置
        SettingsManager().save()
        super().closeEvent(event)
        SettingsWindow._instance = None
        SettingsWindow._initialized = False