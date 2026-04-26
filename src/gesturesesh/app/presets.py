"""Schedule, totals, presets, and recent-session persistence for MainApp."""

from __future__ import annotations

import random

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem

from gesturesesh.session.constants import BREAK_IMAGE_PATH
from gesturesesh.utils.config import save_config
from gesturesesh.utils.time import format_seconds


class MainAppPresetsMixin:
    """Preset and schedule behavior mixed into ``MainApp``."""

    def load_recent(self):
        """Loads most recent session settings from unified config.json."""
        recent = self.config.get("recent_session", {})
        if not recent:
            return self.selected_items.clear()

        # Start from a clean selection so reloading recent state doesn't merge
        # with stale in-memory picks from the current app run.
        self.selection["files"] = []
        self.selection["folders"] = []

        folders = recent.get("folders", [])
        files = recent.get("files", [])
        loaded_any = False
        if folders:
            self.selection["folders"] = folders
            self.scan_directories(folders)
            loaded_any = True
        if files:
            checked = self.check_files(files)
            self.selection["files"].extend(
                file for file in checked["valid_files"] if file != BREAK_IMAGE_PATH
            )
            loaded_any = loaded_any or bool(checked["valid_files"])

        # Preserve order while dropping accidental duplicates.
        self.selection["files"] = list(dict.fromkeys(self.selection["files"]))

        if "recent_preset" in recent:
            self.preset_loader_box.setCurrentIndex(recent.get("recent_preset", 0))
            loaded_any = True
        if "randomized" in recent:
            self.randomize_selection.setChecked(recent.get("randomized", False))
            loaded_any = True

        self.remove_breaks()
        self.display_status()
        if loaded_any:
            self.show_temporary_status("Recent session settings loaded!", 3000)
        self.update_total()

    def append_schedule(self):
        """
        Adds entry information as a new row in the schedule.
        Resets scrollboxes to 0. Updates total amount.
        Prevents adding an entry if both minutes and seconds are 0.
        """
        minutes = self.set_minutes.value()
        seconds = self.set_seconds.value()
        if minutes == 0 and seconds == 0:
            self.show_error_status("Time must be greater than 0 seconds!", 3000)
            return

        row = self.entry_table.rowCount()
        entry = [
            row + 1,
            self.set_number_of_images.value(),
            minutes * 60 + seconds,
        ]
        self.set_number_of_images.setValue(0)
        self.set_minutes.setValue(0)
        self.set_seconds.setValue(0)
        self.entry_table.insertRow(row)

        for column, item in enumerate(entry):
            item = QTableWidgetItem(str(item))
            item.setTextAlignment(4)
            if column == 0:
                item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.entry_table.setItem(row, column, item)
        self.set_number_of_images.setFocus()
        self.set_number_of_images.selectAll()

    def remove_row(self):
        row = self.entry_table.currentRow()
        self.entry_table.removeRow(row)
        for i in range(row, self.entry_table.rowCount()):
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(4)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.entry_table.setItem(i, 0, item)
        if row != self.entry_table.rowCount():
            self.entry_table.setCurrentCell(row, 0)
        else:
            self.entry_table.setCurrentCell(row - 1, 0)
        self.update_total()

    def move_up(self):
        row = self.entry_table.currentRow()
        if row <= 0:
            return
        self.entry_table.setCurrentCell(row, 0)
        for column in range(self.entry_table.columnCount()):
            if column == 0:
                continue
            try:
                current, above = QTableWidgetItem(
                    self.entry_table.item(row, column).text()
                ), QTableWidgetItem(self.entry_table.item(row - 1, column).text())
            except (Exception, ValueError):
                self.show_error_status("Select a row in the table!", 2000)
                return
            current.setTextAlignment(4)
            above.setTextAlignment(4)
            self.entry_table.setItem(row, column, above)
            self.entry_table.setItem(row - 1, column, current)
        self.entry_table.setCurrentCell(row - 1, 0)

    def move_down(self):
        row = self.entry_table.currentRow()
        if row >= self.entry_table.rowCount() - 1:
            return
        self.entry_table.setCurrentCell(row, 0)
        for column in range(1, self.entry_table.columnCount()):
            try:
                current, below = QTableWidgetItem(
                    self.entry_table.item(row, column).text()
                ), QTableWidgetItem(self.entry_table.item(row + 1, column).text())
            except (Exception, ValueError):
                self.show_error_status("Select a row in the table!", 2000)
                return
            current.setTextAlignment(4)
            below.setTextAlignment(4)
            self.entry_table.setItem(row + 1, column, current)
            self.entry_table.setItem(row, column, below)
        self.entry_table.setCurrentCell(row + 1, 0)

    def remove_rows(self):
        """Clears the schedule of its entries."""
        for i in range(self.entry_table.rowCount()):
            self.entry_table.removeRow(0)

    def randomize_items(self):
        copy = self.selection["files"].copy()
        randomized_items = []
        while len(copy) > 0:
            random_index = random.randint(0, len(copy) - 1)
            randomized_items.append(copy.pop(random_index))
        self.selection["files"] = randomized_items
        self.display_status()

    def update_total(self):
        """
        Updates the total number of images and total time based on the entries
        in the entry_table. Iterates rows summing image and time columns; on
        invalid data prints debug info and aborts. Result is rendered in
        total_table.
        """
        rows = self.entry_table.rowCount()
        if (
            self.entry_table.item(rows - 1, 1) is None
            or self.entry_table.item(rows - 1, 2) is None
        ):
            return
        self.total_images = 0
        self.total_time = 0
        for row in range(rows):
            try:
                self.total_images += int(self.entry_table.item(row, 1).text())
            except (Exception, ValueError):
                print(f"BUG self.total_images could not be added from")
                print(f"row: {row}")
                print("item", self.entry_table.item(row, 1).text())
                print(f"{self.entry_table.row()} {self.entry_table.column()}")
                return
            try:
                if int(self.entry_table.item(row, 1).text()) > 0:
                    self.total_time += int(self.entry_table.item(row, 2).text()) * int(
                        self.entry_table.item(row, 1).text()
                    )
                else:
                    self.total_time += int(self.entry_table.item(row, 2).text())
            except (Exception, ValueError):
                print(f"BUG self.total_time could not be counted from")
                print(f"row: {row}")
                print("item", self.entry_table.item(row, 2).text())
                print(f"{self.entry_table.row()} {self.entry_table.column()}")
                return
        if self.total_table.rowCount() < 1:
            self.total_table.insertRow(0)
        total = QTableWidgetItem("Total")
        total.setTextAlignment(4)
        self.total_table.setItem(0, 0, total)
        total_images = QTableWidgetItem(str(self.total_images))
        total_images.setTextAlignment(4)
        self.total_table.setItem(0, 1, total_images)
        total_time = QTableWidgetItem(format_seconds(self.total_time))
        total_time.setTextAlignment(4)
        self.total_table.setItem(0, 2, total_time)

    def init_preset(self):
        self.presets = self.config.get("presets", {})
        self.update_presets()

    def update_presets(self):
        """Populates the configuration with preset."""
        if not self.presets:
            self.preset_loader_box.setCurrentText("Default")
            self.preset_names = ["Default"]
            return
        self.preset_loader_box.clear()
        self.preset_names = list(self.presets.keys())
        self.preset_loader_box.addItems(self.preset_names)
        self.update_total()

    def save(self, wait_status: bool = True):
        if self.entry_table.rowCount() <= 0:
            self.show_error_status("Cannot save an empty schedule!", 4000)
            return
        preset_name = self.preset_loader_box.currentText()
        if preset_name == "":
            self.show_error_status("Cannot save an empty name!", 5500)
            return
        schedule = {}
        for row in range(self.entry_table.rowCount()):
            schedule[row] = []
            for column in range(self.entry_table.columnCount()):
                schedule[row].append(self.entry_table.item(row, column).text())
        # Use the wrapped format so per-preset display settings (e.g.
        # toggle_resize_status) survive across schedule edits.
        existing = self.presets.get(preset_name)
        if isinstance(existing, dict) and "schedule" in existing:
            existing["schedule"] = schedule
            self.presets[preset_name] = existing
        else:
            self.presets[preset_name] = {"schedule": schedule}
        self.config["presets"] = self.presets
        if preset_name not in self.preset_names:
            self.update_presets()
            self.preset_loader_box.setCurrentIndex(self.preset_loader_box.count() - 1)
        if wait_status:
            self.show_temporary_status(f"{preset_name} saved!", 3000)
        save_config(self.config_path, self.config)

    def delete(self):
        preset_name = self.preset_loader_box.currentText()
        if preset_name == "":
            self.show_error_status("Cannot delete an empty field!", 4000)
            return
        if preset_name in self.presets:
            del self.presets[preset_name]
            self.config["presets"] = self.presets
            save_config(self.config_path, self.config)
        self.show_temporary_status(f"{preset_name} deleted!", 2000)
        self.preset_loader_box.removeItem(self.preset_loader_box.currentIndex())

    def load(self):
        preset_name = self.preset_loader_box.currentText()
        preset = self.presets.get(preset_name)
        if preset:
            self.remove_rows()
            # Handle both legacy preset format (schedule dict) and
            # newer wrapped format {"schedule": {...}, "selection": {...}}
            if isinstance(preset, dict) and "schedule" in preset:
                schedule = preset.get("schedule", {})
            else:
                schedule = preset

            try:
                for row_idx, row_data in sorted(
                    schedule.items(), key=lambda x: int(x[0])
                ):
                    row = self.entry_table.rowCount()
                    self.entry_table.insertRow(row)
                    for column, value in enumerate(row_data):
                        item = QTableWidgetItem(str(value))
                        item.setTextAlignment(4)
                        if column == 0:
                            item.setFlags(QtCore.Qt.ItemIsEnabled)
                        self.entry_table.setItem(row, column, item)
            except Exception as e:
                self.show_error_status(f"Error loading preset: {e}", 4000)
