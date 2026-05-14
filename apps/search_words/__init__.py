import json
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QListWidget, QListWidgetItem,
                               QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from core.base_window import BaseWindow


class SearchWordsWindow(BaseWindow):
    """搜索词管理窗口类"""

    words_file_path = "apps/search_words/data/words.json"

    def __init__(self, parent=None):
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
                background-color: rgba(255, 255, 255, 0.1);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton#deleteButton {
                background-color: #D13438;
            }
            QPushButton#deleteButton:hover {
                background-color: #C02B2F;
            }
            QPushButton#deleteButton:pressed {
                background-color: #A8282C;
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

        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        buttons_layout.addWidget(self.delete_button)

        main_layout.addLayout(buttons_layout)

        # 初始化列表显示
        self.refresh_list()

    def load_words(self):
        """加载搜索词数据"""
        if os.path.exists(self.words_file_path):
            with open(self.words_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            os.makedirs(os.path.dirname(self.words_file_path), exist_ok=True)
            with open(self.words_file_path, 'w', encoding='utf-8') as f:
                f.write("[]")
            return []

    def save_words(self):
        """保存搜索词数据"""
        with open(self.words_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.words, f, ensure_ascii=False, indent=4)

    def refresh_list(self):
        """刷新列表显示"""
        self.words_list.clear()
        for word in self.words:
            item = QListWidgetItem(word)
            item.setFlags(item.flags() |
                         Qt.ItemFlag.ItemIsSelectable |
                         Qt.ItemFlag.ItemIsEnabled |
                         Qt.ItemFlag.ItemIsEditable)
            self.words_list.addItem(item)

    def on_item_changed(self, item):
        """列表项内容改变时自动保存"""
        row = self.words_list.row(item)
        new_text = item.text().strip()

        self.words[row] = new_text
        self.save_words()

    def on_add_clicked(self):
        """添加搜索词：在最后加一个空项并触发编辑"""
        self.words.append("")
        self.refresh_list()
        # 编辑最后一项
        last_item = self.words_list.item(self.words_list.count() - 1)
        if last_item:
            self.words_list.editItem(last_item)

    def on_copy_clicked(self):
        """复制选中的搜索词到剪贴板"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            text = selected_items[0].text()
            QGuiApplication.clipboard().setText(text)

    def on_rename_clicked(self):
        """重命名选中的搜索词"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            self.words_list.editItem(selected_items[0])

    def on_delete_clicked(self):
        """删除选中的搜索词"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            row = self.words_list.row(selected_items[0])
            self.words.pop(row)
            self.save_words()
            self.refresh_list()