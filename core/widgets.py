import datetime
import json
import numpy as np
import os
from PySide6.QtCore import QRectF, Qt, Signal, QThread
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton)
import webbrowser
from winotify import Notification

from core.functions import get_today
from core.global_constants import app_name
from core.heartbeat import Heartbeat
from apps import APP_LIST


class ClockWidget(QWidget):
    """时钟部件，显示三个同心环进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置环的宽度
        self.ring_width = 8
        self.dot_size = 8
        
        # 设置组件的尺寸
        self.setFixedSize(128, 128)
        
        # 计算初始进度值（创建时计算一次）
        self.calculate_progress()
    
    def calculate_progress(self):
        """计算三个环的进度值"""
        current_time = datetime.datetime.now()
        current_day = get_today(current_time)
        
        # 计算内环：周次进度条（蓝色）
        # 起始时间：2025年9月11日 4:00
        start_date = datetime.datetime(2025, 9, 11, 4, 0, 0)
        
        # 计算总周数（300周）
        total_weeks = 300
        total_duration = datetime.timedelta(weeks=total_weeks).total_seconds()
        
        # 计算已过时间（精确到秒）
        time_passed = (current_time - start_date).total_seconds()
        
        # 计算周次进度（0-100%）
        self.inner_progress = np.clip((time_passed / total_duration), 0, 1)
        
        # 计算中环：本周进度条（绿色）
        # 每周四4:00开始新的一周
        current_weekday = current_day.weekday()  # 使用current_day的星期
        
        # 计算本周开始日期（上周四）
        # 如果当前是周四或之后，本周开始是周四
        # 如果当前是周三或之前，本周开始是上周四
        days_since_thursday = (current_weekday - 3) % 7
        week_start_day = current_day - datetime.timedelta(days=days_since_thursday)
        
        # 设置本周开始时间为周四4:00
        week_start_time = datetime.datetime.combine(week_start_day, datetime.time(4, 0, 0))
        
        # 计算本周进度
        week_duration = 604800.0  # 7天 * 24小时 * 60分钟 * 60秒
        time_in_week = (current_time - week_start_time).total_seconds()
        
        self.middle_progress = np.clip((time_in_week / week_duration), 0, 1)
        
        # 计算外环：本日状态（灰色虚线 + 黄色圆点）
        # 每日4:00开始新的一天
        # 使用current_day计算日起始时间
        day_start_time = datetime.datetime.combine(current_day, datetime.time(4, 0, 0))
        
        # 计算本日进度
        day_duration = 86400.0  # 24小时 * 60分钟 * 60秒
        time_in_day = (current_time - day_start_time).total_seconds()
        
        self.outer_progress = np.clip((time_in_day / day_duration), 0, 1)
    
    def paintEvent(self, event):
        """绘制三个同心环"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        
        # 获取组件尺寸
        width = self.width()
        height = self.height()
        
        # 计算中心点和半径
        center_x = width // 2
        center_y = height // 2
        
        # 计算最大半径（留出边距）
        max_radius = min(width, height) // 2 - 10
        
        # 计算三个环的半径
        outer_radius = max_radius
        middle_radius = max_radius * 0.65
        inner_radius = max_radius * 0.3
        
        # 绘制外环：本日状态（灰色虚线 + 黄色圆点）
        self.draw_day_ring(painter, center_x, center_y, outer_radius, self.outer_progress)
        
        # 绘制中环：本周进度条（绿色）
        self.draw_week_ring(painter, center_x, center_y, middle_radius, self.middle_progress)
        
        # 绘制内环：周次进度条（蓝色）
        self.draw_season_ring(painter, center_x, center_y, inner_radius, self.inner_progress)
        
    def draw_season_ring(self, painter, center_x, center_y, radius, progress):
        """绘制内环：周次进度条（蓝色）"""
        # 计算环的矩形区域
        rect = QRectF(center_x - radius, center_y - radius, 
                     radius * 2, radius * 2)
        
        # 先绘制灰色背景圆环
        bg_pen = QPen(QColor(128, 128, 128, 128))
        bg_pen.setWidth(self.ring_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 5760)  # 完整的背景环
        
        # 再绘制蓝色进度条
        pen = QPen(QColor(100, 100, 255))  # 蓝色
        pen.setWidth(self.ring_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # 计算进度对应的角度（360度对应100%）
        span_angle = int(progress * 5760)  # Qt使用1/16度为单位
        
        # 绘制进度弧线（从顶部开始，顺时针方向）
        start_angle = 1440  # 从顶部开始（90度）
        painter.drawArc(rect, start_angle, -span_angle)  # 负值表示顺时针
        
        # 删除环标签
    
    def draw_week_ring(self, painter, center_x, center_y, radius, progress):
        """绘制中环：本周进度条（绿色）"""
        # 计算环的矩形区域
        rect = QRectF(center_x - radius, center_y - radius, 
                     radius * 2, radius * 2)
        
        # 先绘制灰色背景圆环
        bg_pen = QPen(QColor(128, 128, 128, 128))
        bg_pen.setWidth(self.ring_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 5760)  # 完整的背景环
        
        # 再绘制绿色进度条
        pen = QPen(QColor(100, 255, 100))  # 绿色
        pen.setWidth(self.ring_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # 计算进度对应的角度（360度对应100%）
        span_angle = int(progress * 5760)  # Qt使用1/16度为单位
        
        # 绘制进度弧线（从顶部开始，顺时针方向）
        start_angle = 1440  # 从顶部开始（90度）
        painter.drawArc(rect, start_angle, -span_angle)  # 负值表示顺时针
    
    def draw_day_ring(self, painter, center_x, center_y, radius, progress):
        """绘制外环：本日状态（灰色背景 + 黄色圆点）"""
        # 计算环的矩形区域
        rect = QRectF(center_x - radius, center_y - radius, 
                     radius * 2, radius * 2)
        
        # 绘制灰色背景圆环
        bg_pen = QPen(QColor(128, 128, 128, 128))
        bg_pen.setWidth(self.ring_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 5760)  # 完整的背景环
        
        # 计算黄色圆点的位置
        angle_rad = (90 - progress * 360) * np.pi / 180  # 转换为弧度，从顶部开始顺时针
        dot_x = center_x + radius * np.cos(angle_rad)
        dot_y = center_y - radius * np.sin(angle_rad)  # Y轴向下为正
        
        # 绘制黄色圆点
        painter.setBrush(QBrush(QColor(255, 255, 0)))  # 黄色填充
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(dot_x - self.dot_size / 2), int(dot_y - self.dot_size / 2), 
                          self.dot_size, self.dot_size)
        
class DateTimeLabel(QLabel):
    """日期时间标签，显示日期和时间"""
    def __init__(self, week_number, parent=None):
        super().__init__(parent)
        self.update_display(week_number)

    def update_display(self, week_number):
        """更新显示内容"""
        # 更新日期周次
        today = get_today()
        date_str = f"{today.month}月{today.day}日"
        weekday_num = today.weekday()
        weekday_cn = ["一", "二", "三", "四", "五", "六", "日"][weekday_num]
        self.setText(f"{date_str} 第{week_number}周 星期{weekday_cn}")

class PeriodSeasonLabel(QLabel):
    """时期与季节标签，显示时期和季节信息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 加载并显示数据
        self.load_data()
    
    def load_data(self):
        """从JSON文件加载数据并更新显示，如果文件不存在则使用默认值并创建文件"""
        
        # 构建文件路径
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'data', 'homepage', 'PeriodSeason.json')
                
        # 尝试读取并解析JSON文件
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取时期和季节数据
            period = data['period']
            season = data['season']
            
        except (FileNotFoundError, json.JSONDecodeError, IOError, KeyError, TypeError):
            # 如果文件不存在、损坏、读取失败或数据格式错误，尝试创建目录并写入默认数据
            default_data = {
                "period": "原初",
                "season": "夏"
            }
            period = "原初"
            season = "夏"
            try:
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
            except IOError:
                pass  # 如果无法写入，继续使用默认数据
        
        # 设置显示文本（无论是否发生异常都会执行）
        display_text = f"{period}期 {season}季"
        self.setText(display_text)
    
class VersionLabel(QLabel):
    """版本标签，显示应用版本与个人版本信息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 加载并显示数据
        self.load_data()
    
    def load_data(self):
        """从JSON文件加载数据并更新显示，如果文件不存在则使用默认值并创建文件"""
        
        # 构建文件路径
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'data', 'homepage', 'Version.json')
        
        # 尝试读取并解析JSON文件
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取版本数据
            user_version = data['user_version']
            app_version = data['app_version']
            
        except (FileNotFoundError, json.JSONDecodeError, IOError, KeyError, TypeError):
            # 如果文件不存在、损坏、读取失败或数据格式错误，尝试创建目录并写入默认数据
            default_data = {
                "user_version": "未知",
                "app_version": "未知"
            }        
            user_version = "未知"
            app_version = "未知"
            try:
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
            except IOError:
                pass  # 如果无法写入，继续使用默认数据
        
        # 设置显示文本（无论是否发生异常都会执行）
        display_text = f"版本：user: {user_version} app: {app_version}"
        self.setText(display_text)
    
class TopStatusWidget(QWidget):
    """顶部状态部件，圆角矩形框内，左侧时钟，右侧日期周次和时期季节"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置组件
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            TopStatusWidget {
                border-radius: 15px;
                border: 1px solid #808080;
            }
        """)
        
        # 创建布局和部件
        # 主水平布局（设置边距确保边框可见）
        main_layout = QHBoxLayout(self)
        
        # 左侧：时钟部件
        self.clock_widget = ClockWidget()
        main_layout.addWidget(self.clock_widget)
        
        # 右侧：垂直布局（日期周次 + 时期季节）
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 日期周次标签
        self.date_week_label = DateTimeLabel(self.get_week_number(), self)
        self.date_week_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #FFFFFF;
        """)
        right_layout.addWidget(self.date_week_label)
        
        # 时期季节标签
        self.period_season_label = PeriodSeasonLabel()
        self.period_season_label.setStyleSheet("""
            font-size: 24px;
            color: #888888;
        """)
        right_layout.addWidget(self.period_season_label)

        # 版本标签
        self.version_label = VersionLabel()
        self.version_label.setStyleSheet("""
            font-size: 18px;
            color: #888888;
        """)
        right_layout.addWidget(self.version_label)

        main_layout.addLayout(right_layout, 1)
    
        # 定期更新显示
        self.updater = Heartbeat(self.update_display, interval=300)
    
    def get_week_number(self):
        """获取周次"""
        # 获取时钟部件的内环进度（对应周次进度）
        inner_progress = self.clock_widget.inner_progress
        # 根据进度计算周次（总300周）
        return int(inner_progress * 300) + 1
    
    def update_display(self):
        """更新所有显示"""
        self.clock_widget.calculate_progress()
        self.clock_widget.update()  # 刷新时钟显示
        self.date_week_label.update_display(self.get_week_number())
        self.period_season_label.load_data()

top_status = TopStatusWidget()


class CollapsibleTitleWidget(QWidget):
    """可折叠标题部件"""
    pass

class CollapsibleContainerWidget(QWidget):
    """可折叠容器基类，提供统一的标题格式和折叠/展开功能"""
    
    def __init__(self, title="", default_expanded=False, parent=None):
        super().__init__(parent)
        self.is_expanded = default_expanded
        self.title = title
        
        # 设置组件样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # 创建布局和部件
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 标题行：可点击的标题和折叠箭头
        self.title_widget = CollapsibleTitleWidget()
        title_layout = QHBoxLayout(self.title_widget)
        
        # 折叠箭头
        self.arrow_label = QLabel("▶" if not self.is_expanded else "▼")
        self.arrow_label.setFixedSize(20, 20)
        self.arrow_label.setStyleSheet("""
            font-size: 16px;
            color: #FFFFFF;
            font-weight: bold;
        """)
        title_layout.addWidget(self.arrow_label)
        
        # 标题名称
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("""
            font-size: 24px;
            color: #FFFFFF;
            font-weight: bold;
        """)
        title_layout.addWidget(self.title_label)
        
        # 右侧伸缩空间
        title_layout.addStretch()
        
        # 设置标题悬停高亮提示
        self.title_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.title_widget.setStyleSheet("""
            CollapsibleTitleWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        layout.addWidget(self.title_widget)
        
        # 内容容器（根据初始状态显示/隐藏）
        self.content_container = QWidget()
        
        if not self.is_expanded:
            self.content_container.hide()
        
        layout.addWidget(self.content_container)
        
        # 连接标题点击事件
        self.title_widget.mousePressEvent = self.toggle_expand
    
    def toggle_expand(self, event):
        """切换折叠/展开状态"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_expanded = not self.is_expanded
            self.update_expansion_display()
    
    def update_expansion_display(self):
        """更新显示状态"""
        # 更新箭头方向
        if self.is_expanded:
            self.arrow_label.setText("▼")
            self.content_container.show()
            self.on_expand()
        else:
            self.arrow_label.setText("▶")
            self.content_container.hide()
            self.on_collapse()
    
    def on_expand(self):
        """展开时的回调函数，子类可以重写"""
        pass
    
    def on_collapse(self):
        """折叠时的回调函数，子类可以重写"""
        pass
    
    def set_title(self, title):
        """设置标题"""
        self.title = title
        self.title_label.setText(title)
    
    def add_widget_to_content(self, widget):
        """向内容容器添加部件"""
        self.content_layout.addWidget(widget)
    
    def clear_content(self):
        """清空内容容器"""
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    self.content_layout.removeWidget(widget)
                    widget.setParent(None)
                    widget.deleteLater()


class NotificationItemWidget(QWidget):
    """单个通知项部件"""
    
    def __init__(
            self,
            title="来自助手的通知",
            content="助手没收到更多内容哦",
            click_action=None,
            icon_path='',
            is_read=False,
            notification_system=None,
            create_time=None
        ):
        super().__init__()
        self.title = title
        self.content = content
        self.is_read = is_read
        self.click_action = click_action
        self.icon_path = icon_path
        self.create_time = create_time if create_time else datetime.datetime.now()
        self.notification_system = notification_system
        
        # 设置组件样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            NotificationItemWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        # 创建布局和部件
        layout = QVBoxLayout(self)
        
        # 标题标签
        self.title_label = QLabel(self.title)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        # 内容标签
        self.content_label = QLabel(self.content)
        self.content_label.setWordWrap(True)
        layout.addWidget(self.content_label)
        
        # 底部行：左侧时间 + 右侧状态按钮
        bottom_layout = QHBoxLayout()
        
        # 左侧：创建时间
        self.time_label = QLabel(self.create_time.strftime("%m-%d %H:%M:%S"))
        self.time_label.setStyleSheet("""
            font-size: 12px;
            color: #888888;
        """)
        bottom_layout.addWidget(self.time_label)
        
        # 右侧：伸缩空间
        bottom_layout.addStretch()
        
        # 右侧：已读/未读状态按钮
        self.status_button = QPushButton()
        self.status_button.setFixedSize(20, 20)
        self.status_button.clicked.connect(self.toggle_read_status)
        bottom_layout.addWidget(self.status_button)
        
        # 右侧：删除按钮
        self.delete_button = QPushButton("×")
        self.delete_button.setFixedSize(20, 20)
        self.delete_button.clicked.connect(
            lambda: self.notification_system.remove_notification(self)
        )
        self.delete_button.setToolTip("删除")
        self.delete_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #FF4444;
                border-radius: 10px;
                background-color: transparent;
                color: #FF4444;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 68, 68, 0.2);
            }
        """)
        bottom_layout.addWidget(self.delete_button)
        
        layout.addLayout(bottom_layout)
        
        # 设置已读状态样式
        self.update_read_style()
    
    def update_read_style(self):
        """更新已读状态样式"""
        if self.is_read:
            self.title_label.setStyleSheet("""
                font-size: 18px;
                font-weight: normal;
                color: #888888;
            """)
            self.content_label.setStyleSheet("""
                font-size: 14px;
                color: #666666;
            """)
            # 已读状态：空心圆圈
            self.status_button.setStyleSheet("""
                QPushButton {
                    border: 1px solid #808080;
                    border-radius: 10px;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """)
            self.status_button.setToolTip("标记未读")
        else:
            self.title_label.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                color: #FFFFFF;
            """)
            self.content_label.setStyleSheet("""
                font-size: 14px;
                color: #CCCCCC;
            """)
            # 未读状态：蓝色实心圆圈
            self.status_button.setStyleSheet("""
                QPushButton {
                    border: 1px solid #007AFF;
                    border-radius: 10px;
                    background-color: #007AFF;
                }
                QPushButton:hover {
                    background-color: #005FAF;
                }
            """)
            self.status_button.setToolTip("标记已读")
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.click_action:
                if self.click_action["type"] == "open_url":
                    url = self.click_action["value"]
                    webbrowser.open(url)
                elif self.click_action["type"] == "open_file":
                    file_path = self.click_action["value"]
                    os.startfile(file_path)
                elif self.click_action["type"] == "open_app":
                    app_name = self.click_action["value"]
                    exec(f"import {app_name}")
                else:
                    raise ValueError(f"未知点击操作类型: {self.click_action['type']}")
        self.mark_as_read()
        super().mousePressEvent(event)
    
    def mark_as_read(self):
        """标记为已读"""
        self.is_read = True
        self.update_read_style()
        # 保存状态变化
        if hasattr(self, 'notification_system'):
            self.notification_system.save_notifications()
            # 更新未读计数
            self.notification_system.update_unread_count()
    
    def mark_as_unread(self):
        """标记为未读"""
        self.is_read = False
        self.update_read_style()
        # 保存状态变化
        if hasattr(self, 'notification_system'):
            self.notification_system.save_notifications()
            # 更新未读计数
            self.notification_system.update_unread_count()
    
    def update_content(self, title=None, content=None):
        """更新通知内容"""
        if title is not None:
            self.title = title
            self.title_label.setText(title)
        if content is not None:
            self.content = content
            self.content_label.setText(content)
    
    def toggle_read_status(self):
        """切换已读/未读状态"""
        if self.is_read:
            self.mark_as_unread()
        else:
            self.mark_as_read()
        # 保存状态变化
        self.notification_system.save_notifications()
    
class NotificationSystemWidget(CollapsibleContainerWidget):
    """通知系统部件，管理多个通知项"""
    
    # 定义信号，用于线程安全的通知添加
    notify_signal = Signal(str, str, object, str, bool)
    
    def __init__(self, parent=None):
        super().__init__("通知", True, parent)  # 默认展开状态
        self.notifications = []
        
        # 通知数据文件路径
        self.notifications_file = "data/homepage/notifications.json"
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.notifications_file), exist_ok=True)
        
        # 连接信号到槽函数
        self.notify_signal.connect(self._notify)
        
        # 添加未读消息计数标签到标题
        self.add_unread_count_label()
        
        # 设置通知布局（垂直布局）
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setSpacing(0)  # 通知项之间紧挨
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 加载保存的通知
        self.load_notifications()
    
    def add_unread_count_label(self):
        """添加未读消息计数标签到标题"""
        # 获取标题布局
        title_layout = self.title_widget.layout()
        
        # 未读消息计数标签
        self.unread_count_label = QLabel()
        self.unread_count_label.setFixedSize(24, 24)
        self.unread_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.unread_count_label.setStyleSheet("""
            QLabel {
                background-color: #007AFF;
                border-radius: 12px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.unread_count_label.hide()  # 初始隐藏
        
        # 插入到标题标签后面
        title_layout.insertWidget(2, self.unread_count_label)
    
    def get_unread_count(self):
        """获取未读通知数量"""
        return sum(1 for notification in self.notifications if not notification.is_read)
    
    def update_unread_count(self):
        """更新未读消息计数"""
        unread_count = self.get_unread_count()
        
        self.unread_count_label.setText(str(unread_count))
        if unread_count > 0:
            # 显示未读计数
            self.unread_count_label.show()
        else:
            # 隐藏未读计数
            self.unread_count_label.hide()
    
    def notify(self,
            title="来自助手的通知",
            content="助手没收到更多内容哦",
            click_action=None,
            icon_path='',
            is_read=False):
        """添加新通知（线程安全版本）"""
        # 如果当前线程不是主线程，使用信号槽机制
        if QThread.currentThread() != self.thread():
            self.notify_signal.emit(title, content, click_action, icon_path, is_read)
            return
        
        # 在主线程中直接执行
        return self._notify(title, content, click_action, icon_path, is_read)
    
    def _notify(self,
            title="来自助手的通知",
            content="助手没收到更多内容哦",
            click_action=None,
            icon_path='',
            is_read=False):
        """线程安全的通知添加方法（在主线程中执行）"""
        # 添加通知项
        notification_item = NotificationItemWidget(
            title, content, click_action, icon_path, is_read, self
        )
        
        # 将新通知插入到列表的开头（最新的在最前面）
        self.notifications.insert(0, notification_item)
        
        # 如果有其他通知，在新通知下方添加分界线
        if len(self.notifications) > 1:
            separator = QLabel()
            separator.setFixedHeight(1)
            separator.setStyleSheet("background-color: #808080;")
            self.content_layout.insertWidget(0, separator)
        
        # 将新通知插入到布局的开头（显示在最上方）
        self.content_layout.insertWidget(0, notification_item)
        
        # 发送系统弹窗气泡通知
        notification_item.send_system_notification()
        
        # 保存通知到文件
        self.save_notifications()
        
        # 更新未读计数
        self.update_unread_count()

        # 窗口高亮提示
        QApplication.alert(self.window())

        return notification_item
    
    def remove_notification(self, notification_item):
        """移除通知"""
        if notification_item in self.notifications:
            # 获取通知项在布局中的索引
            item_index = self.notifications.index(notification_item)
            
            # 计算需要移除的部件索引
            # 每个通知项前面可能有一个分界线（除了第一个）
            layout_index = item_index * 2  # 每个通知项占用2个位置（分界线 + 通知项）
            
            # 从布局中移除通知项
            layout_item = self.content_layout.itemAt(layout_index)
            if layout_item:
                widget = layout_item.widget()
                if widget and widget == notification_item:
                    self.content_layout.removeWidget(widget)
                    widget.setParent(None)
                    widget.deleteLater()
            
            # 如果这不是第一个通知项，移除前面的分界线
            if item_index > 0:
                separator_index = layout_index - 1
                separator_item = self.content_layout.itemAt(separator_index)
                if separator_item:
                    separator_widget = separator_item.widget()
                    if separator_widget:
                        self.content_layout.removeWidget(separator_widget)
                        separator_widget.setParent(None)
                        separator_widget.deleteLater()
            
            # 如果这是第一个通知项而且不仅有一个通知项，移除后面的分界线
            elif item_index == 0 and len(self.notifications) > 1:
                separator_index = layout_index # 第一个通知已被移除
                separator_item = self.content_layout.itemAt(separator_index)
                if separator_item:
                    separator_widget = separator_item.widget()
                    if separator_widget:
                        self.content_layout.removeWidget(separator_widget)
                        separator_widget.setParent(None)
                        separator_widget.deleteLater()
            
            # 从列表中移除
            self.notifications.remove(notification_item)
            
            # 保存更新后的通知列表
            self.save_notifications()
            
            # 更新未读计数
            self.update_unread_count()
            
    def clear_notifications(self):
        """清空所有通知"""
        # 清空布局中的所有部件
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    self.content_layout.removeWidget(widget)
                    widget.setParent(None)
                    widget.deleteLater()
        
        self.notifications.clear()
        
        # 更新未读计数
        self.update_unread_count()
    
    def mark_all_as_read(self):
        """标记所有通知为已读"""
        for notification in self.notifications:
            notification.mark_as_read()
        # 保存更新后的状态
        self.save_notifications()
        # 更新未读计数
        self.update_unread_count()
    
    def save_notifications(self):
        """保存通知到JSON文件"""
        notifications_data = []
        for notification in self.notifications:
            notification_data = {
                "title": notification.title,
                "content": notification.content,
                "is_read": notification.is_read,
                "create_time": notification.create_time.isoformat(),
                "icon_path": notification.icon_path,
                "click_action": notification.click_action  # 保存点击操作字典
            }
            notifications_data.append(notification_data)
        
        with open(self.notifications_file, 'w', encoding='utf-8') as f:
            json.dump(notifications_data, f, ensure_ascii=False, indent=4)
    
    def load_notifications(self):
        """从JSON文件加载通知"""
        if not os.path.exists(self.notifications_file):
            return
        
        with open(self.notifications_file, 'r', encoding='utf-8') as f:
            notifications_data = json.load(f)
        
        # 清空现有通知
        self.clear_notifications()
        
        # 直接创建通知项（不使用add_notification方法）
        for i, notification_data in enumerate(notifications_data):
            notification_item = NotificationItemWidget(
                title=notification_data["title"],
                content=notification_data["content"],
                click_action=notification_data.get("click_action"),
                icon_path=notification_data.get("icon_path", ''),
                is_read=notification_data["is_read"],
                notification_system=self,
                create_time=datetime.datetime.fromisoformat(notification_data["create_time"])
            )
            
            # 添加到列表
            self.notifications.append(notification_item)
            
            # 如果不是第一个通知项，先添加分界线
            if i > 0:
                separator = QLabel()
                separator.setFixedHeight(1)
                separator.setStyleSheet("background-color: #808080;")
                self.content_layout.addWidget(separator)
            
            # 添加通知项到布局
            self.content_layout.addWidget(notification_item)
            
            # 更新已读状态样式
            notification_item.update_read_style()
        
        # 更新未读计数
        self.update_unread_count()

notification_system = NotificationSystemWidget()


class AppItemWidget(QWidget):
    """应用图标部件，显示单个应用的图标和名称"""
    
    def __init__(self, app_name, display_name, icon_path=None, description="", parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self.display_name = display_name
        self.description = description
        
        # 设置图标路径
        if icon_path:
            self.icon_path = icon_path
        else:
            # 默认路径：apps/应用名/icon.svg
            self.icon_path = os.path.join("apps", app_name, "icon.svg")
        
        # 检查图标文件是否存在，如果不存在则使用默认图标
        if not os.path.exists(self.icon_path):
            self.icon_path = os.path.join("apps", "default", "icon.svg")
        
        # 设置组件样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(80, 100)  # 固定尺寸
        self.setStyleSheet("""
            AppItemWidget {
                border-radius: 10px;
            }
            AppItemWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        # 设置悬停提示
        if self.description:
            self.setToolTip(self.description)
        
        # 创建布局和部件
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(5)
        
        # 加载并设置图标
        self.svg_widget = QSvgWidget(self.icon_path)
        self.svg_widget.setFixedSize(48, 48)
        layout.addWidget(self.svg_widget)
        
        # 应用名称
        self.name_label = QLabel(self.display_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("""
            font-size: 12px;
            color: #FFFFFF;
        """)
        layout.addWidget(self.name_label)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_app()
        super().mousePressEvent(event)
    
    def open_app(self):
        """打开应用对应的窗口"""
        app_info = APP_LIST.get(self.app_name)
        if app_info and "window" in app_info:
            app_info["window"]().show()
        else:
            raise TypeError(f"应用 {self.app_name} 未定义或没有窗口函数")


class AppEntryWidget(CollapsibleContainerWidget):
    """应用入口部件，支持折叠/展开显示应用图标"""
    
    def __init__(self, parent=None):
        super().__init__("应用", False, parent)
        
        # 加载应用列表
        self.load_apps()
        
        # 应用图标容器（水平布局）
        self.content_layout = QHBoxLayout(self.content_container)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 填充应用图标
        self.populate_apps()
    
    def load_apps(self):
        """加载应用列表"""
        from apps import APP_LIST
        self.apps = APP_LIST
    
    def add_app(self, app_name, app_info):
        """添加应用图标"""
        app_icon = AppItemWidget(
            app_name=app_name,
            display_name=app_info.get("display_name", app_name),
            icon_path=app_info.get("icon"),
            description=app_info.get("description", "")
        )
        self.content_layout.addWidget(app_icon)
    
    def populate_apps(self):
        """填充应用图标"""
        # 清空现有应用图标
        self.clear_apps()
        
        # 添加应用图标
        for app_name, app_info in self.apps.items():
            self.add_app(app_name, app_info)

    def delete_app(self, idx):
        """删除应用图标"""
        item = self.content_layout.itemAt(idx)
        if item:
            widget = item.widget()
            if widget:
                self.content_layout.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
        
    
    def clear_apps(self):
        """清空应用图标"""
        for i in reversed(range(self.content_layout.count())):
            self.delete_app(i)

app_entry = AppEntryWidget()
