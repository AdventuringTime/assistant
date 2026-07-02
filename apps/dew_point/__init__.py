import math

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox)
from PySide6.QtCore import Qt, QEvent, QTimer

from core.base_objects import BaseDialog


# Magnus 公式常数（水面）
A = 17.27
B = 237.7


def calc_dew_point(temperature, humidity):
    """
    使用 Magnus 公式计算露点温度

    Parameters:
        temperature (float): 温度（摄氏度）
        humidity (float): 相对湿度（百分比，0~100）

    Returns:
        float: 露点温度（摄氏度），输入无效时返回 NaN
    """
    if humidity <= 0 or temperature < -100 or temperature > 100:
        return float('nan')

    # γ(T, RH) = (a * T) / (b + T) + ln(RH / 100)
    gamma = (A * temperature) / (B + temperature) + math.log(humidity / 100.0)
    # Td = (b * γ) / (a - γ)
    dew_point = (B * gamma) / (A - gamma)
    return dew_point


class DewPointDialog(BaseDialog):
    """露点计算对话框，根据温度和湿度计算并实时显示露点温度"""

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
        初始化露点计算对话框

        Parameters:
            parent (QWidget, optional): 父窗口
        """
        if DewPointDialog._initialized:
            return
        super().__init__(parent)

        self.setWindowTitle("露点计算")

        layout = QVBoxLayout(self)

        # 温度输入
        temp_layout = QHBoxLayout()
        self.temp_label = QLabel("温度（℃）：")
        self.temp_spinbox = QDoubleSpinBox()
        self.temp_spinbox.setRange(-50, 50)
        self.temp_spinbox.setDecimals(1)
        self.temp_spinbox.setSingleStep(1)
        self.temp_spinbox.setValue(25.0)
        self.temp_spinbox.valueChanged.connect(self.on_value_changed)
        self.temp_spinbox.installEventFilter(self)
        temp_layout.addWidget(self.temp_label)
        temp_layout.addWidget(self.temp_spinbox)
        layout.addLayout(temp_layout)

        # 湿度输入
        humidity_layout = QHBoxLayout()
        self.humidity_label = QLabel("湿度（%）：")
        self.humidity_spinbox = QDoubleSpinBox()
        self.humidity_spinbox.setRange(0.1, 100)
        self.humidity_spinbox.setDecimals(1)
        self.humidity_spinbox.setSingleStep(5)
        self.humidity_spinbox.setValue(50.0)
        self.humidity_spinbox.valueChanged.connect(self.on_value_changed)
        self.humidity_spinbox.installEventFilter(self)
        humidity_layout.addWidget(self.humidity_label)
        humidity_layout.addWidget(self.humidity_spinbox)
        layout.addLayout(humidity_layout)

        # 露点输出
        dew_layout = QHBoxLayout()
        self.dew_label = QLabel("露点（℃）：")
        self.dew_spinbox = QDoubleSpinBox()
        self.dew_spinbox.setRange(-273.2, 50)
        self.dew_spinbox.setDecimals(1)
        self.dew_spinbox.setReadOnly(True)
        self.dew_spinbox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        dew_layout.addWidget(self.dew_label)
        dew_layout.addWidget(self.dew_spinbox)
        layout.addLayout(dew_layout)

        self.dew_spinbox.setValue(13.8)

        DewPointDialog._instance = self
        DewPointDialog._initialized = True

    def on_value_changed(self):
        """当温度或湿度值改变时，若输入完整则重新计算并更新露点温度"""
        # 检查两个输入框的文本是否完整有效
        if not self.temp_spinbox.hasAcceptableInput() or not self.humidity_spinbox.hasAcceptableInput():
            return

        temp = self.temp_spinbox.value()
        humidity = self.humidity_spinbox.value()

        dew_point = calc_dew_point(temp, humidity)
        if not math.isnan(dew_point):
            self.dew_spinbox.setValue(round(dew_point, 1))

    def eventFilter(self, obj, event):
        """
        事件过滤器，实现输入框聚焦时自动全选

        Parameters:
            obj (QObject): 事件源对象
            event (QEvent): 事件对象

        Returns:
            bool: 是否拦截事件
        """
        if event.type() == QEvent.Type.FocusIn:
            if obj in (self.temp_spinbox, self.humidity_spinbox):
                QTimer.singleShot(0, obj.selectAll)
        return super().eventFilter(obj, event)