from binaryninjaui import qt_major_version
if qt_major_version > 5:
	from PySide6.QtCore import Qt
	from PySide6.QtWidgets import QWidget
else:
	from PySide2.QtCore import Qt
	from PySide2.QtWidgets import QWidget
from binaryninjaui import DockHandler
import sys
import traceback

dockwidgets = []


def _create_widget(widget_class, name, parent, data, *args):
	# It is imperative this function return *some* value because Shiboken will try to deref what we return
	# If we return nothing (or throw) there will be a null pointer deref (and we won't even get to see why)
	# So in the event of an error or a nothing, return an empty widget that at least stops the crash
	try:
		widget = widget_class(parent, name, data, *args)

		if not widget:
			raise Exception('expected widget, got None')

		global dockwidgets

		found = False
		for (bv, widgets) in dockwidgets:
			if bv == data:
				widgets[name] = widget
				found = True

		if not found:
			dockwidgets.append((data, {
				name: widget
			}))

		widget.destroyed.connect(lambda destroyed: destroy_widget(destroyed, widget, data, name))

		return widget
	except Exception as e:
		traceback.print_exc(file=sys.stderr)
		return QWidget(parent)


def destroy_widget(destroyed, old, data, name):
	# Gotta be careful to delete the correct widget here
	for (bv, widgets) in dockwidgets:
		if bv == data:
			for (name, widget) in widgets.items():
				if widget == old:
					# If there are no other references to it, this will be the only one and the call
					# will delete it and invoke __del__.
					widgets.pop(name)
					return


def register_dockwidget(widget_class, name, area=Qt.BottomDockWidgetArea, orientation=Qt.Horizontal, default_visibility=True, *args):
	dock_handler = DockHandler.getActiveDockHandler()
	dock_handler.addDockWidget(name, lambda n, p, d: _create_widget(widget_class, n, p, d, *args), area, orientation, default_visibility)


def get_dockwidget(data, name):
	for (bv, widgets) in dockwidgets:
		if bv == data:
			return widgets.get(name)

	return None

