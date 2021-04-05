from typing import Optional

from binaryninjaui import qt_major_version

if qt_major_version > 5:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QContextMenuEvent, QBrush, QPalette
    from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QHBoxLayout, QHeaderView, QAbstractItemView
else:
    from PySide2.QtCore import Qt
    from PySide2.QtGui import QContextMenuEvent, QBrush, QPalette
    from PySide2.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QHBoxLayout, QHeaderView, QAbstractItemView

from binaryninja import BinaryView, Function, VariableSourceType, ThemeColor, LLIL_REG_IS_TEMP, MediumLevelILFunction, \
    FunctionGraphType, LowLevelILFunction, HighLevelILFunction, Variable
from binaryninjaui import DockContextHandler, UIActionHandler, UIContextNotification, UIContext, ViewLocation, View, \
    ViewFrame, getThemeColor


class FunctionVarsWidget(QWidget, DockContextHandler, UIContextNotification):
    name = "Function Variables"

    def __init__(self, parent, name, data):
        if not type(data) == BinaryView:
            raise Exception("Expected BinaryView")

        self.data: BinaryView = data

        QWidget.__init__(self, parent)
        DockContextHandler.__init__(self, self, name)
        UIContextNotification.__init__(self)
        self.actionHandler = UIActionHandler()
        self.actionHandler.setupActionHandler(self)

        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.table.setColumnCount(3)

        self.address = 0
        self.function: Optional[Function] = None

        UIContext.registerNotification(self)

    def __del__(self):
        UIContext.unregisterNotification(self)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.m_contextMenuManager.show(self.m_menu, self.actionHandler)

    def shouldBeVisible(self, view_frame):
        return view_frame is not None

    def OnAddressChange(self, context: UIContext, frame: Optional[ViewFrame], view: View, location: ViewLocation):
        if location.isValid():
            self.update_address(location)

    def update_address(self, location: ViewLocation):
        self.function: Function = location.getFunction()
        self.address = location.getOffset()
        instr_index = location.getInstrIndex()
        view_type = location.getViewType()
        il_view_type = location.getILViewType()

        self.table.clear()
        if self.function is None:
            self.table.setRowCount(1)
            self.table.setColumnCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No Function Selected"))
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        else:
            self.table.setColumnCount(4)
            self.table.setHorizontalHeaderLabels(["Type", "Variable", "Storage", f"Value at 0x{self.address:x}"])

            # Gotta set these after setColumnCount()
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

            vars = self.function.vars
            self.table.setRowCount(len(vars))

            llil: LowLevelILFunction = self.function.llil
            mlil: MediumLevelILFunction = self.function.mlil
            hlil: HighLevelILFunction = self.function.hlil
            llil_instr = None
            mlil_instr = None
            hlil_instr = None

            if view_type == FunctionGraphType.LowLevelILFunctionGraph:
                llil_instr = llil[instr_index]
            if view_type == FunctionGraphType.MediumLevelILFunctionGraph:
                mlil_instr = mlil[instr_index]
                llil_instr = mlil_instr.llil
            if view_type == FunctionGraphType.HighLevelILFunctionGraph:
                hlil_instr = hlil[instr_index]
                mlil_instr = hlil_instr.mlil
                llil_instr = mlil_instr.llil

            if llil_instr is None and llil.get_instruction_start(self.address) is not None:
                llil_instr = llil[llil.get_instruction_start(self.address)]
            if mlil_instr is None and mlil.get_instruction_start(self.address) is not None:
                mlil_instr = mlil[mlil.get_instruction_start(self.address)]

            # Var accessors
            get_reg_value_at = lambda reg: self.function.get_reg_value_at(self.address, reg)
            get_reg_value_after = lambda reg: self.function.get_reg_value_after(self.address, reg)
            get_stack_value_at = lambda offset, size: self.function.get_stack_contents_at(self.address, offset, size)
            get_stack_value_after = lambda offset, size: self.function.get_stack_contents_after(self.address, offset, size)
            get_flag_value_at = lambda flag: "<undetermined>"
            get_flag_value_after = lambda flag: "<undetermined>"

            if llil_instr is not None:
                get_reg_value_at = lambda reg: llil_instr.get_possible_reg_values(reg)
                get_reg_value_after = lambda reg: llil_instr.get_possible_reg_values_after(reg)
                get_stack_value_at = lambda offset, size: llil_instr.get_possible_stack_contents(offset, size)
                get_stack_value_after = lambda offset, size: llil_instr.get_possible_stack_contents_after(offset, size)
                get_flag_value_at = lambda flag: llil_instr.get_possible_flag_values(flag)
                get_flag_value_after = lambda flag: llil_instr.get_possible_flag_values_after(flag)

            if mlil_instr is not None:
                get_reg_value_at = lambda reg: mlil_instr.get_possible_reg_values(reg)
                get_reg_value_after = lambda reg: mlil_instr.get_possible_reg_values_after(reg)
                get_stack_value_at = lambda offset, size: mlil_instr.get_possible_stack_contents(offset, size)
                get_stack_value_after = lambda offset, size: mlil_instr.get_possible_stack_contents_after(offset, size)
                get_flag_value_at = lambda flag: mlil_instr.get_possible_flag_values(flag)
                get_flag_value_after = lambda flag: mlil_instr.get_possible_flag_values_after(flag)

            for i, var in enumerate(vars):
                storage_str = ""
                conts_str = "Undetermined"
                referenced = False
                active = True
                # Read contents of variable
                if var.source_type == VariableSourceType.StackVariableSourceType:
                    storage_str = f"Stack[{var.storage:x}]"
                    conts_str = str(get_stack_value_after(var.storage, var.type.width))
                    # String compare because apparently two <undetermined>s are not always equal
                    referenced = str(get_stack_value_at(var.storage, var.type.width)) != conts_str
                    active = self.function.get_stack_var_at_frame_offset(var.storage, self.address) == var
                elif var.source_type == VariableSourceType.RegisterVariableSourceType:
                    reg = self.function.arch.get_reg_name(var.storage)
                    storage_str = f"Register[{reg}]"
                    # Classy
                    if not LLIL_REG_IS_TEMP(var.storage):
                        conts_str = str(get_reg_value_after(reg))
                        referenced = str(get_reg_value_at(reg)) != conts_str
                elif var.source_type == VariableSourceType.FlagVariableSourceType:
                    storage_str = f"Flag[{var.storage:x}]"
                    conts_str = str(get_flag_value_after(var.storage))
                    referenced = str(get_flag_value_at(var.storage)) != conts_str

                # Build row
                type_item = QTableWidgetItem(str(var.type))
                name_item = QTableWidgetItem(var.name)
                storage_item = QTableWidgetItem(storage_str)
                conts_item = QTableWidgetItem(conts_str)

                # Highlight referenced/changed rows
                if referenced:
                    type_item.setBackground(getThemeColor(ThemeColor.BackgroundHighlightLightColor))
                    name_item.setBackground(getThemeColor(ThemeColor.BackgroundHighlightLightColor))
                    storage_item.setBackground(getThemeColor(ThemeColor.BackgroundHighlightLightColor))
                    conts_item.setBackground(getThemeColor(ThemeColor.BackgroundHighlightLightColor))

                # Dim inactive vars
                if not active:
                    type_item.setForeground(getThemeColor(ThemeColor.UncertainColor))
                    name_item.setForeground(getThemeColor(ThemeColor.UncertainColor))
                    storage_item.setForeground(getThemeColor(ThemeColor.UncertainColor))
                    conts_item.setForeground(getThemeColor(ThemeColor.UncertainColor))

                self.table.setItem(i, 0, type_item)
                self.table.setItem(i, 1, name_item)
                self.table.setItem(i, 2, storage_item)
                self.table.setItem(i, 3, conts_item)

