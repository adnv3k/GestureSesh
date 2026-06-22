# main.py - GestureSesh main application module

import sys
from pathlib import Path

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QMainWindow,
    QPushButton,
    QShortcut,
)

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from gesturesesh.app.presets import MainAppPresetsMixin
from gesturesesh.app.selection import MainAppSelectionMixin
from gesturesesh.app.session import MainAppSessionMixin
from gesturesesh.app.status import MainAppStatusMixin
from gesturesesh.session.constants import SUPPORTED_IMAGE_TYPES
from gesturesesh.ui.main_window import Ui_MainWindow
from gesturesesh.utils import resources_config  # noqa: F401
from gesturesesh.utils.config import load_config
from gesturesesh.utils.update_checker import UpdateChecker


__version__ = "0.5.6"


class MainApp(
    MainAppSelectionMixin,
    MainAppStatusMixin,
    MainAppPresetsMixin,
    MainAppSessionMixin,
    QMainWindow,
    Ui_MainWindow,
):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Reference Practice")
        self.config = load_config(self)
        self.session_schedule = []
        self.has_break = False
        self.valid_file_types = set(SUPPORTED_IMAGE_TYPES)
        self.selection = {"files": [], "folders": []}

        self.status_timer = QtCore.QTimer()
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.display_status)

        self.status_messages = []
        self.current_animation_group = None
        self.showing_default_status = True

        self.status_update_timer = QtCore.QTimer()
        self.status_update_timer.setSingleShot(True)
        self.status_update_timer.timeout.connect(self._update_status_display_text)

        self.status_opacity_effect = QGraphicsOpacityEffect()
        self.selected_items.setGraphicsEffect(self.status_opacity_effect)

        self.init_selection_order_controls()
        self.init_buttons()
        self.init_shortcuts()
        self.init_preset()
        self.load_recent()
        self.check_version()
        self.entry_table.itemChanged.connect(self.update_total)
        self.dialog_buttons.accepted.connect(self.start_session)
        self.update_dynamic_fonts()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_dynamic_fonts()

    def update_dynamic_fonts(self):
        """Dynamically update font sizes based on window height."""
        base_height = self.height()
        # Calculate font size as a percentage of window height (tweak as needed)
        font_size = max(10, int(base_height * 0.0230))  # Minimum 10pt
        # font_size = max(10, int(base_height * 0.0225))  # Minimum 10pt
        large_font_size = max(14, int(base_height * 0.0325))
        # Main font
        font = QtGui.QFont("Apple SD Gothic Neo", font_size, QtGui.QFont.Bold)
        # Large font for headers
        large_font = QtGui.QFont(
            "Apple SD Gothic Neo", large_font_size, QtGui.QFont.Bold
        )
        # Apply to key widgets
        self.select_images.setFont(large_font)
        self.session_settings.setFont(large_font)
        self.label_7.setFont(font)
        self.label_5.setFont(font)
        self.label_6.setFont(font)
        self.image_amount_label.setFont(font)
        self.duration_label.setFont(font)
        self.label_8.setFont(font)
        self.add_folder.setFont(font)
        self.add_items.setFont(font)
        self.clear_items.setFont(font)
        self.randomize_selection.setFont(font)
        self.remove_duplicates.setFont(font)
        self.add_entry.setFont(font)
        self.preset_loader_box.setFont(font)
        self.save_preset.setFont(font)
        self.delete_preset.setFont(font)
        self.entry_table.setFont(font)
        self.total_table.setFont(font)
        self.remove_entry.setFont(font)
        self.move_entry_up.setFont(font)
        self.move_entry_down.setFont(font)
        self.reset_table.setFont(font)
        self.dialog_buttons.setFont(font)
        self.selected_items.setFont(font)
        self.set_number_of_images.setFont(font)
        self.set_minutes.setFont(font)
        self.set_seconds.setFont(font)
        if hasattr(self, "manage_order"):
            self.manage_order.setFont(font)

    def init_selection_order_controls(self):
        parent = getattr(self, "centralwidget", self)
        self.manage_order = QPushButton("Manage Order", parent)
        self.manage_order.setFocusPolicy(QtCore.Qt.NoFocus)
        self.manage_order.setStyleSheet("background: rgb(119, 153, 146); color: white;")
        self.manage_order.setToolTip("View and reorder selected images.\nShortcut: Ctrl+Shift+I")
        try:
            self.horizontalLayout_5.addWidget(self.manage_order)
        except Exception:
            try:
                self.verticalLayout_4.addWidget(self.manage_order)
            except Exception:
                pass

    def init_buttons(self):
        # Buttons for selection
        self.add_folder.clicked.connect(self.open_folder)
        self.clear_items.clicked.connect(self.remove_items)
        self.randomize_selection.clicked.connect(self.display_random_status)
        self.remove_duplicates.clicked.connect(self.remove_dupes)
        self.manage_order.clicked.connect(self.open_selection_order_viewer)
        # Buttons for preset
        self.add_entry.clicked.connect(self.append_schedule)
        self.save_preset.clicked.connect(self.save)
        self.delete_preset.clicked.connect(self.delete)
        self.preset_loader_box.currentIndexChanged.connect(self.load)
        self.preset_loader_box.currentTextChanged.connect(self.load)
        # Buttons for table
        self.remove_entry.pressed.connect(self.remove_row)
        self.move_entry_up.clicked.connect(self.move_up)
        self.move_entry_down.clicked.connect(self.move_down)
        self.reset_table.clicked.connect(self.remove_rows)

    def init_shortcuts(self):
        # Ctrl+Enter to start session
        self.return_shortcut = QShortcut(QtGui.QKeySequence("Ctrl+Return"), self)
        self.return_shortcut.activated.connect(self.start_session)
        self.enter_shortcut = QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self)
        self.enter_shortcut.activated.connect(self.start_session)
        # Add entry
        self.add_shortcut = QShortcut(QtGui.QKeySequence("Shift+Return"), self)
        self.add_shortcut.activated.connect(self.append_schedule)
        self.add_shortcut = QShortcut(QtGui.QKeySequence("Shift+Enter"), self)
        self.add_shortcut.activated.connect(self.append_schedule)
        # Delete entry
        self.remove_shortcut = QShortcut(QtGui.QKeySequence("Delete"), self)
        self.remove_shortcut.activated.connect(self.remove_row)
        # Escape to close window
        self.escape_shortcut = QShortcut(QtGui.QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.close)
        self.manage_order_shortcut = QShortcut(
            QtGui.QKeySequence("Ctrl+Shift+I"), self
        )
        self.manage_order_shortcut.activated.connect(self.open_selection_order_viewer)

    def check_version(self):
        """
        Checks for updates via UpdateChecker, which itself updates
        self.config["update_check"] in config.json.
        """
        checker = UpdateChecker(__version__)
        update = (
            checker.check_for_updates() if self.config.get("update_check") else None
        )
        if update:
            self.show_temporary_status(
                "Update available! Please visit the site to download!", 5000
            )
            self.show_temporary_status(f"v{update['version']}: {update['notes']}", 6000)
        self.config_path = checker.config_path

    def show_and_activate(self):
        self.show()
        self.raise_()
        self.activateWindow()


def main():
    """Main entry point for the GestureSesh application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton, True)
    if hasattr(QtCore.Qt, "AA_DisableSessionManager"):
        app.setAttribute(QtCore.Qt.AA_DisableSessionManager, True)

    view = MainApp()
    view.show_and_activate()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
