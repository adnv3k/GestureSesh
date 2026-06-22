"""Per-preset image-set associations (phase 1: under-the-hood, no UI).

An *image set* is a named-by-id snapshot of the selection (``files`` + ``folders``)
that a preset can be linked to. The data model is normalized: presets hold a
``selection_id`` reference and the sets themselves live once in
``config["selection_sets"]`` keyed by a stable id, so multiple presets can share
one set without duplicating the file list.

Lifecycle rules (agreed design):

* **Read on switch-in** – when the user deliberately switches to a preset, its
  linked set is applied to the live selection (lazy validation + status report).
* **Write on boundaries** – the live selection is written back to the active
  preset's set only at clean boundaries (switching away, session start, app
  close, explicit save), never on every edit. Reads and writes are kept on
  separate triggers to avoid signal re-entrancy.
* **Copy-on-write** – editing the selection for a preset whose set is shared by
  another preset forks a new set for the current preset rather than mutating the
  shared one.
* **Garbage collection** – sets no longer referenced by any preset are culled
  (which is also why a still-linked set can never be dropped).
* **Offline safety** – when a set is applied while files are unavailable (e.g. an
  unplugged external drive), only the available files load, but the write-back
  preserves the unavailable ones instead of pruning them, so reconnecting the
  drive brings the set back intact. Reconnect recovery: switch to another preset
  and back to re-apply.
"""

from __future__ import annotations

import os
import uuid

from gesturesesh.utils.config import save_config


class MainAppSelectionSetsMixin:
    """Image-set association behavior mixed into ``MainApp``."""

    def init_selection_sets(self):
        """Initialize the in-memory store from config. Call after ``init_preset``."""
        sets = self.config.get("selection_sets", {})
        if not isinstance(sets, dict):
            sets = {}
        self.selection_sets = sets
        self.config["selection_sets"] = self.selection_sets
        # Name of the preset whose set the live selection currently represents.
        # ``None`` means there is no real preset to write back to (e.g. the
        # "Default" placeholder or an unsaved typed name).
        self._active_set_preset = None

    # -- helpers ---------------------------------------------------------------

    def _new_set_id(self) -> str:
        """Return a stable id not currently used by any set."""
        while True:
            set_id = uuid.uuid4().hex[:12]
            if set_id not in self.selection_sets:
                return set_id

    def _selection_snapshot(self) -> dict:
        """Snapshot the live selection (order preserved)."""
        return {
            "files": list(self.selection["files"]),
            "folders": list(self.selection["folders"]),
        }

    def _set_refcount(self, set_id: str) -> int:
        """How many presets reference *set_id*."""
        return sum(
            1
            for preset in self.presets.values()
            if isinstance(preset, dict) and preset.get("selection_id") == set_id
        )

    def _wrapped_preset(self, name: str) -> dict:
        """Return *name*'s preset in wrapped form, upgrading legacy entries."""
        preset = self.presets.get(name)
        if not isinstance(preset, dict) or "schedule" not in preset:
            preset = {"schedule": preset if isinstance(preset, dict) else {}}
            self.presets[name] = preset
        return preset

    @staticmethod
    def _is_offline(path: str) -> bool:
        """True when *path*'s file is gone *and* its directory is too.

        The heuristic distinguishes a disconnected drive / moved tree (the whole
        directory is missing -> preserve) from an in-place deletion (the folder
        still exists, the file was removed -> don't preserve). This keeps
        external-drive workflows intact: unplugging a drive removes its mount
        point, so every file under it reads as offline.
        """
        if os.path.isfile(path):
            return False
        parent = os.path.dirname(path) or os.sep
        return not os.path.isdir(parent)

    @staticmethod
    def _is_offline_dir(path: str) -> bool:
        """Folder variant of :meth:`_is_offline`."""
        if os.path.isdir(path):
            return False
        parent = os.path.dirname(path.rstrip(os.sep)) or os.sep
        return not os.path.isdir(parent)

    def _merge_unavailable(self, snapshot: dict, stored: dict) -> dict:
        """Reconcile the live selection with a stored set, preserving entries
        that are absent only because their drive/tree is disconnected.

        * No real edit (the live selection equals what the stored set currently
          resolves to on disk) -> return the stored set verbatim, so a
          disconnected drive never churns order or drops files.
        * Real edit -> honor the user's order/edits for the visible items, then
          re-append still-offline entries so they survive.
        """
        working_files = list(snapshot["files"])
        working_folders = list(snapshot["folders"])
        stored_files = list(stored.get("files", []))
        stored_folders = list(stored.get("folders", []))

        loadable_files = [f for f in stored_files if os.path.isfile(f)]
        loadable_folders = [d for d in stored_folders if os.path.isdir(d)]

        if working_files == loadable_files and working_folders == loadable_folders:
            return {"files": stored_files, "folders": stored_folders}

        working_fset = set(working_files)
        reserved_files = [
            f
            for f in stored_files
            if f not in working_fset and self._is_offline(f)
        ]
        working_dset = set(working_folders)
        reserved_folders = [
            d
            for d in stored_folders
            if d not in working_dset and self._is_offline_dir(d)
        ]
        return {
            "files": working_files + reserved_files,
            "folders": working_folders + reserved_folders,
        }

    def _gc_selection_sets(self) -> None:
        """Remove sets not referenced by any preset (orphans only)."""
        referenced = {
            preset.get("selection_id")
            for preset in self.presets.values()
            if isinstance(preset, dict) and preset.get("selection_id")
        }
        for set_id in list(self.selection_sets.keys()):
            if set_id not in referenced:
                del self.selection_sets[set_id]

    # -- read / write ----------------------------------------------------------

    def apply_selection_set(self, set_id: str) -> None:
        """Switch-in read: load *set_id* into the live selection.

        Lazy validation: paths are applied as-is, then the ones that no longer
        exist are dropped from the working selection and reported. A missing set
        id is a no-op so the current selection is left untouched.
        """
        data = self.selection_sets.get(set_id)
        if not data:
            return
        stored_files = list(data.get("files", []))
        stored_folders = list(data.get("folders", []))

        valid_files = self.check_files(stored_files)["valid_files"]
        valid_folders = [f for f in stored_folders if os.path.isdir(f)]

        self.selection["files"] = valid_files
        self.selection["folders"] = valid_folders

        missing = len(stored_files) - len(valid_files)
        if missing > 0:
            self.show_temporary_status(
                f"Loaded {len(valid_files)} of {len(stored_files)} images "
                f"— {missing} currently unavailable (kept in this preset).",
                4000,
            )
        self.display_status()

    def write_back_active_set(self) -> None:
        """Boundary write: persist the live selection to the active preset's set.

        Applies copy-on-write when the current set is shared, creates a set on
        first write, GCs orphans, and persists. A no-op when there is no real
        active preset or when nothing changed.
        """
        if getattr(self, "_loading", False):
            return
        name = self._active_set_preset
        if not name or name not in self.presets:
            return

        snapshot = self._selection_snapshot()
        preset = self._wrapped_preset(name)
        existing_id = preset.get("selection_id")

        if existing_id and existing_id in self.selection_sets:
            stored = self.selection_sets[existing_id]
            # Preserve entries missing only because their drive/tree is
            # disconnected; never let an offline drive prune the stored set.
            merged = self._merge_unavailable(snapshot, stored)
            if merged == stored:
                return  # no real change
            if self._set_refcount(existing_id) > 1:
                # shared + changed -> fork a new set for this preset
                new_id = self._new_set_id()
                self.selection_sets[new_id] = merged
                preset["selection_id"] = new_id
            else:
                self.selection_sets[existing_id] = merged
        else:
            # No link yet: only worth remembering if there is something to store.
            if not snapshot["files"] and not snapshot["folders"]:
                return
            new_id = self._new_set_id()
            self.selection_sets[new_id] = snapshot
            preset["selection_id"] = new_id

        self.config["presets"] = self.presets
        self._gc_selection_sets()
        self.config["selection_sets"] = self.selection_sets
        save_config(self.config_path, self.config)

    # -- switch handler --------------------------------------------------------

    def on_preset_switch(self, *args) -> None:
        """Deliberate user preset switch: write back the old set, apply the new.

        Wired to ``QComboBox.activated`` so it fires only on real user selection,
        not on programmatic index changes or text editing.
        """
        if getattr(self, "_loading", False):
            return
        new_name = self.preset_loader_box.currentText()
        if new_name == self._active_set_preset:
            return

        # Boundary write for the preset we are leaving (still the live selection).
        self.write_back_active_set()

        # Read for the preset we are entering.
        self._active_set_preset = new_name if new_name in self.presets else None
        if self._active_set_preset:
            preset = self.presets.get(new_name)
            set_id = (
                preset.get("selection_id") if isinstance(preset, dict) else None
            )
            if set_id:
                self.apply_selection_set(set_id)
            # No linked set -> leave the current selection; it becomes this
            # preset's set on the next boundary write.
