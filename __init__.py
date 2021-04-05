from binaryninja import core_ui_enabled

if core_ui_enabled():
    from . import ui
    ui.init_ui()
