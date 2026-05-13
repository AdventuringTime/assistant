import os
import json
from PySide6.QtWidgets import (
    QDialog, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QProgressBar, QScrollArea, QDateEdit, QMessageBox,
    QInputDialog, QSpinBox, QSizePolicy, QDoubleSpinBox, QListWidget
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtSvgWidgets import QSvgWidget

from core.base_window import BaseWindow, BaseDialog


def evaluate_estimated_amount(expression="0", constants=None):
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


class SortDialog(BaseDialog):
    def __init__(self, parent, children, title="排序"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)
        self.children = children
        
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        layout.addWidget(self.list_widget)
        
        for child in self.children:
            self.list_widget.addItem(child['name'])
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.result = None

    def accept(self):
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
        self.result = None
        super().reject()


class ConstantEditWindow(BaseWindow):
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
        while self.constants_layout.count() > 0:
            item = self.constants_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name, value in self.expenses_window.constants.items():
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            
            name_label = QLabel(name)
            name_label.setFixedWidth(30)
            row_layout.addWidget(name_label)

            value_edit = QSpinBox()
            value_edit.setValue(value)
            row_layout.addWidget(value_edit)

            delete_button = QPushButton("删除")
            delete_button.setFixedWidth(24)
            delete_button.setStyleSheet("QPushButton { background-color: #FF4D4D; color: #FFFFFF; } QPushButton:hover { background-color: #FF3333; } QPushButton:pressed { background-color: #FF2222; }")
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
        name, ok = QInputDialog.getText(self, "添加常量", "输入常量名称:")
        if ok:
            if not name:
                QMessageBox.warning(self, "请输入常量名称", "请输入常量名称")
                return
            if name in self.expenses_window.constants:
                QMessageBox.warning(self, "常量名称已存在", "常量名称已存在")
                return
            self.expenses_window.constants[name] = 0
            self.expenses_window.save_and_reload()
            self.load_constants()

    def delete_constant(self, name):
        if name in self.expenses_window.constants:
            del self.expenses_window.constants[name]
            self.expenses_window.save_and_reload()
            self.load_constants()

    def update_constant(self, name, value):
        if name in self.expenses_window.constants:
            self.expenses_window.constants[name] = value
            self.expenses_window.save_and_reload()


class ExpenseItemWidget(QWidget):
    def __init__(self, item_data, constants, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.constants = constants
        self.recording = False

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
        self.delete_button.setStyleSheet("QPushButton { background-color: #FF4D4D; color: #FFFFFF; } QPushButton:hover { background-color: #FF3333; } QPushButton:pressed { background-color: #FF2222; }")
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
        return evaluate_estimated_amount(self.item_data.get('estimated_amount', "0"), self.constants)

    def update_progress(self):
        estimated = self.get_estimated_value()
        actual = self.item_data.get('actual_amount', 0.)
        
        if estimated == "Error":
            self.estimated_label.setText("Error")
        else:
            self.estimated_label.setText(f"{estimated:.2f}")
        
        if estimated == 0 or estimated == "Error":
            self.progress_bar.setValue(0)
        else:
            progress = actual / estimated
            ratio = min(max(progress / 2, 0), 1)
            self.progress_bar.setValue(int(ratio * 200))
            r = int(255 * ratio)
            g = int(255 * (1 - ratio))
            self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: rgb({r}, {g}, 0); }}")

    def rename(self):
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=self.item_data['name'])
        if ok and new_name:
            self.item_data['name'] = new_name
            self.name_label.setText(new_name)
            self.window().save_and_reload()

    def delete(self):
        self.window().remove_item(self.item_data)

    def modify_budget(self):
        new_budget, ok = QInputDialog.getText(self, "修改预算", "输入新预算:", text=self.item_data.get('estimated_amount', "0"))
        if ok and new_budget != self.item_data.get('estimated_amount'):
            self.item_data['estimated_amount'] = new_budget
            self.update_progress()
            self.window().save_and_reload()

    def toggle_record(self):
        if not self.recording:
            self.recording = True
            self.record_input = QDoubleSpinBox()
            self.record_input.setRange(-1e18, 1e18)
            self.record_input.setDecimals(2)

            index = self.bottom_row.count() - 1
            self.bottom_row.insertWidget(index, self.record_input)
            self.record_button.setText("确认")
        else:
            amount = self.record_input.value()
            if amount != 0:
                self.item_data['actual_amount'] = self.item_data.get('actual_amount', 0) + amount
                self.actual_label.setText(f"{self.item_data['actual_amount']:.2f}")
                self.update_progress()
                self.window().save_and_reload()

            self.bottom_row.removeWidget(self.record_input)
            self.record_input.deleteLater()
            self.record_input = None
            self.recording = False
            self.record_button.setText("记账")


class ExpenseTypeWidget(QWidget):
    def __init__(self, type_data, constants, parent=None):
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
        self.progress_bar.setMaximum(200)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bottom_row.addWidget(self.progress_bar)

        self.sort_button = QPushButton("排序")
        self.sort_button.clicked.connect(self.open_sort_dialog)
        self.sort_button.setFixedSize(24, 24)
        bottom_row.addWidget(self.sort_button)

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

        self.load_children()
        self.update_totals()

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.type_data['expanded'] = self.is_expanded
        self.expand_svg.load("assets/svg/expanded.svg" if self.is_expanded else "assets/svg/collapsed.svg")
        self.children_container.setVisible(self.is_expanded)

    def rename(self):
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=self.type_data['name'])
        if ok and new_name:
            self.type_data['name'] = new_name
            self.name_label.setText(new_name)
            self.window().save_and_reload()

    def delete(self):
        self.window().remove_type(self.type_data)

    def add_item(self):
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
            self.window().save_and_reload()

    def add_subtype(self):
        name, ok = QInputDialog.getText(self, "添加子类型", "输入子类型名称:")
        if ok and name:
            if 'children' not in self.type_data:
                self.type_data['children'] = []
            self.type_data['children'].append({
                'type': 'type',
                'name': name,
                'children': []
            })
            self.window().save_and_reload()

    def open_sort_dialog(self):
        children = self.type_data.get('children', [])
        if not children:
            return
        
        dialog = SortDialog(self, children, f"排序 - {self.type_data['name']}")
        dialog.show()

        def check_result():
            if dialog.result is not None:
                self.type_data['children'] = dialog.result
                self.window().save_and_reload()

        dialog.destroyed.connect(check_result)

    def load_children(self):
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


class ExpensesWindow(BaseWindow):
    data_dir = "apps/expenses/data"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("记账")
        self.setMinimumSize(800, 600)

        self.current_date = QDate.currentDate()
        self.constants = {}
        self.children_ = []

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

        self.sort_button = QPushButton("排序")
        self.sort_button.clicked.connect(self.open_sort_dialog)
        self.sort_button.setFixedSize(24, 24)
        total_bottom_row.addWidget(self.sort_button)

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
        year = self.current_date.year()
        month = self.current_date.month()

        data_path = self.get_data_path(year, month)

        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.constants = data['constants']
                self.children_ = data['children']
        else:
            self.constants = {}
            self.children_ = []

        self.render_ui()

    def render_ui(self):
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

    @classmethod
    def get_data_path(cls, year, month):
        return os.path.join(cls.data_dir, f"{year}-{month:02d}.json")

    def save_month_data(self):
        year = self.current_date.year()
        month = self.current_date.month()
        data_path = self.get_data_path(year, month)

        def remove_expanded_field(children):
            for child in children:
                if 'expanded' in child:
                    del child['expanded']
                if child.get('children'):
                    remove_expanded_field(child['children'])

        remove_expanded_field(self.children_)

        data = {
            'constants': self.constants,
            'children': self.children_
        }
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def save_and_reload(self):
        self.save_month_data()
        self.render_ui()

    def add_root_item(self):
        name, ok = QInputDialog.getText(self, "添加记账项", "输入记账项名称:")
        if ok and name:
            self.children_.append({
                'type': 'item',
                'name': name,
                'estimated_amount': "0",
                'actual_amount': 0
            })
            self.save_and_reload()

    def add_root_type(self):
        name, ok = QInputDialog.getText(self, "添加记账类型", "输入记账类型名称:")
        if ok and name:
            self.children_.append({
                'type': 'type',
                'name': name,
                'children': []
            })
            self.save_and_reload()

    def open_sort_dialog(self):
        if not self.children_:
            return
        
        dialog = SortDialog(self, self.children_, "排序")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.children_ = dialog.result
            self.save_and_reload()

    def remove_item(self, item_data):
        self._remove_from_children(self.children_, item_data)
        self.save_and_reload()

    def remove_type(self, type_data):
        self._remove_from_children(self.children_, type_data)
        self.save_and_reload()

    def _remove_from_children(self, children_list, target_data):
        for i, child in enumerate(children_list):
            if child is target_data:
                del children_list[i]
                return True
            if child.get('children'):
                if self._remove_from_children(child['children'], target_data):
                    return True
        return False

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

    def get_total_estimated(self, children_list=None):
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
        self.constants_window = ConstantEditWindow(self)
        self.constants_window.show()