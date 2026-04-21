import json
import os
import datetime

from PySide6.QtWidgets import (QLabel, QWidget, QHBoxLayout, QVBoxLayout,
                               QScrollArea, QListWidget,
                               QStackedWidget, QPushButton, QDateEdit, QDateTimeEdit)
from PySide6.QtCore import Qt, QDate, QDateTime

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

        self.container_layout = QHBoxLayout(self.container)
        
        # 左侧类别列表
        self.category_scroll_area = QScrollArea()
        self.category_scroll_area.setWidgetResizable(True)
        self.category_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.category_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.category_scroll_area.setFixedWidth(180)

        self.category_list = QListWidget()
        self.category_list.currentRowChanged.connect(self.on_category_changed)
        self.category_scroll_area.setWidget(self.category_list)
        self.container_layout.addWidget(self.category_scroll_area)
        
        # 右侧设置内容区域
        self.stacked_widget = QStackedWidget()
        self.container_layout.addWidget(self.stacked_widget)

        # 上下班打卡
        self.category_list.addItem("上下班打卡")
        self.clock_widget = QWidget()
        self.clock_layout = QVBoxLayout(self.clock_widget)
        self.stacked_widget.addWidget(self.clock_widget)

        self.init_clock_ui()

        # 工作时间详情
        self.category_list.addItem("工作时间详情")
        self.worktime_detail_widget = QWidget()
        self.worktime_detail_layout = QVBoxLayout(self.worktime_detail_widget)
        self.stacked_widget.addWidget(self.worktime_detail_widget)

        self.init_worktime_detail_ui()

        # 默认选择第一个类别
        self.category_list.setCurrentRow(0)
        self.stacked_widget.setCurrentIndex(0)

    def on_category_changed(self, row):
        """类别切换事件"""
        if row >= 0:
            self.stacked_widget.setCurrentIndex(row)

        if row == 1: # 工作时间详情
            self.floating_button.show()
            self.floating_button.raise_()
        else:
            self.floating_button.hide()
    
    def load_clock_data(self):
        """读取打卡数据"""
        clock_file_path = os.path.join(data_dir, "clock.json")
        
        if os.path.exists(clock_file_path):
            with open(clock_file_path, 'r', encoding='utf-8') as f:
                self.clock_data = json.load(f)
        else:
            self.clock_data = {"working": False, "from": None}
    
    def save_clock_data(self):
        """保存打卡数据"""
        clock_file_path = os.path.join(data_dir, "clock.json")
        
        os.makedirs(os.path.dirname(clock_file_path), exist_ok=True)
        with open(clock_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.clock_data, f, ensure_ascii=False, indent=4)
    
    def update_clock_ui(self):
        """更新打卡UI状态"""
        if self.clock_data["working"]:
            # 上班状态：显示下班打卡按钮
            self.clock_button.setText("下班打卡")
            self.clock_button.setStyleSheet("""
                QPushButton {
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: 60px;
                    background-color: #D13438;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #C02B2F;
                }
            """)
            
            self.clock_status_label.setText(f"上班时间: {self.clock_data['from']}")
            self.clock_status_label.show()

        else:
            # 下班状态：显示上班打卡按钮
            self.clock_button.setText("上班打卡")
            self.clock_button.setStyleSheet("""
                QPushButton {
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: 60px;
                    background-color: #107C10;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #0E6B0E;
                }
            """)
            
            self.clock_status_label.hide()
    
    def calculate_work_time_str(self, from_time, to_time):
        """计算工作时间（小时:分钟）"""
        # 处理跨天情况
        total_minutes = (to_time.hour - from_time.hour) * 60 + to_time.minute - from_time.minute
        if total_minutes < 0:
            total_minutes += 1440
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        return f"{hours:02d}:{minutes:02d}"
    
    def add_worktime_record(self, from_time, to_time, year, month, day):
        """
        添加工作时间记录

        :param from_time: 上班时间（格式: "HH:MM"）
        :param to_time: 下班时间（datetime.datetime对象）
        :param year: 年份
        :param month: 月份
        :param day: 日
        """
        worktime_record = {
            "from": from_time,
            "to": to_time.strftime("%H:%M"),
            "total_work": self.calculate_work_time_str(
                datetime.time.strptime(from_time, "%H:%M"),
                to_time.time()
            )
        }
        
        # 读取现有数据
        worktimes_of_month = self.get_worktimes_of_month(year, month)
        if str(day) not in worktimes_of_month:
            worktimes_of_month[str(day)] = []
        worktimes_of_month[str(day)].append(worktime_record)
        self.save_worktimes(year, month, worktimes_of_month)
        if (self.year_displayed == year
            and self.month_displayed == month
            and self.day_displayed == day
        ):
            self.refresh_data()

    
    def on_clock_clicked(self):
        """打卡按钮点击事件"""
        now = datetime.datetime.now()
        
        if self.clock_data["working"]:
            # 下班打卡：添加工作时间记录
            from_time = self.clock_data["from"]

            today = get_today()
            year = today.year
            month = today.month
            day = today.day
            
            # 创建工作时间记录
            self.add_worktime_record(from_time, now, year, month, day)

            self.clock_data["working"] = False
            self.save_clock_data()
            self.update_clock_ui()
            
        else:
            # 上班打卡：设置上班时间
            self.clock_data["working"] = True
            self.clock_data["from"] = now.strftime("%H:%M")
            self.save_clock_data()
            self.update_clock_ui()

    def on_backfill_clicked(self):
        """补卡按钮点击事件"""
        selected_datetime = self.backfill_datetime.dateTime().toPython()
        
        if self.clock_data["working"]:
            # 下班打卡：添加工作时间记录
            from_time = self.clock_data["from"]

            year = selected_datetime.year
            month = selected_datetime.month
            day = selected_datetime.day
            
            # 创建工作时间记录
            self.add_worktime_record(from_time, selected_datetime, year, month, day)

            self.clock_data["working"] = False
            self.save_clock_data()
            self.update_clock_ui()
            
        else:
            # 上班打卡：设置上班时间
            self.clock_data["working"] = True
            self.clock_data["from"] = selected_datetime.strftime("%H:%M")
            self.save_clock_data()
            self.update_clock_ui()
    
    def init_clock_ui(self):
        self.clock_layout.addStretch()

        # 读取打卡数据
        self.load_clock_data()
        
        # 创建打卡按钮
        self.clock_button = QPushButton()
        self.clock_button.setFixedSize(120, 120)
        self.clock_button.clicked.connect(self.on_clock_clicked)
        self.update_clock_ui()
        self.clock_layout.addWidget(self.clock_button)
        
        # 创建打卡时间显示标签
        self.clock_status_label = QLabel()
        self.clock_status_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
        self.clock_layout.addWidget(self.clock_status_label)

        # 创建补卡按钮
        self.backfill_widget = QWidget()
        self.backfill_layout = QHBoxLayout(self.backfill_widget)

        self.backfill_datetime = QDateTimeEdit()
        self.backfill_datetime.setFixedHeight(30)
        self.backfill_datetime.setDateTime(QDateTime.currentDateTime())
        self.backfill_layout.addWidget(self.backfill_datetime)

        self.backfill_button = QPushButton("补卡")
        self.backfill_button.setFixedSize(100, 30)
        self.backfill_button.clicked.connect(self.on_backfill_clicked)
        self.backfill_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """)
        self.backfill_layout.addWidget(self.backfill_button)

        self.clock_layout.addWidget(self.backfill_widget)
        
        self.clock_layout.addStretch()
        
    def init_worktime_detail_ui(self):
        self.date_selector = QDateEdit(self.worktime_detail_widget)
        self.date_selector.setFixedHeight(30)
        self.date_selector.setCalendarPopup(True)
        self.worktime_detail_layout.addWidget(self.date_selector)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.worktime_detail_layout.addWidget(self.scroll_area)
       
        self.create_floating_button()

        self.date_selector.dateChanged.connect(self.on_date_changed)
        today = get_today()
        self.date_selector.setDate(QDate(today.year, today.month, today.day))

    def create_floating_button(self):
        """创建右下角悬浮按钮（默认隐藏）"""
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