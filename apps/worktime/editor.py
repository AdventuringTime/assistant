from core.base_objects import BaseDialog
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                              QPushButton, QMessageBox)
from PySide6.QtCore import QTime
from core.base_objects import DeleteButton
from core.widgets import SettingItemWidget


class EditorWindow(BaseDialog):
    """工作时间编辑窗口，用于创建和编辑工作时间记录"""

    def __init__(self, parent, year, month, day, item=None, id_=None):
        """
        初始化工作时间编辑窗口

        Parameters:
            parent (QWidget): 父窗口
            year (int): 年份
            month (int): 月份
            day (int): 日期
            item (dict, optional): 待编辑的工作时间记录，None表示新建
            id_ (int, optional): 记录索引ID
        """
        super().__init__(parent)
        self.item = item or {} # a if a else b
        self.is_new = item is None

        self.year = year
        self.month = month
        self.day = day
        self.id_ = id_

        self.setModal(True) # 同时修改多个记录会有bug

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """初始化UI界面，创建表单控件和按钮"""
        self.setWindowTitle("工作时间项")
        self.setMinimumSize(500, 400)

        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建编辑器
        self.start_time_editor = SettingItemWidget("上班时间", "time")
        self.end_time_editor = SettingItemWidget("下班时间", "time")
        self.rest_editor = SettingItemWidget("休息时间", "time")
        self.description_editor = SettingItemWidget("描述", "text")

        # 添加到主布局
        main_layout.addWidget(self.start_time_editor)
        main_layout.addWidget(self.end_time_editor)
        main_layout.addWidget(self.rest_editor)
        main_layout.addWidget(self.description_editor)
        main_layout.addStretch()

        # 按钮布局
        button_layout = QHBoxLayout()

        if not self.is_new:
            self.delete_button = DeleteButton("删除")
            self.delete_button.clicked.connect(self.delete)
            button_layout.addWidget(self.delete_button)

        button_layout.addStretch()

        if not self.is_new:
            self.saveas_button = QPushButton("保存副本")
            self.saveas_button.clicked.connect(lambda: self.save(copy=True))
            button_layout.addWidget(self.saveas_button)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

    def load_data(self):
        """从item中加载数据到表单控件"""
        if self.item:
            start_time_str = self.item.get("from")
            if start_time_str:
                start_time = QTime.fromString(start_time_str, "HH:mm")
                self.start_time_editor.set_value(start_time)

            end_time_str = self.item.get("to")
            if end_time_str:
                end_time = QTime.fromString(end_time_str, "HH:mm")
                self.end_time_editor.set_value(end_time)

            rest_time_str = self.item.get("rest")
            if rest_time_str:
                rest_time = QTime.fromString(rest_time_str, "HH:mm")
                self.rest_editor.set_value(rest_time)

            description = self.item.get("description")
            if description:
                self.description_editor.set_value(description)

    def save(self, copy=False):
        """
        保存工作时间记录

        Parameters:
            copy (bool, optional): 是否保存为副本，默认为False
        """
        # 读取数据
        start_time = self.start_time_editor.get_value() or QTime(0, 0)
        end_time = self.end_time_editor.get_value() or QTime(0, 0)
        rest_time = self.rest_editor.get_value() or QTime(0, 0)
        description = self.description_editor.get_value()

        # 计算工作时长
        duration_secs = start_time.secsTo(end_time)
        if duration_secs < 0:
            duration_secs += 86400
        duration_secs -= QTime(0, 0).secsTo(rest_time)

        total_work = QTime(0, 0).addSecs(duration_secs)

        # 构建数据
        self.data_dict = {
            "from": start_time.toString("HH:mm"),
            "to": end_time.toString("HH:mm"),
            "total_work": total_work.toString("HH:mm")
        }
        if rest_time and rest_time != QTime(0, 0):
            self.data_dict["rest"] = rest_time.toString("HH:mm")

        if description:
            self.data_dict["description"] = description

        # 调用父窗口的保存方法
        self.parent().window().save_worktime_of_editor(self, copy=copy)

        # 关闭窗口
        self.close()

    def delete(self):
        """删除当前工作时间记录，需用户确认"""
        reply = QMessageBox.question(self, "确认删除",
                                   "确认删除？",
                                   QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Yes)

        if reply == QMessageBox.StandardButton.Yes:
            # 调用父窗口的删除方法
            self.parent().window().delete_worktime_of_editor(self)

            # 关闭窗口
            self.close()