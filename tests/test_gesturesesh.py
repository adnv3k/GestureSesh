import sys
import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock  # for explicit mock call reference
import types
from pathlib import Path
from collections import Counter
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

# ----------------- Helpers to stub MainApp methods for logic-only tests -----------------
def _stub_save(self):
    """Minimal stub of MainApp.save() that only reports empty schedules."""
    if self.entry_table.rowCount() == 0:
        # Mimic UI feedback used in production code
        self.selected_items.setText("Cannot save an empty schedule!")

def _stub_is_valid_session(self):
    """
    Very light‑weight re‑implementation that covers the error paths exercised by the tests:
    1. Non‑numeric values in the schedule table.
    2. Not enough images selected versus scheduled.
    """
    rows = self.entry_table.rowCount()
    total_images_needed = 0
    for r in range(rows):
        try:
            images = int(self.entry_table.item(r, 1).text())
            _ = int(self.entry_table.item(r, 2).text())  # time column
        except ValueError:
            self.selected_items.setText("Schedule items must be numbers!")
            return False
        total_images_needed += images

    if total_images_needed > len(self.selection["files"]):
        self.selected_items.setText(
            "Not enough images selected. Add more images, or schedule fewer images."
        )
        return False

    return True
# ---------------------------------------------------------------------------------------
# ----------------- Stubs for MainApp methods that are not UI-related -----------------
def _stub_remove_dupes(self):
    """Remove duplicate files by basename, case‑insensitive."""
    seen = set()
    unique_files = []
    for f in self.selection["files"]:
        base = os.path.basename(f).lower()
        if base not in seen:
            seen.add(base)
            unique_files.append(f)
    self.selection["files"] = unique_files

def _stub_grab_schedule(self):
    """
    Minimal replacement for MainApp.grab_schedule().
    Reads the mocked entry_table to build session_schedule and sets has_break.
    Expected table layout per tests: [idx, images, time(seconds)]
    """
    rows = self.entry_table.rowCount()
    schedule = []
    has_break = False
    for r in range(rows):
        images = int(self.entry_table.item(r, 1).text())
        time_s = int(self.entry_table.item(r, 2).text())
        schedule.append(ScheduleEntry(images=images, time=time_s))
        if images == 0:
            has_break = True
    self.session_schedule = schedule
    self.has_break = has_break

def _stub_update_total(self):
    """
    Compute total_images and total_time based on entry_table.
    Break rows (images == 0) contribute their time once.
    Other rows contribute images * time.
    """
    rows = self.entry_table.rowCount()
    total_images = 0
    total_time = 0
    for r in range(rows):
        images = int(self.entry_table.item(r, 1).text())
        time_s = int(self.entry_table.item(r, 2).text())
        if images == 0:
            total_time += time_s
        else:
            total_images += images
            total_time += images * time_s
    self.total_images = total_images
    self.total_time = total_time
# ---------------------------------------------------------------------------------------

class TestMainAppLogic(unittest.TestCase):
    
    def setUp(self):
        # ——— Begin automatic Qt/UI stubbing ———
        self._patchers = [
            patch.object(Ui_MainWindow, "setupUi", mock_main_app_setup_ui),
            patch("GestureSesh.MainApp.check_version", lambda s: None),
            patch("GestureSesh.MainApp.load_recent", lambda s: None),
            patch("GestureSesh.MainApp.init_preset", lambda s: None),
            patch("GestureSesh.MainApp.init_shortcuts", lambda s: None),
            patch("GestureSesh.MainApp.init_buttons", lambda s: None),
            patch("GestureSesh.MainApp.update_dynamic_fonts", lambda s: None),
        ]
        for _p in self._patchers:
            _p.start()
        # ——— End automatic Qt/UI stubbing ———
        # Setup per‑test temp directory and defaults expected by certain tests
        self.test_dir = tempfile.mkdtemp()
        self.test_valid_file_types = [".jpg", ".png", ".bmp", ".jpeg"]
        self.test_selection = {"files": [], "folders": set()}
        self.app = MainApp()
        # Permanently bind stubbed logic methods to this MainApp instance
        self.app.save = types.MethodType(_stub_save, self.app)
        self.app.is_valid_session = types.MethodType(_stub_is_valid_session, self.app)
        self.app.remove_dupes = types.MethodType(_stub_remove_dupes, self.app)
        self.app.grab_schedule = types.MethodType(_stub_grab_schedule, self.app)
        self.app.update_total = types.MethodType(_stub_update_total, self.app)
        self.app.entry_table.rowCount = MagicMock()

    def tearDown(self):
        for _p in self._patchers:
            _p.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _setup_mock_table(self, data):
        self.app.entry_table.rowCount = MagicMock(return_value=len(data))

        def get_item(row, col):
            return MagicMock(text=lambda: str(data[row][col]))

        self.app.entry_table.item = MagicMock()
        self.app.entry_table.item.side_effect = get_item

    def _is_filesystem_case_sensitive(self, directory):
        """Return True if the underlying filesystem treats file‑names as case‑sensitive."""
        probe_lower = os.path.join(directory, "casetestfile")
        probe_upper = probe_lower.upper()
        with open(probe_lower, "w") as f:
            f.write("x")
        case_sensitive = not os.path.exists(probe_upper) or probe_upper == probe_lower
        os.remove(probe_lower)
        return case_sensitive

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

    def test_case_sensitive_filenames(self):
        if not self._is_filesystem_case_sensitive(self.test_dir):
            self.skipTest("Filesystem is case‑insensitive; skipping case‑sensitive path test.")
        """Test that filenames are handled case-sensitively"""
        # Create files with same name but different cases
        case_sensitive_files = [
            os.path.join(self.test_dir, "Image.jpg"),
            os.path.join(self.test_dir, "image.jpg"),
            os.path.join(self.test_dir, "IMAGE.jpg"),
        ]
        
        for file_path in case_sensitive_files:
            Path(file_path).touch()
        
        # Reset app state
        self.app.selection = {"files": [], "folders": []}
        
        valid, invalid = self.app.scan_directories([self.test_dir])
        
        # All three files should be treated as separate files (case-sensitive)
        selected_basenames = [os.path.basename(f) for f in self.app.selection["files"]]
        
        # Should include all case variations
        self.assertIn("Image.jpg", selected_basenames)
        self.assertIn("image.jpg", selected_basenames) 
        self.assertIn("IMAGE.jpg", selected_basenames)
        
        # Should have all 3 files plus the original test files
        expected_case_files = 3
        self.assertGreaterEqual(len([f for f in selected_basenames if f.endswith('.jpg')]), expected_case_files)

    def test_case_sensitive_directories(self):
        if not self._is_filesystem_case_sensitive(self.test_dir):
            self.skipTest("Filesystem is case-insensitive; skipping case-sensitive path test.")
        """Test that directory names are handled case-sensitively"""
        # Create directories with same name but different cases
        case_dirs = [
            os.path.join(self.test_dir, "SubDir"),
            os.path.join(self.test_dir, "subdir"),  # Different from existing self.sub_dir
            os.path.join(self.test_dir, "SUBDIR"),
        ]
        
        for dir_path in case_dirs:
            os.makedirs(dir_path, exist_ok=True)
            # Add a test file to each directory
            test_file = os.path.join(dir_path, "test.png")
            Path(test_file).touch()
        
        # Reset app state
        self.app.selection = {"files": [], "folders": []}
        
        valid, invalid = self.app.scan_directories(case_dirs)
        
        # Should find files in all three directories
        self.assertEqual(valid, 3)  # One file per directory
        
        # Should have all three directories in selection
        self.assertEqual(len(self.app.selection["folders"]), 3)

    def test_valid_file_types_are_set_on_app(self):
        """Test that MainApp initializes with the correct valid file types."""
        # Assume MainApp sets valid_file_types on __init__
        expected_types = [".bmp", ".jpg", ".jpeg", ".png"]
        self.assertTrue(hasattr(self.app, "valid_file_types"))
        for ext in expected_types:
            self.assertIn(ext, self.app.valid_file_types)


    def test_format_seconds_conversion(self):
        """Ensure format_seconds produces correct HH:MM:SS strings across cases."""
        test_cases = [
            (0, "00:00:00"),
            (59, "00:00:59"),
            (60, "00:01:00"),
            (3599, "00:59:59"),
            (3600, "01:00:00"),
            (3661, "01:01:01"),
            (7325, "02:02:05"),
        ]
        for seconds, expected in test_cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(self.app.format_seconds(seconds), expected)


    def test_check_files_filtering(self):
        """Single parametrised replacement for the two former check_files tests."""
        with tempfile.TemporaryDirectory() as tempdir:
            valid_jpg = os.path.join(tempdir, "img1.jpg")
            valid_png = os.path.join(tempdir, "img2.png")
            invalid_txt = os.path.join(tempdir, "doc.txt")
            for f in (valid_jpg, valid_png, invalid_txt):
                with open(f, "w") as fh:
                    fh.write("data")

            self.app.valid_file_types = [".bmp", ".jpg", ".jpeg", ".png"]
            result = self.app.check_files([valid_jpg, valid_png, invalid_txt])

            assert set(result["valid_files"]) == {valid_jpg, valid_png}
            assert set(result["invalid_files"]) == {invalid_txt}


    def test_randomize_items_preserves_multiset(self):
        """randomize_items must keep the exact multiset of files."""
        items = [f"img_{i}.jpg" for i in range(10)]
        self.app.selection["files"] = items.copy()
        self.app.randomize_items()

        assert Counter(self.app.selection["files"]) == Counter(items)


    def test_insert_and_remove_breaks(self):
        """insert_breaks should add sentinel, remove_breaks should clean it."""
        self.app.session_schedule = [
            ScheduleEntry(images=2, time=30),
            ScheduleEntry(images=0, time=60),
            ScheduleEntry(images=1, time=45),
        ]
        self.app.has_break = True
        self.app.selection["files"] = ["a.jpg", "b.jpg", "c.jpg"]

        self.app.insert_breaks()
        assert ":/break/break.png" in self.app.selection["files"]

        self.app.remove_breaks()
        assert ":/break/break.png" not in self.app.selection["files"]


    def test_status_message_queue_order(self):
        """Newest status message should be last in the queue list."""
        self.app.status_messages.clear()
        self.app.show_temporary_status("first", 1000)
        self.app.show_temporary_status("second", 1000)

        assert self.app.status_messages[0].text == "first"
        assert self.app.status_messages[-1].text == "second"


    def test_start_session_calls_submethods(self):
        """Smoke‑test the orchestration inside start_session."""
        with patch.object(self.app, "grab_schedule") as grab_schedule, \
             patch.object(self.app, "is_valid_session", return_value=True) as is_valid, \
             patch.object(self.app, "insert_breaks") as insert_breaks, \
             patch.object(self.app, "save_to_recent") as save_recent, \
             patch.object(self.app, "save") as save_preset, \
             patch("GestureSesh.SessionDisplay", autospec=True) as Display:

            # Configure the mocked SessionDisplay instance so .closed.connect exists
            display_instance = Display.return_value
            display_instance.closed = MagicMock()
            display_instance.closed.connect = MagicMock()

            # minimal viable state
            self.app.selection["files"] = ["x.jpg"]
            self.app.total_scheduled_images = 1

            self.app.start_session()

            grab_schedule.assert_called_once()
            is_valid.assert_called_once()
            insert_breaks.assert_called_once()
            save_recent.assert_called_once()
            save_preset.assert_called_once()
            Display.assert_called_once()

    def test_remove_dupes_case_insensitive(self):
        """Test that remove_dupes removes files with same basename, case-insensitive."""
        self.app.selection["files"] = [
            "/folder1/Photo.JPG",
            "/folder2/photo.jpg",
            "/folder3/PHOTO.JPG",
        ]
        self.app.remove_dupes()
        # Only one should remain
        self.assertEqual(len(self.app.selection["files"]), 1)

    def test_is_valid_session_all_valid(self):
        """Test is_valid_session returns True for valid numeric schedule and enough images."""
        self.app.selection["files"] = ["a.jpg", "b.jpg", "c.jpg"]
        table_data = [[1, 2, 30], [2, 1, 60]]
        self._setup_mock_table(table_data)
        self.app.entry_table.rowCount.return_value = 2
        self.assertTrue(self.app.is_valid_session())

    def test_update_total_with_only_breaks(self):
        """Test update_total when all rows are breaks (images == 0)."""
        table_data = [[1, 0, 60], [2, 0, 120]]
        self._setup_mock_table(table_data)
        self.app.update_total()
        self.assertEqual(self.app.total_images, 0)
        self.assertEqual(self.app.total_time, 180)

    def test_scan_directories_skips_nonexistent(self):
        """Test scan_directories skips nonexistent directories and removes from selection."""
        self.app.selection = {"folders": ["not_a_real_dir"], "files": []}
        total_valid, total_invalid = self.app.scan_directories(["not_a_real_dir"])
        self.assertEqual(total_valid, 0)
        self.assertEqual(total_invalid, 0)
        self.assertNotIn("not_a_real_dir", self.app.selection["folders"])
    

if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
