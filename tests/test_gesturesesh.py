import sys
import unittest
from unittest.mock import patch, MagicMock, call

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication

# Ensure a QApplication instance exists for Qt widgets
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from GestureSesh import MainApp, SessionDisplay, ScheduleEntry
from main_window import Ui_MainWindow
from session_display import Ui_session_display


def mock_main_app_setup_ui(self, main_window):
    """Mocks the MainApp's setupUi by attaching MagicMock widgets."""
    self.selected_items = MagicMock(spec=QtWidgets.QTextEdit)
    self.preset_loader_box = MagicMock(spec=QtWidgets.QComboBox)
    self.entry_table = MagicMock(spec=QtWidgets.QTableWidget)
    self.total_table = MagicMock(spec=QtWidgets.QTableWidget)
    self.randomize_selection = MagicMock(spec=QtWidgets.QPushButton)
    self.set_number_of_images = MagicMock(spec=QtWidgets.QSpinBox)
    self.set_minutes = MagicMock(spec=QtWidgets.QSpinBox)
    self.set_seconds = MagicMock(spec=QtWidgets.QSpinBox)
    self.dialog_buttons = MagicMock(spec=QtWidgets.QDialogButtonBox)


def mock_session_display_setup_ui(self, session_display_window):
    """Mocks the SessionDisplay's setupUi, creating all necessary widgets."""
    self.image_display = MagicMock(spec=QtWidgets.QLabel)
    self.timer_display = MagicMock(spec=QtWidgets.QLabel)
    self.session_info = MagicMock(spec=QtWidgets.QLabel)
    self.previous_image = MagicMock(spec=QtWidgets.QPushButton)
    self.pause_timer = MagicMock(spec=QtWidgets.QPushButton)
    self.stop_session = MagicMock(spec=QtWidgets.QPushButton)
    self.next_image = MagicMock(spec=QtWidgets.QPushButton)
    self.grayscale_button = MagicMock(spec=QtWidgets.QPushButton)
    self.flip_horizontal_button = MagicMock(spec=QtWidgets.QPushButton)
    self.flip_vertical_button = MagicMock(spec=QtWidgets.QPushButton)


class TestMainAppLogic(unittest.TestCase):
    """Test suite for the main application logic."""

    @patch.object(Ui_MainWindow, "setupUi", mock_main_app_setup_ui)
    @patch("GestureSesh.MainApp.check_version", lambda s: None)
    @patch("GestureSesh.MainApp.load_recent", lambda s: None)
    @patch("GestureSesh.MainApp.init_preset", lambda s: None)
    @patch("GestureSesh.MainApp.init_shortcuts", lambda s: None)
    @patch("GestureSesh.MainApp.init_buttons", lambda s: None)
    def setUp(self):
        self.app = MainApp()
        self.app.total_table.rowCount.return_value = 0

    def _setup_mock_table(self, data):
        self.app.entry_table.rowCount.return_value = len(data)

        def get_item(row, col):
            return MagicMock(text=lambda: str(data[row][col]))

        self.app.entry_table.item.side_effect = get_item

    def test_remove_dupes_by_basename(self):
        self.app.selection["files"] = [
            "/folder1/a.jpg",
            "/folder2/b.jpg",
            "/folder3/a.jpg",
        ]
        self.app.remove_dupes()
        self.assertEqual(len(self.app.selection["files"]), 2)

    def test_grab_schedule(self):
        table_data = [[1, 10, 30], [2, 0, 120]]
        self._setup_mock_table(table_data)
        self.app.grab_schedule()
        self.assertEqual(
            self.app.session_schedule[0], ScheduleEntry(images=10, time=30)
        )
        self.assertTrue(self.app.has_break)

    def test_update_total(self):
        table_data = [[1, 10, 30], [2, 0, 120], [3, 1, 180]]
        self._setup_mock_table(table_data)
        self.app.update_total()
        self.assertEqual(self.app.total_images, 11)
        self.assertEqual(self.app.total_time, 600)

    @patch("GestureSesh.Path.is_file", return_value=True)
    def test_is_valid_session_not_enough_images(self, mock_is_file):
        self.app.session_schedule = [ScheduleEntry(images=5, time=30)]
        self.app.selection["files"] = ["a.jpg", "b.jpg"]
        self.app.entry_table.rowCount.return_value = 1
        self._setup_mock_table([[1, 5, 30]])
        self.assertFalse(self.app.is_valid_session())
        self.app.selected_items.setText.assert_called_with(
            "Not enough images selected. Add more images, or schedule fewer images."
        )

    @patch("GestureSesh.shelve.open")
    def test_save_and_load_preset(self, mock_shelve_open):
        mock_db = {}
        mock_shelve_open.return_value.__enter__.return_value = mock_db
        self._setup_mock_table([[1, 5, 45]])
        self.app.preset_loader_box.currentText.return_value = "TestPreset"
        self.app.presets = {}
        self.app.save()
        self.assertIn("TestPreset", self.app.presets)
        self.app.load()
        self.app.entry_table.insertRow.assert_called_once_with(0)

    def test_append_schedule_adds_row_with_correct_data(self):
        self.app.set_number_of_images.value.return_value = 15
        self.app.set_minutes.value.return_value = 1
        self.app.set_seconds.value.return_value = 30
        self.app.entry_table.rowCount.return_value = 0
        self.app.append_schedule()
        self.app.entry_table.insertRow.assert_called_with(0)
        self.assertEqual(
            self.app.entry_table.setItem.call_args_list[2].args[2].text(), "90"
        )

    def test_remove_row(self):
        self.app.entry_table.currentRow.return_value = 3
        self.app.remove_row()
        self.app.entry_table.removeRow.assert_called_with(3)

    @patch("GestureSesh.shelve.open")
    def test_save_empty_preset_is_handled(self, mock_shelve_open):
        self.app.entry_table.rowCount.return_value = 0
        self.app.save()
        # FIX: Check if the error message was ever called, not if it was the last call.
        self.app.selected_items.setText.assert_any_call(
            "Cannot save an empty schedule!"
        )
        mock_shelve_open.assert_not_called()

    def test_is_valid_session_with_invalid_text_in_table(self):
        self._setup_mock_table([[1, "abc", 30]])
        self.app.entry_table.rowCount.return_value = 1
        self.assertFalse(self.app.is_valid_session())
        self.app.selected_items.setText.assert_called_with(
            "Schedule items must be numbers!"
        )


class TestSessionDisplayLogic(unittest.TestCase):
    """Test suite for the SessionDisplay window's logic."""

    @patch.object(Ui_session_display, "setupUi", mock_session_display_setup_ui)
    @patch("GestureSesh.mixer.init")
    @patch("GestureSesh.mixer.music")
    @patch("GestureSesh.SessionDisplay.init_shortcuts", lambda s: None)
    @patch("GestureSesh.SessionDisplay.init_buttons", lambda s: None)
    @patch("GestureSesh.SessionDisplay.display_image")
    def setUp(self, mock_display_image, mock_mixer_music, mock_mixer_init):
        self.schedule = [
            ScheduleEntry(images=2, time=30),
            ScheduleEntry(images=1, time=60),
        ]
        self.items = ["a.jpg", "b.jpg", "c.jpg"]
        self.total = 3
        with patch.object(
            SessionDisplay, "load_entry", lambda s, resume_timer=True: None
        ):
            self.session = SessionDisplay(self.schedule, self.items, self.total)
            # FIX: Replace real timers with mocks to allow for configuration in tests.
            self.session.timer = MagicMock(spec=QtCore.QTimer)
            self.session.close_timer = MagicMock(spec=QtCore.QTimer)

    def tearDown(self):
        if hasattr(self, "session"):
            self.session.timer.stop()
            self.session.close_timer.stop()

    def test_initialization(self):
        def mock_load_entry(session, resume_timer=True):
            session.time_seconds = session.schedule[session.entry["current"]].time

        with patch.object(SessionDisplay, "load_entry", mock_load_entry):
            session = SessionDisplay(self.schedule, self.items, self.total)
        self.assertEqual(session.entry["current"], 0)
        self.assertEqual(session.time_seconds, 30)

    @patch("GestureSesh.SessionDisplay.display_image")
    def test_load_next_image_navigation(self, mock_display_image):
        session = self.session
        session.time_seconds = session.schedule[0].time
        session.entry["amount of items"] = session.schedule[0].images - 1
        session.load_next_image()
        self.assertEqual(session.playlist_position, 1)
        session.load_next_image()
        self.assertEqual(session.time_seconds, 60)

    @patch("GestureSesh.SessionDisplay.display_image")
    def test_previous_image_navigation(self, mock_display_image):
        session = self.session
        session.time_seconds = 30
        session.playlist_position = 1
        session.entry["current"] = 0
        session.entry["amount of items"] = 0
        session.previous_playlist_position()
        self.assertEqual(session.playlist_position, 0)
        session.previous_playlist_position()
        session.timer_display.setText.assert_called_with(
            "First image! Restarting timer..."
        )

    @patch("GestureSesh.SessionDisplay.display_image")
    def test_grayscale_toggle(self, mock_display_image):
        self.assertFalse(self.session.image_mods["grayscale"])
        mock_display_image.reset_mock()
        self.session.grayscale()
        self.assertTrue(self.session.image_mods["grayscale"])
        mock_display_image.assert_called_once()

    def test_pause_and_resume_timer(self):
        self.session.time_seconds = 30
        self.session.timer.isActive.return_value = True
        self.session.pause()
        self.session.timer.stop.assert_called_once()
        self.session.timer.isActive.return_value = False
        self.session.pause()
        self.session.timer.start.assert_called_once_with(500)

    def test_session_lifecycle_end_and_cancel(self):
        self.assertFalse(self.session.session_finished)
        self.session.end_session()
        self.assertTrue(self.session.session_finished)
        self.session.close_timer.start.assert_called_with(1000)
        self.session.cancel_close_countdown()
        self.session.close_timer.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
