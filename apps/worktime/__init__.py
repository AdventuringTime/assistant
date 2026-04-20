import json
import os
import datetime

from PySide6.QtWidgets import (QLabel, QWidget, QVBoxLayout, QScrollArea,
                               QPushButton, QDateEdit)
from PySide6.QtCore import Qt, QDate

from core.base_window import BaseWindow
from core.functions import get_today
from .editor import EditorWindow


data_dir = "apps/worktime/data"

class ItemWidget(QWidget):
    def __init__(self, year, month, day, item, id_=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.year = year
        self.month = month
        self.day = day
        self.id_ = id_

        # 设置悬停效果样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            ItemWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.layout_ = QVBoxLayout(self)

        total_work = item.get("total_work")
        if total_work:
            hours, minutes = map(int, total_work.split(':'))
        else:
            import re
            from_time = datetime.time.strptime(item['from'], '%H:%M')
            to_time = datetime.time.strptime(item['to'], '%H:%M')
            rest_time_match = re.search(r'(\d{1,2}):(\d{1,2})', item.get("rest", "00:00"))
            if rest_time_match:
                rest_time = datetime.timedelta(hours=int(rest_time_match.group(1)), minutes=int(rest_time_match.group(2)))
            if to_time <= from_time:
                to_time += datetime.timedelta(days=1)
            diff = to_time - from_time - rest_time
            hours, minutes = divmod(diff.seconds // 60, 60)

        parts = ""
        if hours > 0:
            parts += f"{hours}小时"
        if minutes > 0:
            parts += f"{minutes}分钟"
        total_work = parts if parts else "0分钟"

        self.main_label = QLabel(f"{total_work} ({item['from']} - {item['to']})")
        self.main_label.setStyleSheet("font-size: 16px; color: #FFFFFF;")
        self.layout_.addWidget(self.main_label)
        
        if item.get("description"):
            self.description_label = QLabel(item["description"])
            self.description_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.description_label.setWordWrap(True)
            self.layout_.addWidget(self.description_label)

    def mousePressEvent(self, event):
         # 打开编辑窗口
         editor = EditorWindow(self, self.year, self.month, self.day, self.item, self.id_)
         editor.show()
        
class WorktimeWindow(BaseWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.worktimes = {}

        self.setWindowTitle("工作时间记录")
        self.setMinimumSize(600, 400)

        self.container = QWidget()
        self.setCentralWidget(self.container)

        self.container_layout = QVBoxLayout(self.container)

        self.date_selector = QDateEdit(self.container)
        self.date_selector.setFixedHeight(30)
        self.date_selector.setCalendarPopup(True)
        self.container_layout.addWidget(self.date_selector)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.container_layout.addWidget(self.scroll_area)
       
        self.create_floating_button()

        self.date_selector.dateChanged.connect(self.on_date_changed)
        today = get_today()
        self.date_selector.setDate(QDate(today.year, today.month, today.day))

    def create_floating_button(self):
        """创建右下角悬浮按钮"""
        # 创建悬浮按钮
        self.floating_button = QPushButton("+", self)
        self.floating_button.setFixedSize(60, 60)
        self.floating_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border-radius: 30px;
                font-size: 24px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """)
        
        # 设置按钮位置（右下角，距离边缘20px）
        self.floating_button.move(self.width() - 80, self.height() - 80)
        
        # 连接点击事件
        self.floating_button.clicked.connect(self.open_new_editor)
        
        # 设置按钮始终在最前面
        self.floating_button.raise_()

    def resizeEvent(self, event):
        """窗口大小改变事件，保持按钮在右下角"""
        super().resizeEvent(event)
        if hasattr(self, 'floating_button'):
            self.floating_button.move(self.width() - 80, self.height() - 80)

    def on_date_changed(self, date):
        """日期改变时的处理函数"""
        self.year_displayed = date.year()
        self.month_displayed = date.month()
        self.day_displayed = date.day()

        self.refresh_data()

    def open_new_editor(self):
        """打开新增工作时间记录窗口"""
        editor = EditorWindow(self, self.year_displayed, self.month_displayed, self.day_displayed)
        editor.show()

    def load_worktimes(self, year, month):
        """从文件加载工作时间记录数据"""
        file_path = os.path.join(data_dir, str(year)[2:], str(month) + ".json")

        if year not in self.worktimes:
            self.worktimes[year] = {}

        if os.path.exists(file_path):
            # 若文件读取失败，应报错
            with open(file_path, 'r', encoding='utf-8') as f:
                self.worktimes[year][month] = json.load(f)
        else:
            self.worktimes[year][month] = {}

        return self.worktimes[year][month]

    def save_worktimes(self, year, month, data):
        """保存工作时间记录数据到文件"""
        file_path = os.path.join(data_dir, str(year)[2:], str(month) + ".json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get_worktimes_of_month(self, year, month):
        """获取指定月份的工作时间记录"""
        if (year in self.worktimes
            and month in self.worktimes[year]
        ):
            return self.worktimes[year][month]
        else:
            return self.load_worktimes(year, month)

    def refresh_data(self):
        """刷新工作时间记录显示"""
        # 清空现有布局（包括所有widget和stretch）
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 根据需要加载数据
        self.worktimes_of_month = self.get_worktimes_of_month(self.year_displayed, self.month_displayed)
        
        # 添加工作时间记录项
        if str(self.day_displayed) in self.worktimes_of_month:
            for id_, worktime in enumerate(self.worktimes_of_month[str(self.day_displayed)]):
                self.scroll_layout.addWidget(ItemWidget(
                    self.year_displayed,
                    self.month_displayed,
                    self.day_displayed,
                    worktime, id_
                ))

        # 添加stretch，确保工作时间记录项在顶部，空白在底部
        self.scroll_layout.addStretch()

    def save_worktime_of_editor(self, worktime_editor, copy=False):
        """
            保存工作时间记录到文件。

            :param worktime_editor: 工作时间记录编辑器窗口实例。
        """
        year = worktime_editor.year
        month = worktime_editor.month
        day = worktime_editor.day
        id_ = worktime_editor.id_
        
        # 读取工作时间记录
        worktimes_of_month = self.get_worktimes_of_month(year, month)
        
        # 修改工作时间记录
        if str(day) not in worktimes_of_month:
            worktimes_of_month[str(day)] = []
        if not copy and id_ is not None:
            worktimes_of_month[str(day)][id_] = worktime_editor.data_dict
        else:
            worktimes_of_month[str(day)].append(worktime_editor.data_dict)

        # 保存修改
        self.save_worktimes(year, month, worktimes_of_month)

        if (self.year_displayed == year
            and self.month_displayed == month
            and self.day_displayed == day
        ):
            self.refresh_data()
    
    def delete_worktime_of_editor(self, worktime_editor):
        """
            删除工作时间记录。

            :param worktime_editor: 工作时间记录编辑器窗口实例。
        """
        year = worktime_editor.year
        month = worktime_editor.month
        day = worktime_editor.day
        id_ = worktime_editor.id_

        # 读取现有数据
        worktimes_of_month = self.get_worktimes_of_month(year, month)

        # 删除记录项
        if len(worktimes_of_month.get(str(day), [])) > id_:
            del worktimes_of_month[str(day)][id_]
        else:
            return

        # 保存文件；如果记录被清空，删除文件
        if not worktimes_of_month[str(day)]:
            del worktimes_of_month[str(day)]
        if worktimes_of_month:
            self.save_worktimes(year, month, worktimes_of_month)
        else:
            os.remove(os.path.join(data_dir, str(year)[2:], str(month) + ".json"))

        if (self.year_displayed == year
            and self.month_displayed == month
            and self.day_displayed == day
        ):
            self.refresh_data()