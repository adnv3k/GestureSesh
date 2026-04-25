"""Session launch/orchestration behavior for MainApp."""

from __future__ import annotations

import os
import importlib
from pathlib import Path

from PyQt5.QtTest import QTest

from gesturesesh.app.models import ScheduleEntry
from gesturesesh.session_window import BREAK_IMAGE_PATH


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
        main_module = importlib.import_module("gesturesesh.main")

        # Pass any saved recent session settings into the display so initial
        # state matches the user's last-used preferences.
        try:
            session_settings = self.config.get("recent_session", {}).get(
                "session_settings", None
            )
        except Exception:
            session_settings = None

        self.display = main_module.SessionDisplay(
            schedule=self.session_schedule,
            items=self.selection["files"],
            total=self.total_scheduled_images,
            settings=session_settings,
        )
        self.display.closed.connect(self.session_closed)
        self.display.show()

    def session_closed(self):
        """Removes breaks, and displays status"""
        self.remove_breaks()
        self.display_status()
        self.activateWindow()
        self.raise_()
        self.show_temporary_status("Recent session settings saved!", 3000)

    def is_valid_session(self):
        """
        Checks if all files exist, and
        if there are enough images for the schedule.

        """
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
                    f"Has the location or file name been changed?"
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
        """Inserts break images as specified by the schedule"""
        if self.has_break:
            current_index = 0
            for entry in self.session_schedule:
                if entry.images == 0:
                    self.selection["files"].insert(current_index, BREAK_IMAGE_PATH)
                    current_index += 1
                else:
                    current_index += entry.images

    def remove_breaks(self):
        """
        Removes all occurrences of 'break.png' from the list of selected files.

        Iterates through the 'files' list in reverse order and removes any file whose
        basename is 'break.png'. This prevents issues with changing list indices during removal.

        Returns:
            None
        """
        i = len(self.selection["files"])
        while i > 0:
            i -= 1
            if self.selection["files"][i] == BREAK_IMAGE_PATH:
                self.selection["files"].pop(i)

    def grab_schedule(self):
        """Builds self.session_schedule with data from the schedule"""
        self.session_schedule = []
        for row in range(self.entry_table.rowCount()):
            images = int(self.entry_table.item(row, 1).text())
            time = int(self.entry_table.item(row, 2).text())
            if images == 0:
                self.has_break = True
            self.session_schedule.append(ScheduleEntry(images, time))

    def save_to_recent(self):
        """
        Saves current session settings into unified config.json.
        """
        main_module = importlib.import_module("gesturesesh.main")

        files_to_save = [
            file_path
            for file_path in self.selection["files"]
            if file_path != BREAK_IMAGE_PATH
        ]
        previous = self.config.get("recent_session") or {}
        recent = {
            "folders": list(self.selection["folders"]),
            "files": list(files_to_save),
            "recent_preset": self.preset_loader_box.currentIndex(),
            "randomized": self.randomize_selection.isChecked(),
        }
        # Preserve display preferences across runs; session_closed() refreshes
        # them when the session window is closed.
        if "session_settings" in previous:
            recent["session_settings"] = previous["session_settings"]
        self.config["recent_session"] = recent
        main_module.save_config(self.config_path, self.config)
