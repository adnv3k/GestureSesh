import unittest
from unittest.mock import patch, MagicMock
import os
from PyQt5.QtWidgets import QApplication
import sys

from GestureSesh import MainApp, ScheduleEntry

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class DummyUi:
    """Minimal dummy UI for MainApp logic testing."""
    def __init__(self):
        self.selected_items = MagicMock()
        self.preset_loader_box = MagicMock()
        self.entry_table = MagicMock()
        self.total_table = MagicMock()
        self.randomize_selection = MagicMock()
        self.set_number_of_images = MagicMock()
        self.set_minutes = MagicMock()
        self.set_seconds = MagicMock()

class TestMainAppLogic(unittest.TestCase):
    def setUp(self):
        # Patch Ui_MainWindow to avoid full UI setup
        patcher = patch('GestureSesh.Ui_MainWindow', new=DummyUi)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.app = MainApp()
        # Patch out methods that require full UI
        self.app.display_status = MagicMock()
        self.app.update_total = MagicMock()
        self.app.selected_items = MagicMock()
        self.app.preset_loader_box = MagicMock()
        self.app.entry_table = MagicMock()
        self.app.total_table = MagicMock()
        self.app.randomize_selection = MagicMock()
        self.app.set_number_of_images = MagicMock()
        self.app.set_minutes = MagicMock()
        self.app.set_seconds = MagicMock()

    def test_check_files(self):
        files = ["image1.jpg", "image2.png", "doc.txt", "photo.jpeg"]
        result = self.app.check_files(files)
        self.assertIn("image1.jpg", result["valid_files"])
        self.assertIn("doc.txt", result["invalid_files"])
        self.assertIn("photo.jpeg", result["valid_files"])

    def test_remove_dupes(self):
        self.app.selection["files"] = [
            "/folder/a.jpg", "/folder/b.jpg", "/folder/a.jpg"
        ]
        self.app.remove_dupes()
        self.assertEqual(len(self.app.selection["files"]), 2)
        self.assertIn("/folder/a.jpg", self.app.selection["files"])
        self.assertIn("/folder/b.jpg", self.app.selection["files"])

    @patch("os.path.exists", return_value=True)
    @patch("os.walk")
    def test_scan_directories(self, mock_walk, mock_exists):
        mock_walk.return_value = [
            ("/folder", [], ["a.jpg", "b.txt", "c.png"])
        ]
        self.app.selection["folders"] = []
        self.app.selection["files"] = []
        valid, invalid = self.app.scan_directories(["/folder"])
        self.assertEqual(valid, 2)
        self.assertEqual(invalid, 1)
        self.assertIn("/folder/a.jpg", self.app.selection["files"])
        self.assertIn("/folder/c.png", self.app.selection["files"])
        self.assertIn("/folder", self.app.selection["folders"])

    def test_format_seconds(self):
        # 1 hour, 2 minutes, 3 seconds = 3723
        result = self.app.format_seconds(3723)
        self.assertTrue(isinstance(result, str))
        self.assertIn(":", result)

    def test_remove_items(self):
        self.app.selection["files"] = ["a.jpg", "b.jpg"]
        self.app.selection["folders"] = ["/folder"]
        self.app.remove_items()
        self.assertEqual(self.app.selection["files"], [])
        self.assertEqual(self.app.selection["folders"], [])

if __name__ == "__main__":
    unittest.main()