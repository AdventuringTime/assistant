import json
import os
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QTableWidget, QTableWidgetItem,
                               QPushButton, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from core.base_window import BaseWindow


class GraduateWorktimeWindow(BaseWindow):
    """研招工时统计窗口类"""

    data_file_path = "apps/graduate_worktime/data/records.json"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("研招工时统计")
        self.setMinimumSize(600, 400)

        self.records = self.load_records()

        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.container.setStyleSheet("""
            QTableWidget {
                border: none;
                border-radius: 5px;
                color: #FFFFFF;
                font-size: 14px;
                outline: none;
                gridline-color: #3D3D3D;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3D3D3D;
            }
            QTableWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QTableWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QHeaderView::section {
                color: #CCCCCC;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QPushButton#clearButton {
                background-color: #D13438;
            }
            QPushButton#clearButton:hover {
                background-color: #C02B2F;
            }
            QPushButton#clearButton:pressed {
                background-color: #A8282C;
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

        main_layout = QVBoxLayout(self.container)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["日期", "内容", "时长"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().resizeSection(0, 105)
        self.table.horizontalHeader().resizeSection(2, 55)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self.on_item_changed)
        main_layout.addWidget(self.table)

        buttons_layout = QHBoxLayout()

        self.clear_button = QPushButton("清空")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.clicked.connect(self.on_clear_clicked)
        buttons_layout.addWidget(self.clear_button)

        self.export_button = QPushButton("导出")
        self.export_button.clicked.connect(self.on_export_clicked)
        buttons_layout.addWidget(self.export_button)

        buttons_layout.addStretch()

        self.delete_button = QPushButton("删除行")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        buttons_layout.addWidget(self.delete_button)

        self.add_button = QPushButton("添加行")
        self.add_button.clicked.connect(self.on_add_clicked)
        buttons_layout.addWidget(self.add_button)

        main_layout.addLayout(buttons_layout)

        self.refresh_table()

    def load_records(self):
        if os.path.exists(self.data_file_path):
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []

    def save_records(self):
        os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)
        with open(self.data_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=4)

    def refresh_table(self):
        self.table.setRowCount(0)
        for record in self.records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col in range(3):
                if col == 0:
                    item = QTableWidgetItem(record["date"])
                elif col == 1:
                    item = QTableWidgetItem(record["content"])
                else:
                    item = QTableWidgetItem(str(record["duration"]))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

    def on_clear_clicked(self):
        self.records = []
        self.save_records()
        self.refresh_table()

    def on_export_clicked(self):
        lines = []
        total_hours = 0.0
        for record in self.records:
            date_str = record["date"]
            content = record["content"]
            hours = record["duration"]
            try:
                total_hours += float(hours)
            except ValueError:
                pass
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                month = date_obj.month
                day = date_obj.day
                lines.append(f"{month}月{day}日 {content} {hours}小时")
            except ValueError:
                lines.append(f"{date_str} {content} {hours}小时")
        if lines:
            lines.append(f"总时长：{total_hours}小时")
            output = "\n".join(lines)
            QGuiApplication.clipboard().setText(output)

    def on_delete_clicked(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            self.records.pop(row)
            self.save_records()
            self.refresh_table()

    def on_item_changed(self, item):
        row = self.table.row(item)
        col = self.table.column(item)
        if 0 <= row < len(self.records):
            if col == 0:
                try:
                    datetime.strptime(item.text(), "%Y-%m-%d")
                    self.records[row]["date"] = item.text()
                except ValueError:
                    QMessageBox.warning(self, "输入非标准格式", "日期格式不是 YYYY-MM-DD，会造成导出时发生异常")
            elif col == 1:
                self.records[row]["content"] = item.text()
            elif col == 2:
                try:
                    float(item.text())
                except ValueError:
                    QMessageBox.warning(self, "输入非标准格式", "时长不是有效数字，将影响导出")
                self.records[row]["duration"] = item.text()
            self.save_records()

    def on_add_clicked(self):
        today = datetime.now().strftime("%Y-%m-%d")
        new_record = {
            "date": today,
            "content": "",
            "duration": "1.5"
        }
        self.records.append(new_record)
        self.save_records()
        self.refresh_table()

        # 自动进入对新添加行的内容的编辑
        new_row = self.table.rowCount() - 1
        content_item = self.table.item(new_row, 1)
        if content_item:
            self.table.editItem(content_item)