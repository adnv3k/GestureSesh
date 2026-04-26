"""Session launch/orchestration behavior for MainApp."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtTest import QTest

from gesturesesh.app.models import ScheduleEntry
from gesturesesh.session.constants import BREAK_IMAGE_PATH
from gesturesesh.session_window import SessionDisplay
from gesturesesh.utils.config import save_config


class MainAppSessionMixin:
    """Session orchestration behavior mixed into ``MainApp``."""

    def start_session(self):
        """
        Grabs schedule, checks for valid session, checks for empty schedule,
        grabs randomization setting, save 'recent', insert break.png,
        shows session window
        self.selection['files'] => images to display
        self.session_schedule => schedule

        """
        self.grab_schedule()
        if not self.is_valid_session():
            print("Invalid session")
            QTest.qWait(4000)
            self.display_status()
            return
        if self.randomize_selection.isChecked():
            self.randomize_items()
        self.save_to_recent()

        self.save(wait_status=False)

        self.insert_breaks()
        # Pass recent session settings (if any) into the SessionDisplay so
        # initial display state (resize, grayscale, zoom, etc.) is preserved.
        session_settings = None
        try:
            session_settings = self.config.get("recent_session", {}).get(
                "session_settings", None
            )
        except Exception:
            session_settings = None

        # toggle_resize_status is persisted per-preset rather than shared across
        # all sessions, so override the global value with the active preset's
        # value when present.
        try:
            preset_name = self.preset_loader_box.currentText()
            preset = self.presets.get(preset_name)
            if isinstance(preset, dict) and "session_settings" in preset:
                preset_settings = preset.get("session_settings") or {}
                if "toggle_resize_status" in preset_settings:
                    session_settings = dict(session_settings or {})
                    session_settings["toggle_resize_status"] = bool(
                        preset_settings.get("toggle_resize_status")
                    )
        except Exception:
            pass

        self.display = SessionDisplay(
            schedule=self.session_schedule,
            items=self.selection["files"],
            total=self.total_scheduled_images,
            settings=session_settings,
        )
        self.display.closed.connect(self.session_closed)
        self.display.show()

    def session_closed(self):
        """Removes breaks, displays status, and persists display preferences."""
        self.remove_breaks()
        self.display_status()
        self.activateWindow()
        self.raise_()
        # Persist a compact snapshot of display-related toggles so subsequent
        # sessions can restore the user's preferences (zoom, resize, grayscale,
        # frameless, etc.). Stored under 'recent_session' -> 'session_settings'.
        try:
            if hasattr(self, "display") and self.display is not None:
                ds = self.display
                ss = {}
                try:
                    ss["zoom_enabled"] = bool(getattr(ds, "zoom_enabled", False))
                except Exception:
                    ss["zoom_enabled"] = False
                try:
                    ss["reset_zoom_between_images"] = bool(
                        getattr(ds, "reset_zoom_between_images", True)
                    )
                except Exception:
                    ss["reset_zoom_between_images"] = True
                try:
                    ss["default_zoom"] = float(getattr(ds, "default_zoom_factor", 1.0))
                except Exception:
                    ss["default_zoom"] = 1.0
                try:
                    imgmods = getattr(ds, "image_mods", {}) or {}
                    ss["grayscale"] = bool(imgmods.get("grayscale", False))
                    ss["grayscale_mode"] = imgmods.get(
                        "grayscale_mode", imgmods.get("grayscale_mode", "perceptual")
                    )
                    ss["hflip"] = bool(imgmods.get("hflip", False))
                    ss["vflip"] = bool(imgmods.get("vflip", False))
                    try:
                        ss["brightness"] = int(imgmods.get("brightness", 0))
                    except Exception:
                        ss["brightness"] = 0
                    try:
                        ss["contrast"] = float(imgmods.get("contrast", 1.0))
                    except Exception:
                        ss["contrast"] = 1.0
                    ss["threshold"] = bool(imgmods.get("threshold", False))
                    ss["edge"] = bool(imgmods.get("edge", False))
                except Exception:
                    ss["grayscale"] = False
                    ss["grayscale_mode"] = "perceptual"
                try:
                    ss["toggle_resize_status"] = bool(
                        getattr(ds, "toggle_resize_status", False)
                    )
                except Exception:
                    ss["toggle_resize_status"] = False
                try:
                    ss["frameless_status"] = bool(getattr(ds, "frameless_status", False))
                except Exception:
                    ss["frameless_status"] = False
                try:
                    ss["always_on_top"] = bool(
                        getattr(ds, "toggle_always_on_top_status", False)
                    )
                except Exception:
                    ss["always_on_top"] = False

                recent = self.config.get("recent_session", {})
                recent["session_settings"] = ss
                self.config["recent_session"] = recent

                # Persist toggle_resize_status onto the active preset so each
                # preset keeps its own resize configuration rather than
                # inheriting the last session's value.
                try:
                    preset_name = self.preset_loader_box.currentText()
                    if preset_name and preset_name in self.presets:
                        preset = self.presets[preset_name]
                        if not (isinstance(preset, dict) and "schedule" in preset):
                            preset = {"schedule": preset}
                        preset_settings = preset.get("session_settings") or {}
                        preset_settings["toggle_resize_status"] = ss[
                            "toggle_resize_status"
                        ]
                        preset["session_settings"] = preset_settings
                        self.presets[preset_name] = preset
                        self.config["presets"] = self.presets
                except Exception:
                    pass

                save_config(self.config_path, self.config)
        except Exception:
            pass

        self.show_temporary_status("Recent session settings saved!", 3000)

    def is_valid_session(self):
        """Checks if all files exist and there are enough images for the schedule."""
        for row in range(self.entry_table.rowCount()):
            items = []
            try:
                for i in range(2):
                    items.append(int(self.entry_table.item(row, i + 1).text()))
            except (Exception, ValueError):
                self.show_error_status("Schedule items must be numbers!")
                return False

        if len(self.session_schedule) == 0:
            self.show_error_status("Schedule cannot be empty.")
            return False
        self.total_scheduled_images = 0
        for entry in self.session_schedule:
            self.total_scheduled_images += entry.images

        for file in self.selection["files"]:
            file_path = Path(file)
            if not file_path.is_file():
                self.selection["files"].remove(file)
                self.selected_items.setText(f"{os.path.basename(file)} not found!")
                self.selected_items.append(
                    "Has the location or file name been changed?"
                )
                self.selected_items.append(
                    "Image removed from selection."
                    f' {len(self.selection["files"])} total files.'
                )
                self.selected_items.append(
                    f"Previous directory: \n{os.path.dirname(file)}"
                )
                return False

        if self.total_scheduled_images > len(self.selection["files"]):
            self.show_error_status(
                "Not enough images selected. Add more images, or schedule fewer"
                " images.",
                7000,
            )
            return False
        return True

    def insert_breaks(self):
        """Inserts break images as specified by the schedule."""
        if self.has_break:
            current_index = 0
            for entry in self.session_schedule:
                if entry.images == 0:
                    self.selection["files"].insert(current_index, BREAK_IMAGE_PATH)
                    current_index += 1
                else:
                    current_index += entry.images

    def remove_breaks(self):
        """Removes all occurrences of break.png from the list of selected files."""
        i = len(self.selection["files"])
        while i > 0:
            i -= 1
            if self.selection["files"][i] == BREAK_IMAGE_PATH:
                self.selection["files"].pop(i)

    def grab_schedule(self):
        """Builds self.session_schedule with data from the schedule."""
        self.session_schedule = []
        for row in range(self.entry_table.rowCount()):
            images = int(self.entry_table.item(row, 1).text())
            time = int(self.entry_table.item(row, 2).text())
            if images == 0:
                self.has_break = True
            self.session_schedule.append(ScheduleEntry(images, time))

    def save_to_recent(self):
        """Saves current session settings into unified config.json."""
        previous = self.config.get("recent_session") or {}
        recent = {
            "folders": list(self.selection["folders"]),
            "files": list(self.selection["files"]),
            "recent_preset": self.preset_loader_box.currentIndex(),
            "randomized": self.randomize_selection.isChecked(),
        }
        # Preserve display preferences (resize, frameless, zoom, grayscale, etc.)
        # so they survive across new sessions. They are refreshed on session
        # close in session_closed().
        if "session_settings" in previous:
            recent["session_settings"] = previous["session_settings"]
        self.config["recent_session"] = recent
        save_config(self.config_path, self.config)
