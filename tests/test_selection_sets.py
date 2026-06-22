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

    # -- unavailable reporting -------------------------------------------------

    def test_active_set_unavailable_lists_missing_files_and_folders(self):
        present = self._touch("here.png")
        gone = os.path.join(self.test_dir, "gone.png")
        missing_dir = os.path.join(self.test_dir, "no_such_dir")
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {
            "set1": {"files": [present, gone], "folders": [self.test_dir, missing_dir]}
        }
        self.app._active_set_preset = "A"

        result = self.app._active_set_unavailable()

        self.assertEqual(result["files"], [gone])
        self.assertEqual(result["folders"], [missing_dir])

    def test_active_set_unavailable_empty_when_all_present(self):
        present = self._touch("here.png")
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {
            "set1": {"files": [present], "folders": [self.test_dir]}
        }
        self.app._active_set_preset = "A"

        self.assertEqual(
            self.app._active_set_unavailable(), {"files": [], "folders": []}
        )

    def test_active_set_unavailable_empty_without_active_preset(self):
        self.app._active_set_preset = None
        self.assertEqual(
            self.app._active_set_unavailable(), {"files": [], "folders": []}
        )

    def test_active_set_unavailable_empty_when_preset_has_no_link(self):
        self.app.presets = {"A": {"schedule": {}}}  # no selection_id
        self.app._active_set_preset = "A"
        self.assertEqual(
            self.app._active_set_unavailable(), {"files": [], "folders": []}
        )

    # -- authoritative write (Manage Order curation) ---------------------------

    def test_authoritative_write_drops_offline_file_user_removed(self):
        # An offline file (whole dir gone) the user removed in Manage Order must
        # stay removed, even though the boundary merge would normally preserve it.
        present = self._touch("keep.png")
        offline = "/mnt/usb/gone.png"  # parent dir missing -> reads as offline
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {"set1": {"files": [present, offline], "folders": []}}
        self.app._active_set_preset = "A"

        self.app.write_back_active_set(
            snapshot={"files": [present], "folders": []}, authoritative=True
        )

        self.assertEqual(
            self.app.selection_sets["set1"], {"files": [present], "folders": []}
        )

    def test_authoritative_write_keeps_supplied_missing_files(self):
        present = self._touch("keep.png")
        offline = "/mnt/usb/later.png"
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {"set1": {"files": [present], "folders": []}}
        self.app._active_set_preset = "A"

        self.app.write_back_active_set(
            snapshot={"files": [present, offline], "folders": []},
            authoritative=True,
        )

        self.assertEqual(
            self.app.selection_sets["set1"],
            {"files": [present, offline], "folders": []},
        )

    def test_authoritative_write_forks_shared_set(self):
        present = self._touch("keep.png")
        self.app.presets = {
            "A": {"schedule": {}, "selection_id": "set1"},
            "B": {"schedule": {}, "selection_id": "set1"},
        }
        self.app.selection_sets = {"set1": {"files": ["/x.png"], "folders": []}}
        self.app._active_set_preset = "B"

        self.app.write_back_active_set(
            snapshot={"files": [present], "folders": []}, authoritative=True
        )

        # A keeps the shared set; B forks its own.
        self.assertEqual(self.app.presets["A"]["selection_id"], "set1")
        new_id = self.app.presets["B"]["selection_id"]
        self.assertNotEqual(new_id, "set1")
        self.assertEqual(
            self.app.selection_sets[new_id], {"files": [present], "folders": []}
        )
        self.assertEqual(
            self.app.selection_sets["set1"], {"files": ["/x.png"], "folders": []}
        )

    # -- Manage Order viewer integration ---------------------------------------

    def _prime_viewer_app(self, set_files):
        """Set up an active preset + live selection for viewer tests."""
        self.app.presets = {"A": {"schedule": {}, "selection_id": "set1"}}
        self.app.selection_sets = {"set1": {"files": list(set_files), "folders": []}}
        self.app._active_set_preset = "A"
        loadable = self.app.check_files(set_files)["valid_files"]
        self.app.selection = {"files": loadable, "folders": []}
        self.app.session_schedule = []
        self.app.grab_schedule = types.MethodType(lambda s: None, self.app)
        self.app.randomize_selection.isChecked = lambda: False

    def test_viewer_feeds_missing_files_as_rows(self):
        present = self._touch("keep.png")
        offline = "/mnt/usb/gone.png"
        self._prime_viewer_app([present, offline])

        with patch(
            "gesturesesh.app.selection.run_selection_order_dialog",
            return_value={"files": [present], "folders": [], "random_preview": False},
        ) as mock_dialog:
            self.app.open_selection_order_viewer()

        # The viewer received the loaded file AND the missing one (as a row).
        _, kwargs = mock_dialog.call_args
        self.assertEqual(kwargs["files"], [present, offline])

    def test_viewer_removing_missing_file_sticks(self):
        present = self._touch("keep.png")
        offline = "/mnt/usb/gone.png"  # offline drive -> merge would resurrect it
        self._prime_viewer_app([present, offline])

        # User removes the MISSING row and applies.
        with patch(
            "gesturesesh.app.selection.run_selection_order_dialog",
            return_value={"files": [present], "folders": [], "random_preview": False},
        ):
            self.app.open_selection_order_viewer()

        self.assertEqual(
            self.app.selection_sets["set1"], {"files": [present], "folders": []}
        )
        self.assertEqual(self.app.selection["files"], [present])

    def test_viewer_keeping_missing_file_preserves_in_set_not_live(self):
        present = self._touch("keep.png")
        offline = "/mnt/usb/later.png"
        self._prime_viewer_app([present, offline])

        # User keeps the MISSING row and applies.
        with patch(
            "gesturesesh.app.selection.run_selection_order_dialog",
            return_value={
                "files": [present, offline],
                "folders": [],
                "random_preview": False,
            },
        ):
            self.app.open_selection_order_viewer()

        # Kept in the preset for when the drive returns...
        self.assertEqual(
            self.app.selection_sets["set1"],
            {"files": [present, offline], "folders": []},
        )
        # ...but excluded from the live, loadable-only selection.
        self.assertEqual(self.app.selection["files"], [present])

    def test_viewer_preserves_stored_order_on_unchanged_apply(self):
        # Regression: missing entries must keep their stored position so an
        # unchanged Apply does not reorder the set (Codex P2).
        present = self._touch("present.png")
        missing = "/mnt/usb/missing.png"  # stored BEFORE the present file
        self._prime_viewer_app([missing, present])

        def echo(*a, **k):
            # Dialog echoes back exactly what it was shown (Apply, no edits).
            return {
                "files": list(k["files"]),
                "folders": list(k["folders"]),
                "random_preview": False,
            }

        with patch(
            "gesturesesh.app.selection.run_selection_order_dialog", side_effect=echo
        ) as mock_dialog:
            self.app.open_selection_order_viewer()

        # Missing item is reinserted at its stored position, not appended.
        self.assertEqual(mock_dialog.call_args.kwargs["files"], [missing, present])
        # Round trip preserves saved order instead of [present, missing].
        self.assertEqual(self.app.selection_sets["set1"]["files"], [missing, present])

    def test_viewer_keeps_invalid_existing_file_out_of_live(self):
        # Regression: an existing but unsupported saved path (e.g. an AppleDouble
        # sidecar) must not re-enter the live selection (Codex P2).
        present = self._touch("present.png")
        sidecar = self._touch("note.txt")  # exists, but unsupported extension

        self._prime_viewer_app([present, sidecar])

        def echo(*a, **k):
            return {
                "files": list(k["files"]),
                "folders": list(k["folders"]),
                "random_preview": False,
            }

        with patch(
            "gesturesesh.app.selection.run_selection_order_dialog", side_effect=echo
        ):
            self.app.open_selection_order_viewer()

        # Stored set keeps the user's full curated list...
        self.assertEqual(
            self.app.selection_sets["set1"]["files"], [present, sidecar]
        )
        # ...but the live selection excludes the unsupported file.
        self.assertEqual(self.app.selection["files"], [present])

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

    def test_on_preset_switch_ignores_unsaved_typed_name(self):
        # Save As: committing a brand-new (unsaved) name must NOT write the
        # current selection — intended for the new preset — back onto the
        # previously active preset (Codex P2). on_preset_switch is a no-op for
        # names that are not saved presets; save() adopts the name instead.
        self.app.presets = {"A": {"schedule": {}, "selection_id": "setA"}}
        self.app.selection_sets = {"setA": {"files": ["/a.png"], "folders": []}}
        self.app._active_set_preset = "A"
        # Selection diverged from A's set, intended for the new preset.
        self.app.selection = {"files": ["/new.png"], "folders": []}
        self.app.preset_loader_box.currentText = lambda: "BrandNew"

        self.app.on_preset_switch()

        # A's set is untouched and it stays active (save() will retarget it).
        self.assertEqual(
            self.app.selection_sets["setA"], {"files": ["/a.png"], "folders": []}
        )
        self.assertEqual(self.app._active_set_preset, "A")

    # -- deleting the active preset --------------------------------------------

    def test_delete_active_preset_applies_fallback_set(self):
        # Deleting the active preset must not leave its stale selection live to
        # be written onto the fallback preset's set (Codex P1). When the
        # fallback has a set, switch the live selection to it.
        b1 = self._touch("b1.png")
        self.app.presets = {
            "A": {"schedule": {}, "selection_id": "setA"},
            "B": {"schedule": {}, "selection_id": "setB"},
        }
        self.app.selection_sets = {
            "setA": {"files": ["/old-a.png"], "folders": []},
            "setB": {"files": [b1], "folders": []},
        }
        self.app._active_set_preset = "A"
        # Live selection still belongs to the about-to-be-deleted preset A.
        self.app.selection = {"files": ["/old-a.png"], "folders": []}
        self.app.preset_loader_box.currentText = MagicMock(side_effect=["A", "B"])
        self.app.preset_loader_box.currentIndex = MagicMock(return_value=0)

        self.app.delete()

        # Falls to B: active follows and B's set is applied to the selection.
        self.assertEqual(self.app._active_set_preset, "B")
        self.assertEqual(self.app.selection["files"], [b1])
        # A boundary write now stores B's own files, not A's stale ones.
        self.app.write_back_active_set()
        self.assertEqual(
            self.app.selection_sets["setB"], {"files": [b1], "folders": []}
        )

    def test_delete_active_preset_unlinked_fallback_drops_active(self):
        # Fallback preset has no set: drop the active link so the deleted
        # preset's stale selection can't be persisted onto it (Codex P1).
        self.app.presets = {
            "A": {"schedule": {}, "selection_id": "setA"},
            "B": {"schedule": {}},  # no linked set
        }
        self.app.selection_sets = {"setA": {"files": ["/old-a.png"], "folders": []}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/old-a.png"], "folders": []}
        self.app.preset_loader_box.currentText = MagicMock(side_effect=["A", "B"])
        self.app.preset_loader_box.currentIndex = MagicMock(return_value=0)

        self.app.delete()

        self.assertIsNone(self.app._active_set_preset)
        # The next boundary write is a no-op; B never adopts A's selection.
        self.app.write_back_active_set()
        self.assertNotIn("selection_id", self.app.presets["B"])
        self.assertEqual(self.app.selection_sets, {})

    def test_delete_only_preset_clears_active(self):
        # Deleting the last preset empties the combo -> no active preset.
        self.app.presets = {"A": {"schedule": {}, "selection_id": "setA"}}
        self.app.selection_sets = {"setA": {"files": ["/a.png"], "folders": []}}
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/a.png"], "folders": []}
        self.app.preset_loader_box.currentText = MagicMock(side_effect=["A", ""])
        self.app.preset_loader_box.currentIndex = MagicMock(return_value=0)

        self.app.delete()

        self.assertIsNone(self.app._active_set_preset)

    # -- editable preset switch (committed typed name) -------------------------

    def test_committing_typed_existing_preset_switches_set(self):
        # Regression: typing an existing preset name and committing it (Enter /
        # focus-out) must run the switch-in read via the real signal wiring, not
        # just load the schedule while the set stays on the old preset (Codex
        # P2). Uses a real editable combo so the production wiring is exercised.
        b1 = self._touch("b1.png")
        combo = QtWidgets.QComboBox()
        combo.setEditable(True)
        self.app.preset_loader_box = combo
        # load() is wired here too; stub it so it doesn't touch other widgets.
        self.app.load = types.MethodType(lambda s: None, self.app)
        self.app._connect_preset_loader_signals()

        self.app.presets = {
            "A": {"schedule": {}, "selection_id": "setA"},
            "B": {"schedule": {}, "selection_id": "setB"},
        }
        self.app.selection_sets = {
            "setA": {"files": ["/old.png"], "folders": []},
            "setB": {"files": [b1], "folders": []},
        }
        self.app._active_set_preset = "A"
        self.app.selection = {"files": ["/a-live.png"], "folders": []}
        combo.addItems(["A", "B"])

        # Type "B" into the line edit and commit it.
        combo.setEditText("B")
        combo.lineEdit().editingFinished.emit()

        self.assertEqual(self.app._active_set_preset, "B")
        self.assertEqual(self.app.selection["files"], [b1])


if __name__ == "__main__":
    unittest.main()
