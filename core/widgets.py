import numpy as np
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtCore import QRectF
import datetime
import math
from core.isFirstToday import get_today

class ExampleWidget(QWidget):
    """示例内容部件，包含文本和切换按钮"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化显示状态
        self.is_hello = True
        
        # 创建布局和部件
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建布局
        layout = QHBoxLayout()
        
        # 创建文本标签
        self.text_label = QLabel("Hello, world!")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 创建切换按钮
        self.toggle_button = QPushButton("切换文字")
        
        # 连接按钮点击事件
        self.toggle_button.clicked.connect(self.toggle_text)
        
        # 将部件添加到布局
        layout.addWidget(self.text_label)
        layout.addWidget(self.toggle_button)
        
        # 设置布局
        self.setLayout(layout)
    
    def toggle_text(self):
        """切换显示的文本"""
        if self.is_hello:
            # 切换到另一段文字
            self.text_label.setText("欢迎使用PySide6应用程序！\n这是一个功能演示。")
        else:
            # 切换回Hello world
            self.text_label.setText("Hello, world!")
        
        # 切换状态
        self.is_hello = not self.is_hello

class ClockWidget(QWidget):
    """时钟部件，显示三个同心环进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置环的宽度
        self.ring_width = 8
        self.dot_size = 8
        
        # 设置组件的最小尺寸
        self.setMinimumSize(128, 128)
        
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
        
        # 设置画笔（蓝色）
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
        
        # 设置画笔（绿色）
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
        """绘制外环：本日状态（灰色虚线 + 黄色圆点）"""
        # 计算环的矩形区域
        rect = QRectF(center_x - radius, center_y - radius, 
                     radius * 2, radius * 2)
        
        # 绘制灰色细虚线背景环
        bg_pen = QPen(QColor(100, 100, 100))  # 灰色
        bg_pen.setWidth(1)  # 细虚线
        bg_pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 5760)  # 完整的虚线环
        
        # 计算黄色圆点的位置
        angle_rad = (90 - progress * 360) * np.pi / 180  # 转换为弧度，从顶部开始顺时针
        dot_x = center_x + radius * np.cos(angle_rad)
        dot_y = center_y - radius * np.sin(angle_rad)  # Y轴向下为正
        
        # 绘制黄色圆点
        painter.setBrush(QBrush(QColor(255, 255, 0)))  # 黄色填充
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(dot_x - self.dot_size / 2), int(dot_y - self.dot_size / 2), 
                          self.dot_size, self.dot_size)

class TopStatusWidget(QWidget):
    """顶部状态部件，包含时钟、日期、周次、时期、季节"""
    pass