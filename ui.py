from binaryninjaui import qt_major_version
if qt_major_version > 5:
    from PySide6.QtCore import Qt
else:
    from PySide2.QtCore import Qt
from .FunctionVarsWidget import FunctionVarsWidget
from . import widget


def init_ui():
    widget.register_dockwidget(FunctionVarsWidget, FunctionVarsWidget.name, Qt.RightDockWidgetArea, Qt.Vertical)
