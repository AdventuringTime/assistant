import os
import json
from PySide6.QtWidgets import (
    QDialog, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QProgressBar, QScrollArea, QDateEdit, QMessageBox,
    QInputDialog, QSpinBox, QSizePolicy, QDoubleSpinBox, QListWidget,
    QTabWidget
)
from PySide6.QtCore import QDate, Qt, QUrl, QPointF
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtGui import QDesktopServices, QPainter, QColor
from PySide6.QtCharts import (QChart, QChartView, QLineSeries, QValueAxis,
                              QBarCategoryAxis)

from core.base_objects import BaseWindow, BaseDialog, DeleteButton
from core.functions import get_today, block_signals


def evaluate_estimated_amount(expression="0", constants=None):
    """
    评估预估金额表达式，支持常量替换

    Parameters:
        expression (str): 数学表达式，可包含常量名称
        constants (dict, optional): 常量字典，键为常量名，值为常量值

    Returns:
        float or str: 计算结果（浮点数）或 "Error"（表达式无效时）
    """
    constants = constants or {}
    expr = expression
    for name, value in constants.items():
        expr = expr.replace(name, str(value))
    if expr.strip() == "":
        return 0.
    try:
        return float(eval(expr))
    except:
        return "Error"


class ExpenseDataManager:
    """数据维护类，管理所有月份的记账数据，支持内存优先读取和延迟保存"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ExpenseDataManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.month_data = {}
        self.modified = set()
        self._initialized = True

    def load_month_data(self, year, month):
        """
        加载指定月份的数据，优先从内存读取
        
        Parameters:
            year (int): 年份
            month (int): 月份（1-12）
        Returns:
            dict: 包含常量和子项数据的字典
            如果数据不存在，返回空字典
        """
        key = f"{year}-{month:02d}"

        if key in self.month_data:
            return self.month_data[key]

        data_path = os.path.join("apps/expenses/data", f"{key}.json")
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                'constants': {},
                'children': []
            }

        self.month_data[key] = data
        return data

    def mark_modified(self, year, month):
        """
        标记指定月份的数据已被修改
        
        Parameters:
            year (int): 年份
            month (int): 月份（1-12）
        """
        key = f"{year}-{month:02d}"
        self.modified.add(key)

    def save_all_modified(self):
        """保存所有被修改过的数据到硬盘"""
        for key in self.modified:
            data_path = os.path.join("apps/expenses/data", f"{key}.json")

            def remove_expanded_field(children):
                for child in children:
                    if 'expanded' in child:
                        del child['expanded']
                    if child.get('children'):
                        remove_expanded_field(child['children'])

            data = self.month_data[key].copy()
            if 'children' in data:
                remove_expanded_field(data['children'])

            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        self.modified.clear()


class SortDialog(BaseDialog):
    """排序对话框，支持拖拽排序列表项"""

    def __init__(self, parent, children, title="排序"):
        """
        初始化排序对话框

        Parameters:
            parent (QWidget): 父窗口
            children (list): 待排序的项列表，每项需包含 'name' 键
            title (str, optional): 对话框标题，默认为"排序"
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.children = children

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        layout.addWidget(self.list_widget)

        for child in self.children:
            self.list_widget.addItem(child['name'])

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

        self.result = None

    def accept(self):
        """确认排序，根据列表顺序重新排列项"""
        new_order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = item.text()
            for child in self.children:
                if child['name'] == name and child not in new_order:
                    new_order.append(child)
                    break
        self.result = new_order
        super().accept()

    def reject(self):
        """取消排序，返回None"""
        self.result = None
        super().reject()


class ConstantEditWindow(BaseWindow):
    """常量编辑窗口，用于管理记账系统中的数学常量"""

    def __init__(self, parent):
        """
        初始化常量编辑窗口

        Parameters:
            parent (QWidget): 父窗口（应为 ExpenseRecordWidget 实例）
        """
        super().__init__(parent)
        self.record_widget = parent
        assert isinstance(self.record_widget, ExpenseRecordWidget)

        self.setWindowTitle("常量编辑")
        self.setMinimumSize(400, 300)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.constants_scroll_area = QScrollArea()
        self.constants_scroll_area.setWidgetResizable(True)
        self.constants_widget = QWidget(self.constants_scroll_area)
        self.constants_scroll_area.setWidget(self.constants_widget)
        self.constants_layout = QVBoxLayout()
        self.constants_widget.setLayout(self.constants_layout)
        layout.addWidget(self.constants_scroll_area)

        self.buttons_layout = QHBoxLayout()
        layout.addLayout(self.buttons_layout)

        self.buttons_layout.addStretch()

        add_button = QPushButton("添加常量")
        add_button.clicked.connect(self.add_constant)
        self.buttons_layout.addWidget(add_button)

        self.load_constants()

    def load_constants(self):
        """加载并显示所有常量"""
        while self.constants_layout.count() > 0:
            item = self.constants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name, value in self.record_widget.constants.items():
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)

            name_label = QLabel(name)
            name_label.setFixedWidth(40)
            row_layout.addWidget(name_label)

            value_edit = QSpinBox()
            value_edit.setValue(value)
            row_layout.addWidget(value_edit)

            delete_button = DeleteButton("🗑️")
            delete_button.setFixedWidth(24)
            row_layout.addWidget(delete_button)

            # 预存 name，防止全部连接到最后一项
            value_edit.valueChanged.connect(
                lambda val, name=name: self.update_constant(name, val))
            # 增加一个 checked，因为按钮点击事件会多传一个参数
            delete_button.clicked.connect(
                lambda checked=False, name=name: self.delete_constant(name))

            self.constants_layout.addWidget(row_widget)

        self.constants_layout.addStretch()

    def add_constant(self):
        """添加新常量"""
        name, ok = QInputDialog.getText(self, "添加常量", "输入常量名称:")
        if ok:
            if not name:
                QMessageBox.warning(self, "请输入常量名称", "请输入常量名称")
                return
            if name in self.record_widget.constants:
                QMessageBox.warning(self, "常量名称已存在", "常量名称已存在")
                return
            self.record_widget.constants[name] = 0
            self.record_widget.mark_modified_and_reload()
            self.load_constants()

    def delete_constant(self, name):
        """
        删除指定常量

        Parameters:
            name (str): 常量名称
        """
        if name in self.record_widget.constants:
            del self.record_widget.constants[name]
            self.record_widget.mark_modified_and_reload()
            self.load_constants()

    def update_constant(self, name, value):
        """
        更新常量值

        Parameters:
            name (str): 常量名称
            value (int): 新的常量值
        """
        if name in self.record_widget.constants:
            self.record_widget.constants[name] = value
            self.record_widget.mark_modified_and_reload()


class ExpenseItemWidget(QWidget):
    """单个费用项部件，显示预算和实际支出"""

    def __init__(self, item_data, constants, parent=None):
        """
        初始化费用项部件

        Parameters:
            item_data (dict): 费用项数据
            constants (dict): 常量字典
            parent (QWidget, optional): 父控件
        """
        super().__init__(parent)
        self.item_data = item_data
        self.constants = constants

        self.main_layout = QVBoxLayout(self)

        top_row = QHBoxLayout()

        self.name_label = QLabel(self.item_data['name'])
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        estimated_value = self.get_estimated_value()
        self.estimated_label = QLabel("Error" if estimated_value == "Error" else f"{estimated_value:.2f}")
        top_row.addWidget(self.estimated_label)

        self.actual_label = QLabel(f"{self.item_data.get('actual_amount', 0.):.2f}")
        top_row.addWidget(self.actual_label)

        self.main_layout.addLayout(top_row)

        self.bottom_row = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.bottom_row.addWidget(self.progress_bar)

        self.rename_button = QPushButton("✏️")
        self.rename_button.setStyleSheet("padding: 0;")
        self.rename_button.setToolTip("重命名")
        self.rename_button.clicked.connect(self.rename)
        self.rename_button.setFixedSize(24, 24)
        self.bottom_row.addWidget(self.rename_button)

        self.delete_button = DeleteButton("🗑️")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #641A1A;
                color: #FFFFFF;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #6B2020;
            }
            QPushButton:pressed {
                background-color: #4A1515;
            }
        """)
        self.delete_button.setToolTip("删除")
        self.delete_button.clicked.connect(self.delete)
        self.delete_button.setFixedSize(24, 24)
        self.bottom_row.addWidget(self.delete_button)

        self.modify_budget_button = QPushButton("🎯")
        self.modify_budget_button.setStyleSheet("padding: 0;")
        self.modify_budget_button.setToolTip("修改预算")
        self.modify_budget_button.clicked.connect(self.modify_budget)
        self.modify_budget_button.setFixedSize(24, 24)
        self.bottom_row.addWidget(self.modify_budget_button)

        self.record_button = QPushButton("📝")
        self.record_button.setStyleSheet("padding: 0;")
        self.record_button.setToolTip("记账")
        self.record_button.clicked.connect(self.record)
        self.record_button.setFixedSize(24, 24)
        self.bottom_row.addWidget(self.record_button)

        self.main_layout.addLayout(self.bottom_row)

        self.update_progress()

    def get_estimated_value(self):
        """获取预估金额值"""
        return evaluate_estimated_amount(self.item_data.get('estimated_amount', "0"), self.constants)

    def update_progress(self):
        """更新进度条显示"""
        estimated = self.get_estimated_value()
        actual = self.item_data.get('actual_amount', 0.)

        if estimated == "Error":
            self.estimated_label.setText("Error")
        else:
            self.estimated_label.setText(f"{estimated:.2f}")

        if estimated == 0 or estimated == "Error":
            self.progress_bar.setValue(0)
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00FF00; };")
        else:
            progress = actual / estimated
            ratio = min(max(progress, 0), 1)
            self.progress_bar.setValue(int(ratio * 100))

            ratio2 = min(max(progress / 2, 0), 1)
            r = int(255 * ratio2)
            g = int(255 * (1 - ratio2))
            self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r}, {g}, 0); }}")

    def rename(self):
        """重命名费用项"""
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=self.item_data['name'])
        if ok and new_name:
            self.item_data['name'] = new_name
            self.name_label.setText(new_name)
            self.window().record_widget.mark_modified_and_reload()

    def delete(self):
        """删除费用项"""
        self.window().record_widget.remove_item(self.item_data)

    def modify_budget(self):
        """修改预算金额"""
        new_budget, ok = QInputDialog.getText(self, "修改预算", "输入新预算:", text=self.item_data.get('estimated_amount', "0"))
        if ok and new_budget != self.item_data.get('estimated_amount'):
            self.item_data['estimated_amount'] = new_budget
            self.update_progress()
            self.window().record_widget.mark_modified_and_reload()

    def record(self):
        """记账，使实际消费增加指定金额"""
        amount, ok = QInputDialog.getDouble(self, "记账", f"记账:", value=0, decimals=2)
        if ok and amount != 0:
            self.item_data['actual_amount'] = round(self.item_data['actual_amount'] + amount, 2)
            self.update_progress()
            self.window().record_widget.mark_modified_and_reload()


class ExpenseTypeWidget(QWidget):
    """费用类型部件，支持展开/折叠，包含子项和子类型"""

    def __init__(self, type_data, constants, parent=None):
        """
        初始化费用类型部件

        Parameters:
            type_data (dict): 类型数据
            constants (dict): 常量字典
            parent (QWidget, optional): 父控件
        """
        super().__init__(parent)
        self.type_data = type_data
        self.constants = constants
        self.is_expanded = type_data.get('expanded', True)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.header = QWidget()
        header_layout = QVBoxLayout(self.header)

        top_row = QHBoxLayout()

        self.expand_svg = QSvgWidget("assets/svg/expanded.svg")
        self.expand_svg.setFixedSize(24, 24)
        top_row.addWidget(self.expand_svg)

        self.name_label = QLabel(self.type_data['name'])
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        self.total_estimated_label = QLabel("0.00")
        top_row.addWidget(self.total_estimated_label)

        self.total_actual_label = QLabel("0.00")
        top_row.addWidget(self.total_actual_label)

        header_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bottom_row.addWidget(self.progress_bar)

        self.sort_button = QPushButton("↕️")
        self.sort_button.setStyleSheet("padding: 0;")
        self.sort_button.setToolTip("排序")
        self.sort_button.clicked.connect(self.open_sort_dialog)
        self.sort_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.sort_button)

        self.rename_button = QPushButton("✏️")
        self.rename_button.setStyleSheet("padding: 0;")
        self.rename_button.setToolTip("重命名")
        self.rename_button.clicked.connect(self.rename)
        self.rename_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.rename_button)

        self.delete_button = QPushButton("🗑️")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #641A1A;
                color: #FFFFFF;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #6B2020;
            }
            QPushButton:pressed {
                background-color: #4A1515;
            }
        """)
        self.delete_button.setToolTip("删除")
        self.delete_button.clicked.connect(self.delete)
        self.delete_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.delete_button)

        self.add_item_button = QPushButton("➕")
        self.add_item_button.setStyleSheet("padding: 0;")
        self.add_item_button.setToolTip("添加记账项")
        self.add_item_button.clicked.connect(self.add_item)
        self.add_item_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.add_item_button)

        self.add_type_button = QPushButton("📂")
        self.add_type_button.setStyleSheet("padding: 0;")
        self.add_type_button.setToolTip("添加子类型")
        self.add_type_button.clicked.connect(self.add_subtype)
        self.add_type_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.add_type_button)

        header_layout.addLayout(bottom_row)

        self.main_layout.addWidget(self.header)

        self.children_container = QWidget()
        self.children_layout = QVBoxLayout(self.children_container)
        self.children_layout.setContentsMargins(10, 0, 0, 0)
        self.main_layout.addWidget(self.children_container)

        self.header.mousePressEvent = lambda e: self.toggle_expand()

        self.load_children()
        self.update_totals()

    def toggle_expand(self):
        """切换展开/折叠状态"""
        self.is_expanded = not self.is_expanded
        self.type_data['expanded'] = self.is_expanded
        self.expand_svg.load("assets/svg/expanded.svg" if self.is_expanded else "assets/svg/collapsed.svg")
        self.children_container.setVisible(self.is_expanded)

    def rename(self):
        """重命名费用类型"""
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=self.type_data['name'])
        if ok and new_name:
            self.type_data['name'] = new_name
            self.name_label.setText(new_name)
            self.window().record_widget.mark_modified_and_reload()

    def delete(self):
        """删除费用类型"""
        self.window().record_widget.remove_type(self.type_data)

    def add_item(self):
        """添加子记账项"""
        name, ok = QInputDialog.getText(self, "添加记账项", "输入记账项名称:")
        if ok and name:
            if 'children' not in self.type_data:
                self.type_data['children'] = []
            self.type_data['children'].append({
                'type': 'item',
                'name': name,
                'estimated_amount': "0",
                'actual_amount': 0
            })
            self.window().record_widget.mark_modified_and_reload()

    def add_subtype(self):
        """添加子类型"""
        name, ok = QInputDialog.getText(self, "添加子类型", "输入子类型名称:")
        if ok and name:
            if 'children' not in self.type_data:
                self.type_data['children'] = []
            self.type_data['children'].append({
                'type': 'type',
                'name': name,
                'children': []
            })
            self.window().record_widget.mark_modified_and_reload()

    def open_sort_dialog(self):
        """打开子项排序对话框"""
        children = self.type_data.get('children', [])
        if not children:
            return

        dialog = SortDialog(self, children, f"排序 - {self.type_data['name']}")
        dialog.show()

        def check_result():
            if dialog.result is not None:
                self.type_data['children'] = dialog.result
                self.window().record_widget.mark_modified_and_reload()

        dialog.destroyed.connect(check_result)

    def load_children(self):
        """加载并显示所有子项和子类型"""
        while self.children_layout.count() > 0:
            item = self.children_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        children = self.type_data.get('children', [])
        for child_data in children:
            if child_data['type'] == 'item':
                item_widget = ExpenseItemWidget(child_data, self.constants)
                self.children_layout.addWidget(item_widget)
            elif child_data['type'] == 'type':
                type_widget = ExpenseTypeWidget(child_data, self.constants)
                self.children_layout.addWidget(type_widget)

    def get_total_estimated(self, type_data=None):
        """
        递归计算预估总金额

        Parameters:
            type_data (dict, optional): 类型数据，默认为当前类型

        Returns:
            float or str: 总预估金额或 "Error"
        """
        if type_data is None:
            type_data = self.type_data
        total = 0.
        for child in type_data.get('children', []):
            if child['type'] == 'item':
                val = evaluate_estimated_amount(child.get('estimated_amount', "0"), self.constants)
                if val == "Error":
                    return "Error"
                total += val
            elif child['type'] == 'type':
                val = self.get_total_estimated(child)
                if val == "Error":
                    return "Error"
                total += val
        return total

    def get_total_actual(self, type_data=None):
        """
        递归计算实际总金额

        Parameters:
            type_data (dict, optional): 类型数据，默认为当前类型

        Returns:
            float: 总实际金额
        """
        if type_data is None:
            type_data = self.type_data
        total = 0.
        for child in type_data.get('children', []):
            if child['type'] == 'item':
                total += child.get('actual_amount', 0)
            elif child['type'] == 'type':
                total += self.get_total_actual(child)
        return total

    def update_totals(self):
        """更新总计金额和进度条显示"""
        estimated = self.get_total_estimated()
        actual = self.get_total_actual()

        self.total_estimated_label.setText("Error" if estimated == "Error" else f"{estimated:.2f}")
        self.total_actual_label.setText(f"{actual:.2f}")

        if estimated == 0 or estimated == "Error":
            self.progress_bar.setValue(0)
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00FF00; };")
        else:
            progress = actual / estimated
            ratio = min(max(progress, 0), 1)

            self.progress_bar.setValue(int(ratio * 100))

            ratio2 = min(max(progress / 2, 0), 1)
            r = int(255 * ratio2)
            g = int(255 * (1 - ratio2))
            self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r}, {g}, 0); }}")


class ExpenseRecordWidget(QWidget):
    """记账标签页部件，包含所有记账功能"""

    data_manager = ExpenseDataManager()

    def __init__(self, parent=None):
        """
        初始化记账标签页

        Parameters:
            parent (ExpensesWindow, optional): 父窗口
        """
        super().__init__(parent)

        self.constants = {}
        self.children_ = []

        main_layout = QVBoxLayout(self)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        self.total_widget = QWidget()
        total_layout = QVBoxLayout(self.total_widget)

        total_top_row = QHBoxLayout()
        total_label = QLabel("总计")
        total_top_row.addWidget(total_label)

        total_top_row.addStretch()

        self.total_estimated_label = QLabel("0.00")
        total_top_row.addWidget(self.total_estimated_label)

        self.total_actual_label = QLabel("0.00")
        total_top_row.addWidget(self.total_actual_label)
        total_layout.addLayout(total_top_row)

        total_bottom_row = QHBoxLayout()

        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setMaximum(100)
        self.total_progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        total_bottom_row.addWidget(self.total_progress_bar)

        self.sort_button = QPushButton("↕️")
        self.sort_button.setStyleSheet("padding: 0;")
        self.sort_button.setToolTip("排序")
        self.sort_button.clicked.connect(self.open_sort_dialog)
        self.sort_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.sort_button)

        self.modify_constants_button = QPushButton("🔢")
        self.modify_constants_button.setStyleSheet("padding: 0;")
        self.modify_constants_button.setToolTip("修改常量")
        self.modify_constants_button.clicked.connect(self.open_constants_window)
        self.modify_constants_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.modify_constants_button)

        self.add_item_button = QPushButton("➕")
        self.add_item_button.setStyleSheet("padding: 0;")
        self.add_item_button.setToolTip("添加记账项")
        self.add_item_button.clicked.connect(self.add_root_item)
        self.add_item_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.add_item_button)

        self.add_type_button = QPushButton("📂")
        self.add_type_button.setStyleSheet("padding: 0;")
        self.add_type_button.setToolTip("添加记账类型")
        self.add_type_button.clicked.connect(self.add_root_type)
        self.add_type_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.add_type_button)

        total_layout.addLayout(total_bottom_row)
        main_layout.addWidget(self.total_widget)

        self.bottom_buttons_layout = QHBoxLayout()

        self.bottom_buttons_layout.addStretch()

        open_ecard_paylist_button = QPushButton("打开交易明细")
        open_ecard_paylist_button.clicked.connect(self.open_ecard_paylist)
        self.bottom_buttons_layout.addWidget(open_ecard_paylist_button)

        main_layout.addLayout(self.bottom_buttons_layout)

    @staticmethod
    def open_ecard_paylist():
        """打开校园卡交易明细网页"""
        QDesktopServices.openUrl(QUrl("https://ecard.ustc.edu.cn/paylist"))

    def load_month_data(self, year, month):
        """
        加载指定月份的记账数据

        Parameters:
            year (int): 年份
            month (int): 月份
        """

        data = self.data_manager.load_month_data(year, month)
        self.constants = data.get('constants', {})
        self.children_ = data.get('children', [])

        self.update_expense_items_and_types()

    def update_expense_items_and_types(self):
        """根据数据更新费用项和类型部件"""
        while self.scroll_layout.count() > 0:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for child_data in self.children_:
            if child_data['type'] == 'item':
                item_widget = ExpenseItemWidget(child_data, self.constants)
                self.scroll_layout.addWidget(item_widget)
            elif child_data['type'] == 'type':
                type_widget = ExpenseTypeWidget(child_data, self.constants)
                self.scroll_layout.addWidget(type_widget)

        self.scroll_layout.addStretch()
        self.update_total_display()

    def mark_modified_and_reload(self):
        """在每次修改数据后，标记数据已修改并刷新UI"""
        expenses_window = self.window()
        self.data_manager.mark_modified(
            expenses_window.current_date.year(),
            expenses_window.current_date.month()
        )
        self.update_expense_items_and_types()

    def add_root_item(self):
        """在根级别添加记账项"""
        name, ok = QInputDialog.getText(self, "添加记账项", "输入记账项名称:")
        if ok and name:
            self.children_.append({
                'type': 'item',
                'name': name,
                'estimated_amount': "0",
                'actual_amount': 0
            })
            self.mark_modified_and_reload()

    def add_root_type(self):
        """在根级别添加记账类型"""
        name, ok = QInputDialog.getText(self, "添加记账类型", "输入记账类型名称:")
        if ok and name:
            self.children_.append({
                'type': 'type',
                'name': name,
                'children': []
            })
            self.mark_modified_and_reload()

    def open_sort_dialog(self):
        """打开根级别排序对话框"""
        if not self.children_:
            return

        dialog = SortDialog(self, self.children_, "排序")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.children_ = dialog.result
            self.mark_modified_and_reload()

    def remove_item(self, item_data):
        """
        删除指定的费用项

        Parameters:
            item_data (dict): 要删除的费用项数据
        """
        self._remove_from_children(self.children_, item_data)
        self.mark_modified_and_reload()

    def remove_type(self, type_data):
        """
        删除指定的费用类型

        Parameters:
            type_data (dict): 要删除的类型数据
        """
        self._remove_from_children(self.children_, type_data)
        self.mark_modified_and_reload()

    def _remove_from_children(self, children_list, target_data):
        """
        递归从子列表中删除指定数据

        Parameters:
            children_list (list): 子项列表
            target_data (dict): 目标数据

        Returns:
            bool: 仅在递归时使用，调用时不应接收该变量
        """
        for i, child in enumerate(children_list):
            if child is target_data:
                del children_list[i]
                return True
            if child.get('children'):
                if self._remove_from_children(child['children'], target_data):
                    return True
        return False

    def update_total_display(self):
        """更新总计金额显示和进度条"""
        estimated = self.get_total_estimated()
        actual = self.get_total_actual()

        self.total_estimated_label.setText("Error" if estimated == "Error" else f"{estimated:.2f}")
        self.total_actual_label.setText(f"{actual:.2f}")

        if estimated == 0 or estimated == "Error":
            self.total_progress_bar.setValue(0)
            self.total_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00FF00; };")
        else:
            progress = actual / estimated
            ratio = min(max(progress, 0), 1)

            self.total_progress_bar.setValue(int(ratio * 100))

            ratio2 = min(max(progress / 2, 0), 1)
            r = int(255 * ratio2)
            g = int(255 * (1 - ratio2))
            self.total_progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r}, {g}, 0); }}")

    def get_total_estimated(self, children_list=None):
        """
        递归计算所有子项的预估总金额

        Parameters:
            children_list (list, optional): 子项列表，默认为根级子项

        Returns:
            float or str: 总预估金额或 "Error"
        """
        if children_list is None:
            children_list = self.children_
        total = 0.
        for child in children_list:
            if child['type'] == 'item':
                val = evaluate_estimated_amount(child.get('estimated_amount', "0"), self.constants)
                if val == "Error":
                    return "Error"
                total += val
            elif child['type'] == 'type':
                val = self.get_total_estimated(child.get('children', []))
                if val == "Error":
                    return "Error"
                total += val
        return total

    def get_total_actual(self, children_list=None):
        """
        递归计算所有子项的实际总金额

        Parameters:
            children_list (list, optional): 子项列表，默认为根级子项

        Returns:
            float: 总实际金额
        """
        if children_list is None:
            children_list = self.children_
        total = 0.
        for child in children_list:
            if child['type'] == 'item':
                total += child.get('actual_amount', 0)
            elif child['type'] == 'type':
                total += self.get_total_actual(child.get('children', []))
        return total

    def open_constants_window(self):
        """打开常量编辑窗口"""
        self.constants_window = ConstantEditWindow(self)
        self.constants_window.show()


class TrendWidget(QWidget):
    """余额趋势部件，显示最近12个月余额折线图并支持修改"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_path = "apps/expenses/data/monthly_balance.json"
        self.modified = False
        self.load_data()

        main_layout = QVBoxLayout(self)

        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        main_layout.addWidget(self.chart_view)

        self.modify_widget = QWidget()
        self.modify_layout = QHBoxLayout(self.modify_widget)
        self.modify_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.modify_widget)

        self.balance_label = QLabel("")
        self.balance_label.setStyleSheet("color: white;")
        self.modify_layout.addWidget(self.balance_label)

        self.balance_spinbox = QDoubleSpinBox()
        self.balance_spinbox.setRange(-1e18, 1e18)
        self.balance_spinbox.setDecimals(2)
        self.balance_spinbox.valueChanged.connect(self.on_balance_changed)
        self.modify_layout.addWidget(self.balance_spinbox)

    def load_data(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.balance_data = json.load(f)
        else:
            self.balance_data = {}

    def update_view(self, year, month):
        self.update_chart(year, month)
        self.update_modify_widget(year, month)

    @staticmethod
    def get_last_12_months(year, month):
        months = []
        for m in range(month-1, month-13, -1):
            y = year
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m))
        months.reverse()
        return months

    def update_chart(self, year, month):
        chart = QChart()
        chart.setTheme(QChart.ChartThemeDark)
        chart.setTitle("最近12个月余额趋势")

        series = QLineSeries()
        months = self.get_last_12_months(year, month)
        month_labels = []
        valid_balances = []

        for y, m in months:
            key = f"{y}-{m:02d}"
            balance = self.balance_data.get(key)
            if balance:
                series.append(QPointF(len(month_labels), balance))
                valid_balances.append(balance)
            month_labels.append(f"{y % 100}-{m:02d}")
        
        max_balance = max(valid_balances) if valid_balances else 0.0

        series.setPointLabelsVisible(True)
        series.setPointLabelsFormat("@yPoint")
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(month_labels)
        axis_x.setGridLineVisible(False)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelsVisible(False)
        axis_y.setGridLineVisible(False)
        if max_balance > 0:
            axis_y.setMax(max_balance * 1.15)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().hide()
        self.chart_view.setChart(chart)

    def update_modify_widget(self, year, month):
        lm_year, lm_month = (year, month - 1) if month > 1 else (year - 1, 12)
        key = f"{lm_year}-{lm_month:02d}"
        balance = self.balance_data.get(key, 0.0)

        self.balance_label.setText(f"{lm_year}年{lm_month}月余额:")
        with block_signals([self.balance_spinbox]):
            self.balance_spinbox.setProperty("current_key", key)
            self.balance_spinbox.setValue(balance)

    def on_balance_changed(self, value):
        key = self.balance_spinbox.property("current_key")
        if not key:
            return

        old_value = self.balance_data.get(key, 0.0)
        if value != old_value:
            self.balance_data[key] = value
            self.modified = True
        
        if self.window():
            expenses_window = self.window()
            self.update_chart(expenses_window.current_date.year(), expenses_window.current_date.month())

    def save_if_modified(self):
        if self.modified:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.balance_data, f, ensure_ascii=False, indent=4)
            self.modified = False


class ExpensesWindow(BaseWindow):
    """记账管理窗口，用于管理月度费用预算和支出记录"""

    _instance = None
    _initialized = False
    data_dir = "apps/expenses/data"

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
        初始化记账窗口

        Parameters:
            parent (QWidget, optional): 父窗口
        """
        if ExpensesWindow._initialized:
            return
        super().__init__(parent)
        self.setWindowTitle("记账")
        self.setMinimumSize(800, 600)

        current_date = get_today()
        self.current_date = QDate(current_date.year, current_date.month, current_date.day)

        self.date_edit = QDateEdit(self.current_date)
        self.date_edit.setDisplayFormat("yyyy-MM")
        self.date_edit.dateChanged.connect(self.on_date_changed)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.date_edit)
        main_layout.addLayout(top_bar)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.record_widget = ExpenseRecordWidget(self)
        self.tab_widget.addTab(self.record_widget, "记账")

        self.trend_widget = TrendWidget(self)
        self.tab_widget.addTab(self.trend_widget, "余额趋势")

        os.makedirs(self.data_dir, exist_ok=True)
        self.load_month_data()
        ExpensesWindow._instance = self
        ExpensesWindow._initialized = True

    def on_date_changed(self, date):
        """
        日期改变时加载对应月份数据

        Parameters:
            date (QDate): 新选择的日期
        """
        self.current_date = date
        self.load_month_data()

    def load_month_data(self):
        """加载指定月份的记账数据"""
        year = self.current_date.year()
        month = self.current_date.month()

        data_path = self.get_data_path(year, month)
        if not os.path.exists(data_path):
            self.try_init_from_last_month(year, month)

        self.record_widget.load_month_data(year, month)
        self.trend_widget.update_view(year, month)

    @classmethod
    def get_data_path(cls, year, month):
        """
        获取指定月份数据文件的路径

        Parameters:
            year (int): 年份
            month (int): 月份

        Returns:
            str: 数据文件路径
        """
        return os.path.join(cls.data_dir, f"{year}-{month:02d}.json")

    @classmethod
    def try_init_from_last_month(cls, year, month):
        """
        尝试从上一个月初始化当前月的记账数据文件

        Parameters:
            year (int): 目标年份
            month (int): 目标月份
        """
        last_month = month - 1
        last_year = year
        if last_month == 0:
            last_month = 12
            last_year -= 1

        data_path = cls.get_data_path(year, month)
        last_path = cls.get_data_path(last_year, last_month)

        if os.path.exists(last_path):
            import shutil
            shutil.copy(last_path, data_path)
            cls.reset_actual(data_path)

    @staticmethod
    def reset_actual(data_path):
        """
        将记账数据文件中的所有实际金额重置为0

        Parameters:
            data_path (str): 数据文件路径
        """
        def reset_actual_children(data):
            for child in data.get('children', []):
                if child['type'] == 'item':
                    child['actual_amount'] = 0
                elif child['type'] == 'type':
                    reset_actual_children(child)

        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        reset_actual_children(data)

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def closeEvent(self, event):
        """窗口关闭时保存所有被修改过的数据"""
        self.record_widget.data_manager.save_all_modified()
        self.trend_widget.save_if_modified()
        super().closeEvent(event)
        ExpensesWindow._instance = None
        ExpensesWindow._initialized = False