import sys
import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from GestureSesh import MainApp, SessionDisplay, ScheduleEntry
from main_window import Ui_MainWindow
from session_display import Ui_session_display


def mock_main_app_setup_ui(self, main_window):
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

    def test_save_empty_preset_is_handled(self):
        self.app.entry_table.rowCount.return_value = 0
        self.app.save()
        self.app.selected_items.setText.assert_any_call(
            "Cannot save an empty schedule!"
        )

    def test_is_valid_session_with_invalid_text_in_table(self):
        self._setup_mock_table([[1, "abc", 30]])
        self.app.entry_table.rowCount.return_value = 1
        self.assertFalse(self.app.is_valid_session())
        self.app.selected_items.setText.assert_called_with(
            "Schedule items must be numbers!"
        )

    def test_check_files_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as tempdir:
            valid_file = os.path.join(tempdir, "image1.jpg")
            invalid_file = os.path.join(tempdir, "notimage.txt")
            with open(valid_file, "w") as f:
                f.write("fake image data")
            with open(invalid_file, "w") as f:
                f.write("not an image")
            subdir = os.path.join(tempdir, "sub")
            os.makedirs(subdir)
            valid_file2 = os.path.join(subdir, "image2.png")
            with open(valid_file2, "w") as f:
                f.write("fake image data")
            self.app.valid_file_types = [".bmp", ".jpg", ".jpeg", ".png"]
            files = [valid_file, invalid_file, valid_file2]
            result = self.app.check_files(files)
            self.assertIn(valid_file, result["valid_files"])
            self.assertIn(valid_file2, result["valid_files"])
            self.assertIn(invalid_file, result["invalid_files"])

    def test_scan_directories_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as tempdir:
            valid_file = os.path.join(tempdir, "image1.jpg")
            invalid_file = os.path.join(tempdir, "notimage.txt")
            with open(valid_file, "w") as f:
                f.write("fake image data")
            with open(invalid_file, "w") as f:
                f.write("not an image")
            subdir = os.path.join(tempdir, "sub")
            os.makedirs(subdir)
            valid_file2 = os.path.join(subdir, "image2.png")
            with open(valid_file2, "w") as f:
                f.write("fake image data")
            self.app.valid_file_types = [".bmp", ".jpg", ".jpeg", ".png"]
            self.app.selection = {"folders": [], "files": []}
            total_valid, total_invalid = self.app.scan_directories([tempdir])
            self.assertEqual(total_valid, 2)
            self.assertEqual(total_invalid, 1)
            self.assertIn(valid_file, self.app.selection["files"])
            self.assertIn(valid_file2, self.app.selection["files"])
            self.assertIn(tempdir, self.app.selection["folders"])

    def test_scan_directories_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as tempdir:
            valid_file = os.path.join(tempdir, "image1.jpg")
            dup_file = os.path.join(tempdir, "IMAGE1.JPG")
            with open(valid_file, "w") as f:
                f.write("fake image data")
            with open(dup_file, "w") as f:
                f.write("fake image data")
            self.app.valid_file_types = [".bmp", ".jpg", ".jpeg", ".png"]
            self.app.selection = {"folders": [], "files": []}
            total_valid, total_invalid = self.app.scan_directories([tempdir])
            files_lower = [f.lower() for f in self.app.selection["files"]]
            self.assertEqual(files_lower.count(valid_file.lower()), 1)

    def test_scan_directories_outside_allowed_dirs(self):
        with tempfile.TemporaryDirectory() as tempdir:
            valid_file = os.path.join(tempdir, "image1.jpg")
            with open(valid_file, "w") as f:
                f.write("fake image data")
            outside_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            outside_file.close()
            self.app.valid_file_types = [".bmp", ".jpg", ".jpeg", ".png"]
            self.app.selection = {"folders": [], "files": []}
            total_valid, total_invalid = self.app.scan_directories([outside_file.name])
            self.assertEqual(total_valid, 0)
            self.assertNotIn(outside_file.name, self.app.selection["files"])
            os.unlink(outside_file.name)

if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
