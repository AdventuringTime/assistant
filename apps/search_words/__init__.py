import json
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QListWidget, QListWidgetItem,
                               QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from core.base_objects import BaseWindow, DeleteButton


class SearchWordsWindow(BaseWindow):
    """搜索词管理窗口，用于管理和维护搜索词列表"""

    words_file_path = "apps/search_words/data/words.json"

    def __init__(self, parent=None):
        """
        初始化搜索词管理窗口

        Parameters:
            parent (QWidget, optional): 父窗口
        """
        super().__init__(parent)

        self.setWindowTitle("搜索词")
        self.setMinimumSize(400, 300)

        # 加载搜索词数据
        self.words = self.load_words()

        # 创建中心widget
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.container.setStyleSheet("""
            QListWidget {
                background-color: #2D2D30;
                border: none;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #3D3D3D;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)

        # 主布局
        main_layout = QVBoxLayout(self.container)

        # 搜索词列表
        self.words_list = QListWidget()
        self.words_list.itemChanged.connect(self.on_item_changed)
        main_layout.addWidget(self.words_list)

        # 操作按钮区域
        buttons_layout = QHBoxLayout()

        buttons_layout.addStretch()

        self.add_button = QPushButton("添加")
        self.add_button.clicked.connect(self.on_add_clicked)
        buttons_layout.addWidget(self.add_button)

        self.copy_button = QPushButton("复制")
        self.copy_button.clicked.connect(self.on_copy_clicked)
        buttons_layout.addWidget(self.copy_button)

        self.rename_button = QPushButton("重命名")
        self.rename_button.clicked.connect(self.on_rename_clicked)
        buttons_layout.addWidget(self.rename_button)

        self.delete_button = DeleteButton("删除")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        buttons_layout.addWidget(self.delete_button)

        main_layout.addLayout(buttons_layout)

        # 初始化列表显示
        self.refresh_list()

    def load_words(self):
        """
        从文件加载搜索词数据，若文件不存在则创建空文件

        Returns:
            list: 搜索词列表
        """
        if os.path.exists(self.words_file_path):
            with open(self.words_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            os.makedirs(os.path.dirname(self.words_file_path), exist_ok=True)
            with open(self.words_file_path, 'w', encoding='utf-8') as f:
                f.write("[]")
            return []

    def save_words(self):
        """保存搜索词数据到文件"""
        with open(self.words_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.words, f, ensure_ascii=False, indent=4)

    def refresh_list(self):
        """刷新搜索词列表显示，将words数据加载到列表控件中"""
        self.words_list.clear()
        for word in self.words:
            item = QListWidgetItem(word)
            item.setFlags(item.flags() |
                         Qt.ItemFlag.ItemIsSelectable |
                         Qt.ItemFlag.ItemIsEnabled |
                         Qt.ItemFlag.ItemIsEditable)
            self.words_list.addItem(item)

    def on_item_changed(self, item):
        """
        列表项内容改变时自动保存到文件

        Parameters:
            item (QListWidgetItem): 修改后的列表项
        """
        row = self.words_list.row(item)
        new_text = item.text().strip()

        self.words[row] = new_text
        self.save_words()

    def on_add_clicked(self):
        """添加新搜索词，在列表末尾添加空项并自动进入编辑状态"""
        self.words.append("")
        self.refresh_list()
        # 编辑最后一项
        last_item = self.words_list.item(self.words_list.count() - 1)
        if last_item:
            self.words_list.scrollToItem(last_item)
            self.words_list.editItem(last_item)

    def on_copy_clicked(self):
        """将选中的搜索词复制到系统剪贴板"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            text = selected_items[0].text()
            QGuiApplication.clipboard().setText(text)

    def on_rename_clicked(self):
        """触发选中搜索词的编辑状态以进行重命名"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            self.words_list.scrollToItem(selected_items[0])
            self.words_list.editItem(selected_items[0])

    def on_delete_clicked(self):
        """删除选中的搜索词并保存"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            row = self.words_list.row(selected_items[0])
            self.words.pop(row)
            self.save_words()
            self.refresh_list()