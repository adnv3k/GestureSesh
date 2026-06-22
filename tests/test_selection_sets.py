"""Tests for per-preset image-set associations (selection_sets.py)."""

import os
import sys
import types
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from gesturesesh.main import MainApp
from gesturesesh.ui.main_window import Ui_MainWindow


def _mock_setup_ui(self, main_window):
    """Minimal widget stubbing so MainApp() constructs without a real UI."""
    self.selected_items = MagicMock(spec=QtWidgets.QTextEdit)
    self.preset_loader_box = MagicMock(spec=QtWidgets.QComboBox)
    self.entry_table = MagicMock(spec=QtWidgets.QTableWidget)
    self.total_table = MagicMock(spec=QtWidgets.QTableWidget)
    self.randomize_selection = MagicMock(spec=QtWidgets.QPushButton)
    self.set_number_of_images = MagicMock(spec=QtWidgets.QSpinBox)
    self.set_minutes = MagicMock(spec=QtWidgets.QSpinBox)
    self.set_seconds = MagicMock(spec=QtWidgets.QSpinBox)
    self.dialog_buttons = MagicMock(spec=QtWidgets.QDialogButtonBox)


class TestSelectionSets(unittest.TestCase):
    def setUp(self):
        self._patchers = [
            patch.object(Ui_MainWindow, "setupUi", _mock_setup_ui),
            patch("gesturesesh.main.MainApp.check_version", lambda s: None),
            patch("gesturesesh.main.MainApp.load_recent", lambda s: None),
            patch("gesturesesh.main.MainApp.init_preset", lambda s: None),
            patch("gesturesesh.main.MainApp.init_shortcuts", lambda s: None),
            patch("gesturesesh.main.MainApp.init_buttons", lambda s: None),
            patch("gesturesesh.main.MainApp.update_dynamic_fonts", lambda s: None),
        ]
        for p in self._patchers:
            p.start()

        self.test_dir = tempfile.mkdtemp()
        self.app = MainApp()

        # Isolate from the real on-disk config and any pre-existing state.
        self.app.config = {}
        self.app.config_path = Path(self.test_dir) / "config.json"
        self.app.presets = {}
        self.app.selection_sets = {}
        self.app._active_set_preset = None
        self.app._loading = False
        self.app.selection = {"files": [], "folders": []}
        # Keep status/UI side effects out of the logic under test.
        self.app.show_temporary_status = types.MethodType(
            lambda s, *a, **k: None, self.app
        )
        self.app.display_status = types.MethodType(lambda s: None, self.app)

    def tearDown(self):
        for p in self._patchers:
            p.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _touch(self, name):
        path = os.path.join(self.test_dir, name)
        with open(path, "w") as f:
            f.write("x")
        return path

    # -- write-back / creation -------------------------------------------------

    def test_first_write_creates_and_links_set(self):
        self.app.presets = {"A": {"schedule": {}}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/x.png"], "folders": ["/imgs"]}

        self.app.write_back_active_set()

        set_id = self.app.presets["A"].get("selection_id")
        self.assertIsNotNone(set_id)
        self.assertEqual(
            self.app.selection_sets[set_id],
            {"files": ["/x.png"], "folders": ["/imgs"]},
        )

    def test_empty_selection_creates_no_link(self):
        self.app.presets = {"A": {"schedule": {}}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": [], "folders": []}

        self.app.write_back_active_set()

        self.assertNotIn("selection_id", self.app.presets["A"])
        self.assertEqual(self.app.selection_sets, {})

    def test_write_back_noop_when_unchanged(self):
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {"set1": {"files": ["/x.png"], "folders": []}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/x.png"], "folders": []}

        self.app.write_back_active_set()

        self.assertEqual(self.app.presets["A"]["selection_id"], "set1")
        self.assertEqual(list(self.app.selection_sets.keys()), ["set1"])

    def test_unshared_set_updated_in_place(self):
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {"set1": {"files": ["/x.png"], "folders": []}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/x.png", "/y.png"], "folders": []}

        self.app.write_back_active_set()

        self.assertEqual(self.app.presets["A"]["selection_id"], "set1")
        self.assertEqual(
            self.app.selection_sets["set1"],
            {"files": ["/x.png", "/y.png"], "folders": []},
        )

    def test_shared_set_edit_forks_copy_on_write(self):
        self.app.presets = {
            "A": {"schedule": {}, "selection_id": "set1"},
            "B": {"schedule": {}, "selection_id": "set1"},
        }
        self.app.selection_sets = {"set1": {"files": ["/x.png"], "folders": []}}
        self.app._active_set_preset = "B"
        self.app.selection = {"files": ["/x.png", "/y.png"], "folders": []}

        self.app.write_back_active_set()

        # A keeps the original set untouched; B gets a fresh forked set.
        self.assertEqual(self.app.presets["A"]["selection_id"], "set1")
        self.assertEqual(self.app.selection_sets["set1"], {"files": ["/x.png"], "folders": []})
        new_id = self.app.presets["B"]["selection_id"]
        self.assertNotEqual(new_id, "set1")
        self.assertEqual(
            self.app.selection_sets[new_id],
            {"files": ["/x.png", "/y.png"], "folders": []},
        )

    def test_loading_guard_suppresses_write(self):
        self.app.presets = {"A": {"schedule": {}}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/x.png"], "folders": []}
        self.app._loading = True

        self.app.write_back_active_set()

        self.assertNotIn("selection_id", self.app.presets["A"])
        self.assertEqual(self.app.selection_sets, {})

    # -- external-drive / offline safety --------------------------------------

    def test_offline_set_preserved_when_no_edits(self):
        # Paths under a directory that does not exist (simulates an unplugged
        # drive: the whole mount point is gone).
        offline = [
            "/Volumes/NopeDriveXYZ/refs/a.png",
            "/Volumes/NopeDriveXYZ/refs/b.png",
        ]
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {
            "set1": {"files": list(offline), "folders": ["/Volumes/NopeDriveXYZ/refs"]}
        }
        self.app._active_set_preset = "A"
        # apply() while offline would leave the working selection empty.
        self.app.selection = {"files": [], "folders": []}

        self.app.write_back_active_set()

        self.assertEqual(self.app.selection_sets["set1"]["files"], offline)

    def test_offline_files_preserved_when_adding_local_file(self):
        offline = "/Volumes/NopeDriveXYZ/refs/a.png"
        local = self._touch("local.png")
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {"set1": {"files": [offline], "folders": []}}
        self.app._active_set_preset = "A"
        # User added a local file while the drive was disconnected.
        self.app.selection = {"files": [local], "folders": []}

        self.app.write_back_active_set()

        files = self.app.selection_sets["set1"]["files"]
        self.assertIn(local, files)
        self.assertIn(offline, files)

    def test_in_place_deleted_file_dropped_offline_kept(self):
        # f1 exists then is removed by the user (its folder still exists ->
        # treated as a real removal). offline file's tree is gone -> preserved.
        f1 = self._touch("keep_then_remove.png")
        offline = "/Volumes/NopeDriveXYZ/refs/b.png"
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {"set1": {"files": [f1, offline], "folders": []}}
        self.app._active_set_preset = "A"
        # User removed f1 from the visible selection.
        self.app.selection = {"files": [], "folders": []}

        self.app.write_back_active_set()

        self.assertEqual(self.app.selection_sets["set1"]["files"], [offline])

    # -- garbage collection ----------------------------------------------------

    def test_gc_removes_orphans_keeps_linked(self):
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {
            "set1": {"files": ["/x.png"], "folders": []},
            "orphan": {"files": ["/z.png"], "folders": []},
        }

        self.app._gc_selection_sets()

        self.assertIn("set1", self.app.selection_sets)
        self.assertNotIn("orphan", self.app.selection_sets)

    # -- apply / lazy validation ----------------------------------------------

    def test_apply_set_drops_missing_files_preserves_order(self):
        f1 = self._touch("a.png")
        f2 = self._touch("b.png")
        missing = os.path.join(self.test_dir, "gone.png")
        self.app.selection_sets = {
            "set1": {"files": [f1, missing, f2], "folders": [self.test_dir]}
        }

        self.app.apply_selection_set("set1")

        self.assertEqual(self.app.selection["files"], [f1, f2])
        self.assertEqual(self.app.selection["folders"], [self.test_dir])

    def test_apply_missing_id_is_noop(self):
        self.app.selection = {"files": ["/keep.png"], "folders": ["/keep"]}
        self.app.apply_selection_set("does-not-exist")
        self.assertEqual(self.app.selection, {"files": ["/keep.png"], "folders": ["/keep"]})

    # -- switch handler --------------------------------------------------------

    def test_on_preset_switch_writes_old_and_applies_new(self):
        b1 = self._touch("b1.png")
        self.app.presets = {
            "A": {"schedule": {}, "selection_id": "setA"},
            "B": {"schedule": {}, "selection_id": "setB"},
        }
        self.app.selection_sets = {
            "setA": {"files": ["/old.png"], "folders": []},
            "setB": {"files": [b1], "folders": []},
        }
        self.app._active_set_preset = "A"
        # Live working copy for A diverged from setA.
        self.app.selection = {"files": ["/a-new.png"], "folders": []}
        self.app.preset_loader_box.currentText = lambda: "B"

        self.app.on_preset_switch()

        # A's set was written back from the live selection (unshared -> in place).
        self.assertEqual(
            self.app.selection_sets["setA"], {"files": ["/a-new.png"], "folders": []}
        )
        # B's set is applied to the live selection (validated).
        self.assertEqual(self.app.selection["files"], [b1])
        self.assertEqual(self.app._active_set_preset, "B")

    def test_on_preset_switch_unlinked_target_keeps_selection(self):
        self.app.presets = {
            "A": {"schedule": {}, "selection_id": "setA"},
            "B": {"schedule": {}},  # no linked set
        }
        self.app.selection_sets = {"setA": {"files": ["/old.png"], "folders": []}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/keep.png"], "folders": []}
        self.app.preset_loader_box.currentText = lambda: "B"

        self.app.on_preset_switch()

        # Switching to an unlinked preset leaves the current selection in place.
        self.assertEqual(self.app.selection["files"], ["/keep.png"])
        self.assertEqual(self.app._active_set_preset, "B")


if __name__ == "__main__":
    unittest.main()
