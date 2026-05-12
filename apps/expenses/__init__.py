import os
import json
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QProgressBar, QScrollArea, QDateEdit, QMessageBox,
    QInputDialog, QSpinBox, QSizePolicy, QDoubleSpinBox
)
from PySide6.QtCore import QDate, Signal
from PySide6.QtSvgWidgets import QSvgWidget

from core.base_window import BaseWindow

class ConstantRowWidget(QWidget):
    def __init__(self, name, value, parent=None):
        super().__init__(parent)
        self.name = name

        self.row_layout = QHBoxLayout(self)

        self.name_label = QLabel(self.name)
        self.name_label.setFixedWidth(30)
        self.row_layout.addWidget(self.name_label)

        self.value_edit = QSpinBox()
        self.value_edit.setValue(value)
        self.row_layout.addWidget(self.value_edit)

        self.delete_button = QPushButton("删除")
        self.delete_button.setFixedWidth(24)
        self.row_layout.addWidget(self.delete_button)

    def get_value(self):
        return self.value_edit.value()


class ConstantEditWindow(BaseWindow):
    constants_updated = Signal()
    def __init__(self, parent):
        super().__init__(parent)
        self.expenses_window = parent.window()
        assert isinstance(self.expenses_window, ExpensesWindow)

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
        # 清空当前布局
        while self.constants_layout.count() > 0:
            item = self.constants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.row_widgets = []

        # 添加常量行
        for name, value in self.expenses_window.constants.items():
            row_widget = ConstantRowWidget(name, value)
            self.row_widgets.append(row_widget)
            # 预存 name，防止全部连接到最后一项
            row_widget.value_edit.valueChanged.connect(
                lambda value, name=name: self.update_constant(name, value))
            # 增加一个 checked，因为按钮点击事件会多传一个参数
            row_widget.delete_button.clicked.connect(
                lambda checked=False, name=name: self.delete_constant(name))
            self.constants_layout.addWidget(row_widget)

        self.constants_layout.addStretch()

    def add_constant(self):
        name, ok = QInputDialog.getText(self, "添加常量", "输入常量名称:")
        if ok:
            if not name:
                QMessageBox.warning(self, "请输入常量名称", "请输入常量名称")
                return
            if name in self.expenses_window.constants:
                QMessageBox.warning(self, "常量名称已存在", "常量名称已存在")
                return
            self.expenses_window.constants[name] = 0
            self.constants_updated.emit()
            self.load_constants()

    def delete_constant(self, name):
        if name in self.expenses_window.constants:
            del self.expenses_window.constants[name]
            self.constants_updated.emit()
            self.load_constants()

    def update_constant(self, name, value):
        if name in self.expenses_window.constants:
            self.expenses_window.constants[name] = value
            self.constants_updated.emit()


class EstimatedAmount:
    def __init__(self, expression="0", parent=None):
        self.expression = expression
        self.parent = parent

    def get_constants(self):
        if self.parent:
            window = self.parent.window()
            assert isinstance(window, ExpensesWindow)
            return window.constants
        return {}

    def evaluate(self):
        expr = self.expression
        for name, value in self.get_constants().items():
            expr = expr.replace(name, str(value))
        if expr.strip() == "":
            return 0.
        try:
            return float(eval(expr))
        except:
            return "Error"


class ExpenseItemWidget(QWidget):
    removed = Signal(object)
    renamed = Signal(object)
    value_updated = Signal(object)

    def __init__(self, name, parent, estimated_amount="0", actual_amount=0.):
        super().__init__(parent)
        self.name = name
        self.estimated_amount_object = EstimatedAmount(estimated_amount, parent=self)
        self.actual_amount = actual_amount
        self.recording = False
        self.record_input = None

        self.main_layout = QVBoxLayout(self)

        top_row = QHBoxLayout()

        self.name_label = QLabel(self.name)
        top_row.addWidget(self.name_label)

        top_row.addStretch()

        estimated_value = self.get_estimated_value()
        self.estimated_label = QLabel("Error" if estimated_value == "Error" else f"{estimated_value:.2f}")
        top_row.addWidget(self.estimated_label)

        self.actual_label = QLabel(f"{self.actual_amount:.2f}")
        top_row.addWidget(self.actual_label)

        self.main_layout.addLayout(top_row)

        self.bottom_row = QHBoxLayout()

        self.progress_bar = QProgressBar(minimum=0, maximum=200)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.bottom_row.addWidget(self.progress_bar)

        self.rename_button = QPushButton("重命名")
        self.rename_button.clicked.connect(self.rename)
        self.rename_button.setFixedSize(24, 24)
        self.bottom_row.addWidget(self.rename_button)

        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete)
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setStyleSheet("QPushButton { background-color: #FF4D4F; color: #FFFFFF; }")
        self.bottom_row.addWidget(self.delete_button)

        self.modify_budget_button = QPushButton("修改预算")
        self.modify_budget_button.clicked.connect(self.modify_budget)
        self.modify_budget_button.setFixedSize(24, 24)
        self.bottom_row.addWidget(self.modify_budget_button)

        self.record_button = QPushButton("记账")
        self.record_button.clicked.connect(self.toggle_record)
        self.record_button.setFixedSize(24, 24)
        self.bottom_row.addWidget(self.record_button)

        self.main_layout.addLayout(self.bottom_row)

        self.update_progress()

    def get_estimated_value(self):
        return self.estimated_amount_object.evaluate()

    def update_progress(self):
        estimated = self.get_estimated_value()
        
        if estimated == "Error":
            self.estimated_label.setText("Error")
        else:
            self.estimated_label.setText(f"{estimated:.2f}")
        
        if estimated == 0 or estimated == "Error":
            self.progress_bar.setValue(0)
        else:
            progress = self.actual_amount / estimated
            ratio = min(max(progress / 2, 0), 1)
            self.progress_bar.setValue(int(ratio * 200))
            r = int(255 * ratio)
            g = int(255 * (1 - ratio))
            self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r}, {g}, 0); }}")

    def rename(self):
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=self.name)
        if ok and new_name:
            self.name = new_name
            self.name_label.setText(new_name)
            self.renamed.emit(self)

    def delete(self):
        self.removed.emit(self)

    def modify_budget(self):
        new_budget, ok = QInputDialog.getText(self, "修改预算", "输入新预算:", text=self.estimated_amount_object.expression)
        if ok and new_budget != self.estimated_amount_object.expression:
            self.estimated_amount_object = EstimatedAmount(new_budget, parent=self)
            estimated = self.get_estimated_value()
            self.estimated_label.setText("Error" if estimated == "Error" else f"{estimated:.2f}")
            self.update_progress()
            self.value_updated.emit(self)

    def toggle_record(self):
        if not self.recording:
            self.recording = True
            self.record_input = QDoubleSpinBox()
            self.record_input.setRange(-1e18, 1e18)
            self.record_input.setDecimals(2)
            self.record_input.setPrefix("¥ ")
            self.record_input.setSingleStep(1.0)

            index = self.bottom_row.count() - 1
            self.bottom_row.insertWidget(index, self.record_input)
            self.record_button.setText("确认")
        else:
            amount = self.record_input.value()
            if amount != 0:
                self.actual_amount += amount
                self.actual_label.setText(f"{self.actual_amount:.2f}")
                self.update_progress()
                self.value_updated.emit(self)

            self.bottom_row.removeWidget(self.record_input)
            self.record_input.deleteLater()
            self.record_input = None
            self.recording = False
            self.record_button.setText("记账")


class ExpenseTypeWidget(QWidget):
    removed = Signal(object)
    renamed = Signal(object)
    child_removed = Signal(object)
    child_renamed = Signal(object)
    child_value_updated = Signal(object)
    child_added = Signal(object)

    def __init__(self, name, parent):
        super().__init__(parent)
        self.name = name
        self.children_ = []
        self.is_expanded = True

        self.main_layout = QVBoxLayout(self)

        self.header = QWidget()
        header_layout = QVBoxLayout(self.header)

        top_row = QHBoxLayout()

        self.expand_svg = QSvgWidget("assets/svg/expanded.svg")
        self.expand_svg.setFixedSize(24, 24)
        top_row.addWidget(self.expand_svg)

        self.name_label = QLabel(self.name)
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
        self.progress_bar.setMaximum(200)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bottom_row.addWidget(self.progress_bar)

        self.rename_button = QPushButton("重命名")
        self.rename_button.clicked.connect(self.rename)
        self.rename_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.rename_button)

        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete)
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setStyleSheet("QPushButton { background-color: #FF4D4F; color: #FFFFFF; }")
        bottom_row.addWidget(self.delete_button)

        self.add_item_button = QPushButton("添加记账项")
        self.add_item_button.clicked.connect(self.add_item)
        self.add_item_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.add_item_button)

        self.add_type_button = QPushButton("添加子类型")
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

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.expand_svg.load("assets/svg/expanded.svg" if self.is_expanded else "assets/svg/collapsed.svg")
        self.children_container.setVisible(self.is_expanded)

    def rename(self):
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=self.name)
        if ok and new_name:
            self.name = new_name
            self.name_label.setText(new_name)
            self.renamed.emit(self)

    def delete(self):
        self.removed.emit(self)

    def add_item(self):
        name, ok = QInputDialog.getText(self, "添加记账项", "输入记账项名称:")
        if ok and name:
            item = ExpenseItemWidget(name, self)
            item.removed.connect(self.remove_item)
            item.renamed.connect(lambda i: self.child_renamed.emit(i))
            item.value_updated.connect(self.on_child_value_updated)
            self.children_.append(item)
            self.children_layout.addWidget(item)
            self.update_totals()
            self.child_added.emit(item)

    def add_subtype(self):
        name, ok = QInputDialog.getText(self, "添加子类型", "输入子类型名称:")
        if ok and name:
            subtype = ExpenseTypeWidget(name, self)
            subtype.removed.connect(self.remove_child)
            subtype.renamed.connect(lambda s: self.child_renamed.emit(s))
            subtype.child_removed.connect(self.on_child_removed)
            subtype.child_renamed.connect(lambda s: self.child_renamed.emit(s))
            subtype.child_value_updated.connect(self.on_child_value_updated)
            subtype.child_added.connect(lambda s: self.child_added.emit(s))
            self.children_.append(subtype)
            self.children_layout.addWidget(subtype)
            self.update_totals()
            self.child_added.emit(subtype)

    def remove_item(self, item):
        if item in self.children_:
            self.children_layout.removeWidget(item)
            item.deleteLater()
            self.children_.remove(item)
            self.update_totals()
            self.child_removed.emit(item)

    def remove_child(self, child):
        if child in self.children_:
            self.children_layout.removeWidget(child)
            child.deleteLater()
            self.children_.remove(child)
            self.update_totals()
            self.child_removed.emit(child)

    def on_child_removed(self, child):
        self.update_totals()
        self.child_removed.emit(child)

    def on_child_value_updated(self, child):
        self.update_totals()
        self.child_value_updated.emit(child)

    def get_total_estimated(self):
        total = 0.
        for child in self.children_:
            if isinstance(child, ExpenseItemWidget):
                val = child.get_estimated_value()
                if val == "Error":
                    return "Error"
                total += val
            elif isinstance(child, ExpenseTypeWidget):
                val = child.get_total_estimated()
                if val == "Error":
                    return "Error"
                total += val
        return total

    def get_total_actual(self):
        total = 0.
        for child in self.children_:
            if isinstance(child, ExpenseItemWidget):
                total += child.actual_amount
            elif isinstance(child, ExpenseTypeWidget):
                total += child.get_total_actual()
        return total

    def update_totals(self):
        estimated = self.get_total_estimated()
        actual = self.get_total_actual()

        self.total_estimated_label.setText("Error" if estimated == "Error" else f"{estimated:.2f}")
        self.total_actual_label.setText(f"{actual:.2f}")

        if estimated == 0 or estimated == "Error":
            self.progress_bar.setValue(0)
        else:
            progress = actual / estimated
            ratio = min(max(progress / 2, 0), 1)

            self.progress_bar.setValue(int(ratio * 200))

            r = int(255 * ratio)
            g = int(255 * (1 - ratio))
            self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r}, {g}, 0); }}")

    def load_type_children(self, children_data):
        for child_data in children_data:
            if child_data['type'] == 'item':
                item = ExpenseItemWidget(
                    child_data['name'],
                    self,
                    child_data['estimated_amount'],
                    child_data.get('actual_amount', 0)
                )
                item.removed.connect(self.remove_item)
                item.renamed.connect(lambda i: self.child_renamed.emit(i))
                item.value_updated.connect(self.on_child_value_updated)
                self.children_.append(item)
                self.children_layout.addWidget(item)
            elif child_data['type'] == 'type':
                subtype = ExpenseTypeWidget(child_data['name'], self)
                subtype.removed.connect(self.remove_child)
                subtype.renamed.connect(lambda s: self.child_renamed.emit(s))
                subtype.child_removed.connect(self.on_child_removed)
                subtype.child_renamed.connect(lambda s: self.child_renamed.emit(s))
                subtype.child_value_updated.connect(self.on_child_value_updated)
                if 'children' in child_data:
                    subtype.load_type_children(child_data['children'])
                self.children_.append(subtype)
                self.children_layout.addWidget(subtype)

    def get_type_data(self):
        children_data = []
        for child in self.children_:
            if isinstance(child, ExpenseItemWidget):
                children_data.append({
                    'type': 'item',
                    'name': child.name,
                    'estimated_amount': child.estimated_amount_object.expression,
                    'actual_amount': child.actual_amount
                })
            elif isinstance(child, ExpenseTypeWidget):
                children_data.append(child.get_type_data())
        return {
            'type': 'type',
            'name': self.name,
            'children': children_data
        }


class ExpensesWindow(BaseWindow):
    data_dir = "apps/expenses/data"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("记账")
        self.setMinimumSize(800, 600)

        self.current_date = QDate.currentDate()
        self.constants = {}
        self.root_children = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_bar = QHBoxLayout()

        self.date_edit = QDateEdit(self.current_date)
        self.date_edit.setDisplayFormat("yyyy-MM")
        self.date_edit.dateChanged.connect(self.on_date_changed)
        top_bar.addWidget(self.date_edit)

        main_layout.addLayout(top_bar)

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
        self.total_progress_bar.setMaximum(200)
        self.total_progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        total_bottom_row.addWidget(self.total_progress_bar)

        self.modify_constants_button = QPushButton("修改常量")
        self.modify_constants_button.clicked.connect(self.open_constants_window)
        self.modify_constants_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.modify_constants_button)

        self.add_item_button = QPushButton("添加记账项")
        self.add_item_button.clicked.connect(self.add_root_item)
        self.add_item_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.add_item_button)

        self.add_type_button = QPushButton("添加记账类型")
        self.add_type_button.clicked.connect(self.add_root_type)
        self.add_type_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.add_type_button)

        total_layout.addLayout(total_bottom_row)
        main_layout.addWidget(self.total_widget)

        os.makedirs(self.data_dir, exist_ok=True)

        data_path = self.get_data_path(self.current_date.year(), self.current_date.month())
        if not os.path.exists(data_path):
            self.try_init_from_last_month(self.current_date.year(), self.current_date.month())

        self.load_month_data()

    def on_date_changed(self, date):
        self.current_date = date
        self.load_month_data()

    def load_month_data(self):
        self.clear_root_items()

        year = self.current_date.year()
        month = self.current_date.month()

        data_path = self.get_data_path(year, month)

        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.constants = data['constants']

            self.load_types_from_data(data['children'])
        else:
            self.constants = {}

        self.update_total_display()

    @classmethod
    def try_init_from_last_month(cls, year, month):
        """尝试从上一个月初始化当前月的记账数据文件，然后仍然需要重新加载"""
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
        """将一个记账数据文件的实际金额全部设为0"""
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

    def load_types_from_data(self, types_data):
        for child_data in types_data:
            if child_data.get('type') == 'item' or 'children' not in child_data:
                item = ExpenseItemWidget(
                    child_data['name'],
                    self,
                    child_data.get('estimated_amount', "0"),
                    child_data.get('actual_amount', 0)
                )
                item.removed.connect(self.remove_root_item)
                item.renamed.connect(self.update_and_save)
                item.value_updated.connect(self.update_and_save)
                self.root_children.append(item)
                self.scroll_layout.addWidget(item)
            else:
                exp_type = ExpenseTypeWidget(child_data['name'], self)
                exp_type.removed.connect(self.remove_root_type)
                exp_type.renamed.connect(self.update_and_save)
                exp_type.child_removed.connect(self.update_and_save)
                exp_type.child_renamed.connect(self.update_and_save)
                exp_type.child_value_updated.connect(self.update_and_save)
                exp_type.child_added.connect(self.update_and_save)
                if 'children' in child_data:
                    exp_type.load_type_children(child_data['children'])
                self.root_children.append(exp_type)
                self.scroll_layout.addWidget(exp_type)
        self.scroll_layout.addStretch()

    @classmethod
    def get_data_path(cls, year, month):
        return os.path.join(cls.data_dir, f"{year}-{month:02d}.json")

    def save_month_data(self):
        year = self.current_date.year()
        month = self.current_date.month()
        data_path = self.get_data_path(year, month)

        data = {
            'constants': self.constants,
            'children': self.get_children_data()
        }

        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get_children_data(self):
        children_data = []
        for item in self.root_children:
            if isinstance(item, ExpenseItemWidget):
                children_data.append({
                    'type': 'item',
                    'name': item.name,
                    'estimated_amount': item.estimated_amount_object.expression,
                    'actual_amount': item.actual_amount
                })
            elif isinstance(item, ExpenseTypeWidget):
                children_data.append(item.get_type_data())
        return children_data

    def clear_root_items(self):
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                self.scroll_layout.removeItem(item)
        self.root_children = []

    def add_root_item(self):
        name, ok = QInputDialog.getText(self, "添加记账项", "输入记账项名称:")
        if ok and name:
            item = ExpenseItemWidget(name, self, "0")
            item.removed.connect(self.remove_root_item)
            item.value_updated.connect(self.update_and_save)
            self.root_children.append(item)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, item)
            self.update_and_save()

    def add_root_type(self):
        name, ok = QInputDialog.getText(self, "添加记账类型", "输入记账类型名称:")
        if ok and name:
            exp_type = ExpenseTypeWidget(name, self)
            exp_type.removed.connect(self.remove_root_type)
            exp_type.renamed.connect(self.update_and_save)
            exp_type.child_removed.connect(self.update_and_save)
            exp_type.child_renamed.connect(self.update_and_save)
            exp_type.child_value_updated.connect(self.update_and_save)
            exp_type.child_added.connect(self.update_and_save)
            self.root_children.append(exp_type)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, exp_type)
            self.update_and_save()

    def remove_root_item(self, item):
        if item in self.root_children:
            self.root_children.remove(item)
            self.scroll_layout.removeWidget(item)
            item.deleteLater()
            self.update_and_save()

    def remove_root_type(self, exp_type):
        if exp_type in self.root_children:
            self.root_children.remove(exp_type)
            self.scroll_layout.removeWidget(exp_type)
            exp_type.deleteLater()
            self.update_and_save()

    def update_total_display(self):
        estimated = self.get_total_estimated()
        actual = self.get_total_actual()

        self.total_estimated_label.setText("Error" if estimated == "Error" else f"{estimated:.2f}")
        self.total_actual_label.setText(f"{actual:.2f}")

        if estimated == 0 or estimated == "Error":
            self.total_progress_bar.setValue(0)
        else:
            progress = actual / estimated
            ratio = min(max(progress / 2, 0), 1)

            self.total_progress_bar.setValue(int(ratio * 200))

            r = int(255 * ratio)
            g = int(255 * (1 - ratio))
            self.total_progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r}, {g}, 0); }}")

    def update_and_save(self):
        self.update_total_display()
        self.save_month_data()

    def get_total_estimated(self):
        total = 0.
        for item in self.root_children:
            if isinstance(item, ExpenseItemWidget):
                val = item.get_estimated_value()
                if val == "Error":
                    return "Error"
                total += val
            elif isinstance(item, ExpenseTypeWidget):
                val = item.get_total_estimated()
                if val == "Error":
                    return "Error"
                total += val
        return total

    def get_total_actual(self):
        total = 0.
        for item in self.root_children:
            if isinstance(item, ExpenseItemWidget):
                total += item.actual_amount
            elif isinstance(item, ExpenseTypeWidget):
                total += item.get_total_actual()
        return total

    def open_constants_window(self):
        self.constants_window = ConstantEditWindow(self)
        self.constants_window.constants_updated.connect(self.on_constants_updated)
        self.constants_window.show()

    def on_constants_updated(self):
        self.update_total_display()
        self.save_month_data()