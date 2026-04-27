import json
import os
import datetime

from sortedcontainers import SortedDict
from PySide6.QtWidgets import (QLabel, QWidget, QHBoxLayout, QVBoxLayout,
                               QScrollArea, QPushButton, QDateEdit)
from PySide6.QtCore import Qt, QDate, QEvent

from core.base_window import BaseWindow
from core.functions import get_today
from .schedule_editor import ScheduleEditorWindow


data_dir = "apps/calendar/data"

class PlaceLabel(QLabel):
    def __init__(self, text, parent=None):
        if text.startswith("https://"):
            super().__init__(f'<a href="{text}">{text}</a>', parent)
        else:
            super().__init__(text, parent)
        self.setMouseTracking(True)
        self.is_hovering_link = False
        self.setOpenExternalLinks(True)
        self.linkHovered.connect(self.onLinkHovered)

    def onLinkHovered(self, link):
        """当悬停状态改变时调用"""
        if link:
            # 鼠标进入链接
            self.is_hovering_link = True
            
            # 安装事件过滤器到父控件，阻止事件传递
            if self.parent():
                self.parent().installEventFilter(self)
        else:
            # 鼠标离开链接
            self.is_hovering_link = False
            
            # 移除事件过滤器，恢复事件传递
            if self.parent():
                self.parent().removeEventFilter(self)

    def eventFilter(self, obj, event):
        """事件过滤器：拦截父控件的事件"""
        if self.is_hovering_link and obj == self.parent():
            # 当悬停在链接上时，拦截所有鼠标事件
            if event.type() in [QEvent.Type.MouseButtonPress,
                               QEvent.Type.MouseButtonRelease,
                               QEvent.Type.MouseButtonDblClick,
                               QEvent.Type.MouseMove]:
                # 将事件转发给当前标签处理
                self.mousePressEvent(event)
                return True  # 拦截事件，不让父控件处理
        
        return super().eventFilter(obj, event)

class ScheduleItemWidget(QWidget):
    def __init__(self, schedule_item, schedule_id=None, parent=None):
        super().__init__(parent)
        self.schedule_item = schedule_item
        self.schedule_id = schedule_id

        # 设置悬停效果样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            ScheduleItemWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        self.layout_ = QVBoxLayout(self)

        self.title_label = QLabel(schedule_item["title"])
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        self.title_label.setWordWrap(True)
        self.layout_.addWidget(self.title_label)

        if "start_time" and "end_time" in schedule_item and schedule_item["start_time"] and schedule_item["end_time"]:
            self.time_label = QLabel(f"{schedule_item['start_time']} - {schedule_item['end_time']}")
            self.time_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.layout_.addWidget(self.time_label)
        
        if "location" in schedule_item and schedule_item["location"]:
            self.location_label = PlaceLabel(schedule_item['location'])
            self.location_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.location_label.setWordWrap(True)
            self.layout_.addWidget(self.location_label)

        if "type" in schedule_item or ("repetition" in schedule_item and schedule_item["repetition"] != 0):
            self.type_repetition_widget = QWidget()
            self.type_repetition_layout = QHBoxLayout(self.type_repetition_widget)
            self.layout_.addWidget(self.type_repetition_widget)

        if "type" in schedule_item:
            self.type_label = QLabel(
                "类型：{}".format(
                    ["其他", "会议", "娱乐", "活动", "课程"]
                    [schedule_item["type"]]
                )
            )
            self.type_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.type_repetition_layout.addWidget(self.type_label)

        if "repetition" in schedule_item and schedule_item["repetition"] != 0:
            self.repetition_label = QLabel(
                "重复：{}".format(
                    ["无", "每天", "每周"]
                    [schedule_item["repetition"]]
                )
            )
            self.repetition_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.type_repetition_layout.addWidget(self.repetition_label)

        if "description" in schedule_item and schedule_item["description"]:
            self.description_label = QLabel(schedule_item["description"])
            self.description_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            self.description_label.setWordWrap(True)
            self.layout_.addWidget(self.description_label)

    def mousePressEvent(self, event):
         # 打开日程编辑窗口
         editor = ScheduleEditorWindow(self, self.schedule_item, self.schedule_id)
         editor.show()

class CalendarSchedulesManager:
    def init_repeat_events_of_date(self, date):
        """初始化指定日期的重复事件"""
        # 处理每天重复事件
        yesterday = date - datetime.timedelta(days=1)
        events_yesterday = self.load_schedules(yesterday.year, yesterday.month, yesterday.day)
        for event in events_yesterday.values():
            if event.get("repetition") == 1: # 每天重复
                start_time_old = datetime.datetime.strptime(event["start_time"], '%Y-%m-%d %H:%M')
                start_time_new = start_time_old + datetime.timedelta(days=1)
                event["start_time"] = start_time_new.strftime('%Y-%m-%d %H:%M')

                end_time_old = datetime.datetime.strptime(event["end_time"], '%Y-%m-%d %H:%M')
                end_time_new = end_time_old + datetime.timedelta(days=1)
                event["end_time"] = end_time_new.strftime('%Y-%m-%d %H:%M')

                id_ = int(((start_time_new.hour * 60 + start_time_new.minute) - 240) % 1440)
                self.save_schedule(
                    event,
                    date.year, date.month, date.day, id_,
                    copy=True)
                
        # 处理每周重复事件
        lastweek = date - datetime.timedelta(days=7)
        events_lastweek = self.load_schedules(lastweek.year, lastweek.month, lastweek.day)
        for event in events_lastweek.values():
            if event.get("repetition") == 2: # 每周重复
                start_time_old = datetime.datetime.strptime(event["start_time"], '%Y-%m-%d %H:%M')
                start_time_new = start_time_old + datetime.timedelta(days=7)
                event["start_time"] = start_time_new.strftime('%Y-%m-%d %H:%M')

                end_time_old = datetime.datetime.strptime(event["end_time"], '%Y-%m-%d %H:%M')
                end_time_new = end_time_old + datetime.timedelta(days=7)
                event["end_time"] = end_time_new.strftime('%Y-%m-%d %H:%M')

                id_ = int(((start_time_new.hour * 60 + start_time_new.minute) - 240) % 1440)
                self.save_schedule(
                    event,
                    date.year, date.month, date.day, id_,
                    copy=True)

    def init_repeat_events_until_today(self, today):
        """初始化从上次到今天的重复事件（要求时间差不多于30天）"""
        # 获取上次更新的日期
        last_update_date_file = os.path.join(data_dir, "last_update_date.json")
        try:
            with open(last_update_date_file, 'r', encoding='utf-8') as f:
                last_update_date_str = json.load(f)
            last_update_date = datetime.datetime.strptime(last_update_date_str, '%Y-%m-%d').date()
        except Exception:
            last_update_date = today - datetime.timedelta(days=1)
        
        # 如果上次更新在今天或之后，直接返回
        if last_update_date >= today:
            return
        
        # 如果上次更新在30天之前，警告后返回
        if last_update_date + datetime.timedelta(days=30) < today:
            import warnings
            warnings.warn("上次更新在30天之前，暂不更新重复事件")
            return
        
        # 遍历日期
        updating_date = last_update_date
        while updating_date < today:
            updating_date += datetime.timedelta(days=1)
            self.init_repeat_events_of_date(updating_date)

        # 保存最新的上次更新时间
        with open(last_update_date_file, 'w', encoding='utf-8') as f:
            json.dump(str(today), f, indent=4)
        
    def load_schedules(self, year, month, day):
        """从文件加载日程数据"""
        file_path = os.path.join(data_dir, str(year), str(month), str(day) + ".json")
        if os.path.exists(file_path):
            # 若文件读取失败，应报错
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_schedule(
            self,
            schedule_data,
            year_new, month_new, day_new, id_new,
            year_old=None, month_old=None, day_old=None, id_old=None,
            copy=False
        ):
        """
        保存日程到文件。

        Parameters:
            schedule_data: 日程数据字典。
            year_new: 新日期的年份。
            month_new: 新日期的月份。
            day_new: 新日期的日期。
            id_new: 新日程的id。
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
            copy: 是否复制旧日程，默认False。
        """
        # 读取日程
        file_path = os.path.join(data_dir, str(year_new), str(month_new), str(day_new) + ".json")
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                schedules = SortedDict(json.load(f))
        else:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            schedules = SortedDict()
        
        # 尝试删除旧日程
        if not copy and year_old is not None:
            if (year_old == year_new
                and month_old == month_new
                and day_old == day_new
            ):
                if id_old in schedules:
                    del schedules[id_old]
            else:
                self.delete_schedule(year_old, month_old, day_old, id_old)

        # 添加日程
        id_new = str(id_new)
        if id_new in schedules:
            seen = 0
            while str(f"{id_new}_{str(seen).zfill(3)}") in schedules:
                seen += 1
            id_new = f"{id_new}_{str(seen).zfill(3)}"
        
        schedules[id_new] = schedule_data

        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dict(schedules), f, ensure_ascii=False, indent=4)
        
    def delete_schedule(self, year_old, month_old, day_old, id_old):
        """
        从文件中删除日程。

        Parameters:
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
        """
        # 检查文件是否存在
        if not year_old:
            return 1 # 返回flag
        file_path = os.path.join(data_dir, str(year_old), str(month_old), str(day_old) + ".json")
        if not os.path.exists(file_path):
            return 1 # 返回flag

        # 删除日程
        with open(file_path, 'r', encoding='utf-8') as f:
            schedules = json.load(f)
        if id_old in schedules:
            del schedules[id_old]
        
        # 保存文件；如果日程被清空，删除文件
        if schedules:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(schedules, f, ensure_ascii=False, indent=4)
        else:
            os.remove(file_path)

class CalendarWindow(BaseWindow, CalendarSchedulesManager):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("日程")
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
        self.floating_button.clicked.connect(self.open_new_schedule)
        
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

        self.refresh_schedules()

    def open_new_schedule(self):
        """打开新增日程窗口"""
        editor = ScheduleEditorWindow(
            self,
            year=self.year_displayed,
            month=self.month_displayed,
            day=self.day_displayed
        )
        editor.show()

    def refresh_schedules(self):
        """刷新日程显示"""
        # 清空现有布局（包括所有widget和stretch）
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新加载数据
        self.schedules = self.load_schedules(self.year_displayed, self.month_displayed, self.day_displayed)
        
        # 添加日程项
        for schedule_id, schedule in self.schedules.items():
            self.scroll_layout.addWidget(ScheduleItemWidget(schedule, schedule_id))

        # 添加stretch，确保日程项在顶部，空白在底部
        self.scroll_layout.addStretch()

    def save_schedule_from_editor(self, schedule_editor, copy=False):
        """
        从日程编辑器保存日程。

        Parameters:
            schedule_editor: 日程编辑器窗口实例。
            copy: 是否复制旧日程，默认False。
        """
        self.save_schedule(
            schedule_data=schedule_editor.schedule_data,
            year_new=schedule_editor.year_new,
            month_new=schedule_editor.month_new,
            day_new=schedule_editor.day_new,
            id_new=schedule_editor.id_new,
            year_old=schedule_editor.year,
            month_old=schedule_editor.month,
            day_old=schedule_editor.day,
            id_old=schedule_editor.id,
            copy=copy
        )

    def save_schedule(
            self,
            schedule_data,
            year_new, month_new, day_new, id_new,
            year_old=None, month_old=None, day_old=None, id_old=None,
            copy=False
        ):
        """
        保存日程到文件。

        Parameters:
            schedule_data: 日程数据字典。
            year_new: 新日期的年份。
            month_new: 新日期的月份。
            day_new: 新日期的日期。
            id_new: 新日程的id。
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
            copy: 是否复制旧日程，默认False。
        """
        super().save_schedule(
            schedule_data,
            year_new, month_new, day_new, id_new,
            year_old, month_old,
            day_old,
            id_old,
            copy
        )

        if (self.year_displayed == year_new
            and self.month_displayed == month_new
            and self.day_displayed == day_new
        ):
            self.refresh_schedules()

    def delete_schedule_from_editor(self, schedule_editor):
        """
        从日程编辑器删除日程。

        Parameters:
            schedule_editor: 日程编辑器窗口实例。
        """
        self.delete_schedule(
            schedule_editor.year,
            schedule_editor.month,
            schedule_editor.day,
            schedule_editor.id
        )

    def delete_schedule(self, year_old, month_old, day_old, id_old):
        """
        从文件中删除日程。

        Parameters:
            year_old: 旧日期的年份。
            month_old: 旧日期的月份。
            day_old: 旧日期的日期。
            id_old: 旧日程的id。
        """
        flag = super().delete_schedule(year_old, month_old, day_old, id_old)
        if flag:
            return

        if (self.year_displayed == year_old
            and self.month_displayed == month_old
            and self.day_displayed == day_old
        ):
            self.refresh_schedules()
