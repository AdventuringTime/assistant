import json
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QListWidget, QListWidgetItem,
                               QPushButton, QInputDialog)
from PySide6.QtCore import Qt

from core.base_window import BaseWindow


class SearchWordsWindow(BaseWindow):
    """搜索词管理窗口类"""
    
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
            QWidget { background-color: #1E1E1E; }
            QListWidget {
                background-color: #2D2D30;
                border: none;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #3D3D40;
            }
            QListWidget::item:hover {
                background-color: #3D3D40;
            }
            QListWidget::item:selected {
                background-color: #0078D4;
            }
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
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
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # 搜索词列表
        self.words_list = QListWidget()
        self.words_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        main_layout.addWidget(self.words_list)
        
        # 操作按钮区域
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.add_button = QPushButton("添加")
        self.add_button.clicked.connect(self.on_add_clicked)
        buttons_layout.addWidget(self.add_button)
        
        self.rename_button = QPushButton("重命名")
        self.rename_button.clicked.connect(self.on_rename_clicked)
        buttons_layout.addWidget(self.rename_button)
        
        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        buttons_layout.addWidget(self.delete_button)
        
        main_layout.addLayout(buttons_layout)
        
        # 刷新列表显示
        self.refresh_list()
    
    def get_words_file_path(self):
        """获取搜索词文件路径"""
        return os.path.join(os.path.dirname(__file__), "data", "words.json")
    
    def load_words(self):
        """加载搜索词数据"""
        file_path = self.get_words_file_path()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_words(self):
        """保存搜索词数据"""
        file_path = self.get_words_file_path()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.words, f, ensure_ascii=False, indent=4)
    
    def refresh_list(self):
        """刷新列表显示"""
        self.words_list.clear()
        for word in self.words:
            item = QListWidgetItem(word)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.words_list.addItem(item)
    
    def on_add_clicked(self):
        """添加搜索词"""
        word, ok = QInputDialog.getText(self, "添加搜索词", "输入搜索词：")
        
        if ok and word.strip():
            word = word.strip()
            if word not in self.words:
                self.words.append(word)
                self.save_words()
                self.refresh_list()
    
    def on_item_double_clicked(self, item):
        """双击列表项进行重命名"""
        self.rename_item(item)
    
    def on_rename_clicked(self):
        """重命名选中的搜索词"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            self.rename_item(selected_items[0])
    
    def rename_item(self, item):
        """重命名指定项"""
        old_word = item.text()
        new_word, ok = QInputDialog.getText(self, "重命名", "输入新的搜索词：", text=old_word)
        
        if ok and new_word.strip():
            new_word = new_word.strip()
            if new_word != old_word:
                index = self.words.index(old_word)
                self.words[index] = new_word
                self.save_words()
                self.refresh_list()
    
    def on_delete_clicked(self):
        """删除选中的搜索词"""
        selected_items = self.words_list.selectedItems()
        if selected_items:
            word = selected_items[0].text()
            self.words.remove(word)
            self.save_words()
            self.refresh_list()