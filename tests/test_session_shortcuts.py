import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import unittest

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gesturesesh.session_window import SessionDisplay
from gesturesesh.ui.session_display import Ui_session_display


class TestSessionDisplayShortcuts(unittest.TestCase):
    def test_filter_buttons_do_not_own_window_shortcuts(self):
        widget = QtWidgets.QWidget()
        ui = Ui_session_display()
        ui.setupUi(widget)

        self.assertTrue(ui.grayscale_button.shortcut().isEmpty())
        self.assertTrue(ui.flip_horizontal_button.shortcut().isEmpty())
        self.assertTrue(ui.flip_vertical_button.shortcut().isEmpty())

    def test_filter_shortcuts_are_registered_on_session_window(self):
        class DummySession(QtWidgets.QWidget):
            pass

        dummy = DummySession()
        callback_names = [
            "toggle_resize",
            "toggle_always_on_top",
            "toggle_mute",
            "add_30_seconds",
            "add_60_seconds",
            "restart_timer",
            "skip_image",
            "toggle_frameless",
            "toggle_fullscreen_frameless",
            "increase_brightness",
            "decrease_brightness",
            "increase_contrast",
            "decrease_contrast",
            "toggle_threshold",
            "toggle_edge",
            "reset_image_mods",
            "toggle_grayscale_mode",
            "grayscale",
            "flip_horizontal",
            "flip_vertical",
            "open_image_directory",
            "toggle_zoom_enabled",
            "reset_zoom_to_default",
            "quick_inspect",
            "open_session_order_viewer",
            "toggle_zoom_reset_mode",
            "open_shortcut_map",
        ]
        for name in callback_names:
            setattr(dummy, name, lambda: None)

        SessionDisplay.init_shortcuts(dummy)

        self.assertEqual(dummy.grayscale_shortcut.key().toString(), "G")
        self.assertEqual(dummy.flip_horizontal_shortcut.key().toString(), "H")
        self.assertEqual(dummy.flip_vertical_shortcut.key().toString(), "V")
        self.assertEqual(dummy.frameless_fullscreen.key().toString(), "Ctrl+Shift+F")
        self.assertEqual(dummy.selection_order_key.key().toString(), "Ctrl+Shift+I")
