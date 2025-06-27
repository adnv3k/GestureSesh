# GestureSesh.py
import os
import sys
import random
import platform
from pathlib import Path
from dataclasses import dataclass
from importlib import resources

import cv2
import numpy as np
from pygame import mixer

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import (
    QApplication,
    QShortcut,
    QFileDialog,
    QTableWidgetItem,
    QListView,
    QTreeView,
    QAbstractItemView,
    QWidget,
    QMainWindow,
    QGraphicsOpacityEffect,
    QProgressBar,
)
from PyQt5.QtCore import (
    QPropertyAnimation,
    QEasingCurve,
    QSequentialAnimationGroup,
    pyqtProperty,
)
from check_update import UpdateChecker, save_config, load_config, get_config_dir
from main_window import Ui_MainWindow
from session_display import Ui_session_display

import resources_config  # This is a generated file from resources.qrc DO NOT REMOVE


def sound_file(name: str):
    """Return a context manager yielding the path to an embedded sound file."""
    return resources.as_file(resources.files("sounds") / name)


from dot_indicator import DotIndicator


@dataclass
class ScheduleEntry:
    images: int
    time: int


@dataclass
class StatusMessage:
    text: str
    duration: int  # milliseconds
    is_error: bool = False
    timer: QtCore.QTimer | None = None
    blink_timer: QtCore.QTimer | None = None
    fade_timer: QtCore.QTimer | None = None
    is_blinking: bool = False
    fade_step: int = 0
    _blink_cycle_count: int = 0
    _current_fade_step: int = 0
    _fade_direction: str = "out"
    _max_blink_cycles: int = 0
    _fade_steps: int = 0
    _is_fading_out: bool = False


# Subclass to enable multifolder selection.
class FileDialog(QFileDialog):
    def __init__(self):
        super(FileDialog, self).__init__()
        self.setOption(QFileDialog.DontUseNativeDialog, True)
        self.setFileMode(QFileDialog.Directory)
        self.setOption(QFileDialog.ShowDirsOnly, True)
        self.findChildren(QListView)[0].setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.findChildren(QTreeView)[0].setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )


__version__ = "0.5.0"


class MainApp(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle(f"Reference Practice")
        self.config = load_config(self)
        self.session_schedule = []
        self.has_break = False
        self.valid_file_types = {".bmp", ".jpg", ".jpeg", ".png"}
        # Initialize selection before loading recent session
        self.selection = {"files": [], "folders": []}

        # Initialize enhanced status message system
        self.status_timer = QtCore.QTimer()
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.display_status)

        # Status message queue and animation system
        self.status_messages = []  # Queue of active status messages
        self.current_animation_group = None
        self.showing_default_status = True

        # Debounce timer for status updates to prevent UI freezing
        self.status_update_timer = QtCore.QTimer()
        self.status_update_timer.setSingleShot(True)
        self.status_update_timer.timeout.connect(self._update_status_display_text)

        # Setup opacity effect for selected_items
        self.status_opacity_effect = QGraphicsOpacityEffect()
        self.selected_items.setGraphicsEffect(self.status_opacity_effect)

        self.init_buttons()
        self.init_shortcuts()
        self.init_preset()
        self.load_recent()
        self.check_version()
        self.entry_table.itemChanged.connect(self.update_total)
        self.dialog_buttons.accepted.connect(self.start_session)
        # Add: Initial dynamic font sizing
        self.update_dynamic_fonts()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_dynamic_fonts()

    def update_dynamic_fonts(self):
        """Dynamically update font sizes based on window height."""
        base_height = self.height()
        # Calculate font size as a percentage of window height (tweak as needed)
        font_size = max(10, int(base_height * 0.0230))  # Minimum 10pt
        # font_size = max(10, int(base_height * 0.0225))  # Minimum 10pt
        large_font_size = max(14, int(base_height * 0.0325))
        # Main font
        font = QtGui.QFont("Apple SD Gothic Neo", font_size, QtGui.QFont.Bold)
        # Large font for headers
        large_font = QtGui.QFont(
            "Apple SD Gothic Neo", large_font_size, QtGui.QFont.Bold
        )
        # Apply to key widgets
        self.select_images.setFont(large_font)
        self.session_settings.setFont(large_font)
        self.label_7.setFont(font)
        self.label_5.setFont(font)
        self.label_6.setFont(font)
        self.image_amount_label.setFont(font)
        self.duration_label.setFont(font)
        self.label_8.setFont(font)
        self.add_folder.setFont(font)
        self.add_items.setFont(font)
        self.clear_items.setFont(font)
        self.randomize_selection.setFont(font)
        self.remove_duplicates.setFont(font)
        self.add_entry.setFont(font)
        self.preset_loader_box.setFont(font)
        self.save_preset.setFont(font)
        self.delete_preset.setFont(font)
        self.entry_table.setFont(font)
        self.total_table.setFont(font)
        self.remove_entry.setFont(font)
        self.move_entry_up.setFont(font)
        self.move_entry_down.setFont(font)
        self.reset_table.setFont(font)
        self.dialog_buttons.setFont(font)
        self.selected_items.setFont(font)
        self.set_number_of_images.setFont(font)
        self.set_minutes.setFont(font)
        self.set_seconds.setFont(font)

    def init_buttons(self):
        # Buttons for selection
        self.add_folder.clicked.connect(self.open_folder)
        self.clear_items.clicked.connect(self.remove_items)
        self.randomize_selection.clicked.connect(self.display_random_status)
        self.remove_duplicates.clicked.connect(self.remove_dupes)
        # Buttons for preset
        self.add_entry.clicked.connect(self.append_schedule)
        self.save_preset.clicked.connect(self.save)
        self.delete_preset.clicked.connect(self.delete)
        self.preset_loader_box.currentIndexChanged.connect(self.load)
        self.preset_loader_box.currentTextChanged.connect(self.load)
        # Buttons for table
        self.remove_entry.pressed.connect(self.remove_row)
        self.move_entry_up.clicked.connect(self.move_up)
        self.move_entry_down.clicked.connect(self.move_down)
        self.reset_table.clicked.connect(self.remove_rows)

    def init_shortcuts(self):
        # Ctrl+Enter to start session
        self.return_shortcut = QShortcut(QtGui.QKeySequence("Ctrl+Return"), self)
        self.return_shortcut.activated.connect(self.start_session)
        self.enter_shortcut = QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self)
        self.enter_shortcut.activated.connect(self.start_session)
        # Add entry
        self.add_shortcut = QShortcut(QtGui.QKeySequence("Shift+Return"), self)
        self.add_shortcut.activated.connect(self.append_schedule)
        self.add_shortcut = QShortcut(QtGui.QKeySequence("Shift+Enter"), self)
        self.add_shortcut.activated.connect(self.append_schedule)
        # Delete entry
        self.remove_shortcut = QShortcut(QtGui.QKeySequence("Delete"), self)
        self.remove_shortcut.activated.connect(self.remove_row)
        # Escape to close window
        self.escape_shortcut = QShortcut(QtGui.QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.close)

    # region
    # Functions for user input
    # region
    # Select Items
    def open_files(self):
        selected_files = QFileDialog().getOpenFileNames()
        checked_files = self.check_files(selected_files[0])
        self.selection["files"].extend(checked_files["valid_files"])

        self.selection["files"].extend(checked_files["valid_files"])

        # Use new status system for file adding messages
        self.show_temporary_status(
            f'{len(checked_files["valid_files"])} file(s) added!', 4000
        )

        if len(checked_files["invalid_files"]) > 0:
            self.show_temporary_status(
                f'{len(checked_files["invalid_files"])} file(s) not added. '
                f'Supported file types: {", ".join(self.valid_file_types)}.',
                duration_ms=4000,
                is_error=True,
            )

    def open_folder(self):
        """
        Calls on self.check_files to check each file in the user selected directories
        Saves folder paths, and file names
        Displays message of result

        """
        # Subclassed QFileDialog
        selected_dir = FileDialog()
        if selected_dir.exec():
            # Get all selected folders (supporting multi-selection)
            directories = selected_dir.selectedFiles()
            total_valid_files, total_invalid_files = self.scan_directories(directories)

            # Use new status system for folder adding messages
            self.show_temporary_status(
                f"{total_valid_files} file(s) added from {len(directories)} folder(s)!",
                4000,
            )

            if total_invalid_files > 0:
                self.show_temporary_status(
                    f"{total_invalid_files} file(s) not added. "
                    f'Supported file types: {", ".join(self.valid_file_types)}.',
                    duration_ms=4000,
                    is_error=True,
                )
            return

        # No folders selected
        self.show_temporary_status("0 folder(s) added!", 2000)

    def scan_directories(self, directories):
        """Scan a list of directories and collect valid files from all subfolders, robust to symlinks, permissions, and case."""
        total_valid_files, total_invalid_files = 0, 0
        visited = set()
        seen_paths = set()

        # Normalize allowed directories for safety check
        allowed_dirs = [os.path.abspath(d) for d in directories]

        # def is_within_allowed_dirs(path, allowed_dirs):
        #     abs_path = os.path.abspath(path)
        #     for folder in allowed_dirs:
        #         if abs_path.startswith(folder + os.sep):
        #             return True
        #     return False
        def is_within_allowed_dirs(path, allowed_dirs):
            abs_path = os.path.abspath(path)
            # Case-sensitive path comparison
            return any(
                abs_path.startswith(folder + os.sep) or abs_path == folder
                for folder in allowed_dirs
            )

        for directory in directories:
            if not os.path.exists(directory):
                if directory in self.selection["folders"]:
                    self.selection["folders"].remove(directory)
                continue
            # Save folder that was explicitly selected
            if directory not in self.selection["folders"]:
                self.selection["folders"].append(directory)
            for root, dirs, files in os.walk(directory, followlinks=True):
                # Prevent infinite recursion via symlinks
                try:
                    stat = os.stat(root)
                    key = (stat.st_dev, stat.st_ino)
                    if key not in visited:
                        visited.add(key)
                except OSError:
                    continue  # Skip directories we can't stat

                # Check files for type and accessibility first
                potential_files = self.check_files(
                    [os.path.join(root, f) for f in files]
                )
                total_invalid_files += len(
                    potential_files["invalid_files"]
                )  # Add initial invalid files

                for file in potential_files["valid_files"]:
                    try:
                        # Use inode + case-sensitive path for duplicate detection
                        stat = os.stat(file)
                        file_key = (stat.st_dev, stat.st_ino, file)  # Added file path

                        if file_key in seen_paths:
                            continue

                        if not is_within_allowed_dirs(file, allowed_dirs):
                            total_invalid_files += 1
                            continue

                        seen_paths.add(file_key)
                        self.selection["files"].append(file)
                        total_valid_files += 1

                    except (OSError, PermissionError):
                        total_invalid_files += 1
                        continue

        return total_valid_files, total_invalid_files
        #         # Now, filter the potentially valid files
        #         for file in potential_files['valid_files']:
        #             norm_path = os.path.abspath(file)

        #             # Perform all rejection checks first
        #             if norm_path in seen_paths:
        #                 continue # Skip duplicate

        #             if not is_within_allowed_dirs(file, allowed_dirs):
        #                 total_invalid_files += 1 # This file is ultimately invalid
        #                 continue # Skip files outside allowed dirs

        #             # If all checks pass, it's a confirmed valid file
        #             seen_paths.add(norm_path)
        #             self.selection['files'].append(file)
        #             total_valid_files += 1 # Increment valid count here
        # return total_valid_files, total_invalid_files

    def check_files(self, files):
        """Checks if files are supported file types and are accessible."""
        res = {"valid_files": [], "invalid_files": []}
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in self.valid_file_types:
                res["invalid_files"].append(file)
                continue
            # Only check file accessibility, not by opening
            if os.path.isfile(file):
                res["valid_files"].append(file)
            else:
                res["invalid_files"].append(file)
        return res

    def remove_items(self):
        """Clears entire selection"""
        self.selection["files"].clear()
        self.selection["folders"].clear()
        self.show_temporary_status("All files and folders cleared!", 2000)

    def remove_dupes(self):
        """Remove duplicate files from selection (case-sensitive)"""
        if not self.selection["files"]:
            self.show_temporary_status("No files to check for duplicates")
            return

        original_count = len(self.selection["files"])
        seen_files = set()
        unique_files = []

        for file_path in self.selection["files"]:
            try:
                # Use inode + case-sensitive path for duplicate detection
                stat = os.stat(file_path)
                file_key = (stat.st_dev, stat.st_ino, file_path)

                if file_key not in seen_files:
                    seen_files.add(file_key)
                    unique_files.append(file_path)
            except (OSError, PermissionError):
                # If we can't stat the file, keep it in the list
                unique_files.append(file_path)

        self.selection["files"] = unique_files
        removed_count = original_count - len(unique_files)

        if removed_count > 0:
            self.show_temporary_status(f"Removed {removed_count} duplicate file(s)")
        else:
            self.show_temporary_status("No duplicates found")

        self.display_status()

    def display_status(self):
        """Displays amount of files, and folders selected"""
        default_message = (
            f'{len(self.selection["files"])} total files added from '
            f'{len(self.selection["folders"])} folder(s).'
        )

        # If there are no active status messages, show default message directly
        if not self.status_messages:
            if (
                self.showing_default_status
                and self.selected_items.toPlainText() == default_message
            ):
                return  # Already showing this default message

            # Restore full opacity for default message
            self.status_opacity_effect.setOpacity(0.8)

            # Style default message to prevent white flash
            self.selected_items.setHtml(f"<div>{default_message}</div>")
            # Mark as showing default status
            self.showing_default_status = True

    def show_temporary_status(self, message, duration_ms=2000, is_error=False):
        """Shows a temporary status message with sophisticated animations"""
        self._add_status_message(message, duration_ms, is_error)

    def show_error_status(self, message, duration_ms=3000):
        """Shows an error/warning status message with faster, more attention-grabbing animations"""
        self._add_status_message(message, duration_ms, is_error=True)

    def _remove_status_message(self, status_msg):
        """Start fade‑out animation and remove a status message after its timer expires."""
        # If a fade‑out is already running for this message, do nothing.
        if getattr(status_msg, "_is_fading_out", False):
            return

        status_msg._is_fading_out = True  # Mark so we don't start two fades.

        # Stop and delete the timer that originally triggered removal.
        status_msg.timer.stop()
        status_msg.timer.deleteLater()

        # Begin a smooth fade‑out; the message will be dropped at the end.
        self._fade_out_and_remove(status_msg)

    def _fade_out_and_remove(self, status_msg):
        """Fade a status message out smoothly, then remove it from the queue."""
        fade_steps = 20
        fade_duration = 400  # milliseconds
        start_opacity = 0.6  # Begin fade‑out at dim opacity to avoid white flash
        step_duration = fade_duration // fade_steps

        status_msg._fade_step = 0

        fade_timer = QtCore.QTimer()
        fade_timer.setSingleShot(False)

        def _step():
            # Compute opacity: 1.0 ➜ 0.0 over `fade_steps`.

            progress = status_msg._fade_step / fade_steps
            opacity = start_opacity * (1 - progress)
            self._update_display_with_selective_opacity(status_msg, opacity)

            status_msg._fade_step += 1
            if status_msg._fade_step > fade_steps:
                # End of fade: clean up and finally drop the message.
                fade_timer.stop()
                fade_timer.deleteLater()
                if status_msg in self.status_messages:
                    self.status_messages.remove(status_msg)
                self._update_status_display()

        fade_timer.timeout.connect(_step)
        fade_timer.start(step_duration)
        status_msg._fade_timer = fade_timer  # keep a reference

    def _add_status_message(self, message, duration_ms, is_error=False):
        """Add a new status message to the queue and display it"""
        # Create timer for this message
        message_timer = QtCore.QTimer()
        message_timer.setSingleShot(True)

        # Create status message object
        status_msg = StatusMessage(message, duration_ms, is_error)
        status_msg.timer = message_timer

        # Connect timer to removal function
        message_timer.timeout.connect(lambda: self._remove_status_message(status_msg))

        # Stop any existing blinking animations before adding new message
        for existing_msg in self.status_messages:
            try:
                existing_msg.is_blinking = False
            except Exception as e:
                print(f"Exception while setting is_blinking: {e}")
                pass  # Handle case where is_blinking attribute doesn't exist
            try:
                existing_msg._blink_timer.stop()
            except Exception as e:
                print(f"Exception while stopping blink timer: {e}")
                pass

        # Add to queue (newest messages at the end, so they appear at top when reversed)
        self.status_messages.append(status_msg)

        # Update display immediately
        self._update_status_display_text()

        # Start blinking animation for this specific new message only
        self._start_message_blink_animation(status_msg, is_error)

        message_timer.start(7000)

    def _debounced_update_status_display(self):
        """Debounce status display updates to prevent UI freezing"""
        self.status_update_timer.start(50)  # single‑shot; restart is safe

    def _update_status_display(self):
        """Update the status display with current messages"""
        if self.status_messages:
            self._debounced_update_status_display()
        else:
            # No status messages, show default
            self.display_status()

    def _start_message_blink_animation(self, status_msg, is_error=False):
        """Start blinking animation for a specific message"""
        # Mark this message as blinking
        status_msg.is_blinking = True

        # Animation parameters
        max_blink_cycles = 3 if is_error else 2
        fade_duration = 300 if is_error else 400
        fade_steps = 20
        fade_step_duration = fade_duration // fade_steps

        # Store animation state in the message object
        status_msg._blink_cycle_count = 0
        status_msg._current_fade_step = 0
        status_msg._fade_direction = "out"
        status_msg._max_blink_cycles = max_blink_cycles
        status_msg._fade_steps = fade_steps

        # Create timer for this specific message's animation
        blink_timer = QtCore.QTimer()
        blink_timer.setSingleShot(False)

        status_msg._blink_timer = blink_timer

        def animate_message_fade():
            if not status_msg.is_blinking or status_msg not in self.status_messages:
                blink_timer.stop()
                blink_timer.deleteLater()
                return

            # Calculate current opacity
            if status_msg._fade_direction == "out":
                progress = status_msg._current_fade_step / status_msg._fade_steps
                current_opacity = 1.0 - (0.8 * progress)  # 1.0 -> 0.2
            else:  # fade_direction == 'in'
                progress = status_msg._current_fade_step / status_msg._fade_steps
                current_opacity = 0.2 + (0.8 * progress)  # 0.2 -> 1.0

            # Update display with selective opacity for this message
            self._update_display_with_selective_opacity(status_msg, current_opacity)

            status_msg._current_fade_step += 1

            # Check if this fade direction is complete
            if status_msg._current_fade_step >= status_msg._fade_steps:
                if status_msg._fade_direction == "out":
                    status_msg._fade_direction = "in"
                    status_msg._current_fade_step = 0
                else:
                    # Fade in complete, cycle is done
                    status_msg._blink_cycle_count += 1

                    if status_msg._blink_cycle_count < status_msg._max_blink_cycles:
                        # Brief pause between cycles, then start next cycle
                        blink_timer.stop()

                        def restart_cycle():
                            if (
                                status_msg.is_blinking
                                and status_msg in self.status_messages
                            ):
                                status_msg._current_fade_step = 0
                                status_msg._fade_direction = "out"
                                blink_timer.start(fade_step_duration)

                        QtCore.QTimer.singleShot(200, restart_cycle)
                        return
                    else:
                        # All cycles complete
                        self._finish_message_blink_animation(status_msg)
                        blink_timer.stop()
                        blink_timer.deleteLater()
                        return

        blink_timer.timeout.connect(animate_message_fade)
        blink_timer.start(fade_step_duration)

    def _finish_message_blink_animation(self, status_msg):
        """Restore normal state for a specific message after blinking completes"""
        status_msg.is_blinking = False
        if hasattr(status_msg, "_blink_timer"):
            delattr(status_msg, "_blink_timer")

        # Restore the main widget's opacity to full
        self.status_opacity_effect.setOpacity(1.0)

        # Update the display to show the final, non-transparent state
        self._update_status_display_text()

    # --- unified renderer --------------------------------------------------
    def _render_status(
        self, highlight: StatusMessage | None = None, opacity: float | None = None
    ) -> None:
        """
        Draw all status messages.  If *highlight* is supplied, that message is
        rendered in the given *opacity* (0‑1).  All others use full colour.
        """
        if not self.status_messages:
            self.display_status()
            return

        # Always show widget fully – we tint via text colour.
        self.status_opacity_effect.setOpacity(1.0)

        html = ['<div style="line-height:1.1;">']
        visible = list(reversed(self.status_messages))  # newest first
        for i, msg in enumerate(visible):
            margin = "margin-top:3px;" if i else ""

            if msg is highlight:
                base_rgb = "220, 20, 60" if msg.is_error else "225, 225, 225"
                css = f"font-weight:bold; color:rgba({base_rgb}, {opacity}); {margin}"
            elif i == 0:
                css = (
                    "font-weight:bold;"
                    f' {"color:#DC143C;" if msg.is_error else ""} {margin}'
                )
            else:
                css = f"color:rgb(102,102,102); {margin}"

            html.append(f'<div style="{css}">{msg.text}</div>')
        html.append("</div>")

        self.selected_items.setHtml("".join(html))
        self.showing_default_status = False

    def _update_display_with_selective_opacity(self, blinking_msg, opacity):
        self._render_status(blinking_msg, opacity)

    def _update_status_display_text(self):
        self._render_status()

    def display_random_status(self):
        """Displays the randomization setting"""
        if self.randomize_selection.isChecked():
            self.show_temporary_status("Randomization on!", 2000)
        else:
            self.show_temporary_status("Randomization off!", 2000)

    def load_recent(self):
        """
        Loads most recent session settings from unified config.json.
        """
        recent = self.config.get("recent_session", {})
        if not recent:  # First time launch or no recent session
            return self.selected_items.clear()

        folders = recent.get("folders", [])
        loaded_any = False
        if folders:
            self.selection["folders"] = folders
            self.scan_directories(folders)
            loaded_any = True

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

    # endregion

    # region Session Settings
    def append_schedule(self):
        """
        Adds entry information as a new row in the schedule.
        Resets scrollboxes to 0.
        Updates total amount.
        Prevents adding an entry if both minutes and seconds are 0.
        """
        minutes = self.set_minutes.value()
        seconds = self.set_seconds.value()
        if minutes == 0 and seconds == 0:
            self.show_error_status("Time must be greater than 0 seconds!", 3000)
            return

        row = self.entry_table.rowCount()
        entry = [
            row + 1,  # entry number
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
            # Sets the entry column to be not editable, while still selectable.
            if column == 0:
                item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.entry_table.setItem(row, column, item)
        self.set_number_of_images.setFocus()
        self.set_number_of_images.selectAll()

    def remove_row(self):
        # Save current row
        row = self.entry_table.currentRow()
        self.entry_table.removeRow(row)
        for i in range(row, self.entry_table.rowCount()):
            item = QTableWidgetItem(str(i + 1))
            item.setTextAlignment(4)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.entry_table.setItem(i, 0, item)
        # Set current cell
        if row != self.entry_table.rowCount():
            self.entry_table.setCurrentCell(row, 0)
        else:  # Case for last row selected
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
        for column in range(
            1, self.entry_table.columnCount()
        ):  # Column 0 is the title column
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
        """Clears the schedule of its entries"""
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
        Updates the total number of images and total time based on the entries in the entry_table.

        This method iterates through all rows in the entry_table, summing up the values in the image and time columns.
        It handles cases where the row is incomplete or contains invalid data, printing debug information if an error occurs.
        The computed totals are then displayed in the total_table, adding a new row if necessary.

        Returns:
            None
        """
        # Check if the row is completely set
        rows = self.entry_table.rowCount()
        if (
            self.entry_table.item(rows - 1, 1) is None
            or self.entry_table.item(rows - 1, 2) is None
        ):
            return
        self.total_images = 0
        self.total_time = 0
        for row in range(rows):
            # Amount of images
            try:
                self.total_images += int(self.entry_table.item(row, 1).text())
            except (Exception, ValueError):
                print(f"BUG self.total_images could not be added from")
                print(f"row: {row}")
                print("item", self.entry_table.item(row, 1).text())
                print(f"{self.entry_table.row()} {self.entry_table.column()}")
                return
            # Amount of time
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
        # Adds a row for total if it's empty
        if self.total_table.rowCount() < 1:
            self.total_table.insertRow(0)
        total = QTableWidgetItem("Total")
        total.setTextAlignment(4)
        self.total_table.setItem(0, 0, total)
        # Sets amount of images
        total_images = QTableWidgetItem(str(self.total_images))
        total_images.setTextAlignment(4)
        self.total_table.setItem(0, 1, total_images)
        # Sets amount of time
        total_time = QTableWidgetItem(self.format_seconds(self.total_time))
        total_time.setTextAlignment(4)
        self.total_table.setItem(0, 2, total_time)

    def format_seconds(self, sec):
        """
        Convert *sec* seconds (float or int, ≥ 0) to a zero-padded
        ``HH:MM:SS`` string. If *sec* has a fraction, show milliseconds:
        ``HH:MM:SS.mmm``.

        Examples
        --------
        >>> self.format_seconds(3661)
        '01:01:01'
        >>> self.format_seconds(5.3)
        '00:00:05.300'
        >>> self.format_seconds(0.007)
        '00:00:00.007'
        """
        if sec < 0:
            raise ValueError("seconds cannot be negative")

        # Split into hours, minutes, seconds-with-fraction
        hours, remainder = divmod(sec, 3600)
        minutes, sec_fraction = divmod(remainder, 60)

        hours = int(hours)
        minutes = int(minutes)

        int_secs = int(sec_fraction)
        millis_raw = int(round((sec_fraction - int_secs) * 1000))

        # Handle rounding overflow (59.9995 s → 60.000 s etc.)
        if millis_raw == 1000:
            millis_raw = 0
            int_secs += 1
            if int_secs == 60:
                int_secs = 0
                minutes += 1
                if minutes == 60:
                    minutes = 0
                    hours += 1

        if millis_raw == 0:
            secs_str = f"{int_secs:02d}"
        else:
            secs_str = f"{int_secs:02d}.{millis_raw:03d}"

        return f"{hours:02d}:{minutes:02d}:{secs_str}"

    # endregion

    # region Presets
    def init_preset(self):
        # Load presets from config.json under 'presets' key
        self.presets = self.config.get("presets", {})
        self.update_presets()

    def update_presets(self):
        """
        Populates the configuration with preset.
        """
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
        tmppreset = {}
        for row in range(self.entry_table.rowCount()):
            tmppreset[row] = []
            for column in range(self.entry_table.columnCount()):
                tmppreset[row].append(self.entry_table.item(row, column).text())
        # Save to config.json under 'presets'
        self.presets[preset_name] = tmppreset
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
        # If the current text in the preset field exists as the key for a saved
        # preset, then update the schedule
        preset = self.presets.get(preset_name)
        if preset:
            self.remove_rows()
            # preset is a dict: {row_index: [col1, col2, ...], ...}
            # Sort by row index to preserve order
            try:
                for row_idx, row_data in sorted(
                    preset.items(), key=lambda x: int(x[0])
                ):
                    row = self.entry_table.rowCount()
                    self.entry_table.insertRow(row)
                    for column, value in enumerate(row_data):
                        item = QTableWidgetItem(value)
                        item.setTextAlignment(4)
                        if column == 0:
                            item.setFlags(QtCore.Qt.ItemIsEnabled)
                        self.entry_table.setItem(row, column, item)
            except Exception as e:
                self.show_error_status(f"Error loading preset: {e}", 4000)

    # endregion
    # endregion
    # region
    # Start Session
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
        # Apply randomization
        if self.randomize_selection.isChecked():
            self.randomize_items()
        # Save to recent folder
        self.save_to_recent()

        # save config
        self.save(wait_status=False)

        self.insert_breaks()
        self.display = SessionDisplay(
            schedule=self.session_schedule,
            items=self.selection["files"],
            total=self.total_scheduled_images,
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
        # Check if all items are numbers
        for row in range(self.entry_table.rowCount()):
            items = []
            try:
                for i in range(2):
                    items.append(int(self.entry_table.item(row, i + 1).text()))
            except (Exception, ValueError):
                self.show_error_status("Schedule items must be numbers!")
                return False

        # Check if empty schedule
        if len(self.session_schedule) == 0:
            self.show_error_status("Schedule cannot be empty.")
            return False
        # Count scheduled images
        self.total_scheduled_images = 0
        for entry in self.session_schedule:
            self.total_scheduled_images += entry.images

        # Check if file exists
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

        # Check if there are enough selected images for the schedule
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
                    self.selection["files"].insert(current_index, ":/break/break.png")
                    continue
                current_index += entry.images

    def remove_breaks(self):
        """
        Removes all occurrences of 'break.png' from the list of selected files.

        Iterates through the 'files' list in reverse order and removes any file whose
        basename is 'break.png'. This prevents issues with changing list indices during removal.

        Returns:
            None
        """
        """Removes breaks images from the selection of files"""
        i = len(self.selection["files"])
        while i > 0:
            i -= 1
            if self.selection["files"][i] == ":/break/break.png":
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
        self.config["recent_session"] = {
            "folders": self.selection["folders"],
            "files": self.selection["files"],
            "recent_preset": self.preset_loader_box.currentIndex(),
            "randomized": self.randomize_selection.isChecked(),
        }
        save_config(self.config_path, self.config)

    # endregion

    # region
    # Updates
    def check_version(self):
        """
        Checks for updates via UpdateChecker, which itself updates
        self.config["update_check"] in config.json.
        """
        checker = UpdateChecker(__version__)
        update = (
            checker.check_for_updates() if self.config.get("update_check") else None
        )
        if update:
            self.show_temporary_status(
                "Update available! Please visit the site to download!", 5000
            )
            self.show_temporary_status(f"v{update['version']}: {update['notes']}", 6000)
        self.config_path = checker.config_path
        # else:
        #     self.selected_items.append("Up to date.")

    def show_and_activate(self):
        self.show()
        self.raise_()
        self.activateWindow()


class SessionDisplay(QWidget, Ui_session_display):
    closed = QtCore.pyqtSignal()  # Needed here for close event to work.

    def __init__(self, schedule=None, items=None, total=None, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.init_sizing()

        self.init_scaling_size()
        self.init_button_sizes()
        # Hide the old numeric status label
        self.session_info.hide()

        # Top row → images in current entry | Bottom row → entries in session
        self.image_progress = DotIndicator(
            parent=self, dot_d=11, top_overlay=True
        )  # larger cyan
        self.entry_progress = DotIndicator(
            parent=self, dot_d=8, top_overlay=True
        )  # smaller green
        self.image_progress.setContentsMargins(0, 10, 0, 0)
        self.entry_progress.setContentsMargins(0, 0, 0, 10)

        # Pack the two rows into a left‑hand container so the central control
        # buttons remain perfectly centred.
        self.indicators_container = QWidget()
        vbox = QtWidgets.QVBoxLayout(self.indicators_container)
        vbox.setContentsMargins(0, 0, 1, 0)  # no unwanted vertical gap
        vbox.setSpacing(0)
        # make the thickness of the border thinner
        self.indicators_container.setStyleSheet(
            "QWidget { rgba(85,85,85,0.25); border-radius: 4px; }"
        )
        vbox.addWidget(self.image_progress)
        vbox.addWidget(self.entry_progress)

        # Insert the container at the far‑left edge of the control row
        controls_layout_item: QtWidgets.QLayoutItem = self.verticalLayout.itemAt(1)
        if controls_layout_item and isinstance(
            controls_layout_item.layout(), QtWidgets.QHBoxLayout
        ):
            controls_layout = controls_layout_item.layout()
            controls_layout.insertWidget(0, self.indicators_container, stretch=0)

            # Prevent the container from hogging horizontal space.
            self.indicators_container.setSizePolicy(
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.Fixed,
            )

            # Keep the controls cluster centred when the window is resized.
            self._adjust_progressbar_width()
        self.drag_timer_was_active = False
        self.drag_start_position = QtCore.QPoint()
        self.drag_threshold = 6
        self.schedule = schedule
        self.playlist = items
        self.playlist_position = 0
        self.total_scheduled_images = total
        self.init_timer()
        self.init_entries()
        self.installEventFilter(self)
        self.image_display.installEventFilter(self)
        pause_style = "background: rgb(100, 120, 118); padding:2px;"
        for btn in (
            self.previous_image,
            self.pause_timer,
            self.stop_session,
            self.next_image,
            self.grayscale_button,
            self.flip_horizontal_button,
            self.flip_vertical_button,
        ):
            btn.setMinimumSize(60, 32)
            btn.setStyleSheet(pause_style)
        self.init_image_mods()
        self.init_mixer()
        break_indices = [
            i for i, entry in enumerate(self.schedule) if entry.images == 0
        ]
        self.entry_progress.setBreaks(break_indices)
        self.entry_progress.setMaximum(len(self.schedule))
        self.entry_progress.setValue(1)
        self.load_entry()
        self.init_buttons()
        self.init_shortcuts()
        self.skip_count = 0

    def init_sizing(self):
        """
        Resizes the window to half of the current screen's resolution,
        sets states for window flags,
        and initializes self.previous_size.

        """
        self.resize(self.screen().availableSize() / 2)
        self.toggle_resize_status = False
        self.toggle_always_on_top_status = False
        self.frameless_status = False
        self.sizePolicy().setHeightForWidth(True)
        self.previous_size = self.size()

    def init_scaling_size(self):
        """
        Creates a scaling box size that is used as a basis for
        images to scale off of. The box dimensions are determined by the
        smallest side of half of the given rectangle from the
        current screen's available resolution.

        """
        half_screen = self.screen().availableSize() / 2
        min_length = min(half_screen.height(), half_screen.width())
        self.scaling_size = QtCore.QSize(min_length, min_length)

    def init_timer(self):
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.countdown)
        self.timer.start(500)
        self.session_finished = False
        self.close_seconds = 15
        self.close_timer = QtCore.QTimer()
        self.close_timer.timeout.connect(self.close_countdown)
        self.sec = ["0", "0"]
        self.minutes_list = ["0", "0"]
        self.hrs_list = ["0", "0"]

    def init_entries(self):
        self.entry = {
            "current": 0,
            "total": len(self.schedule),
            "amount of items": self.schedule[0].images,
            "time": self.schedule[0].time,
        }
        self.new_entry = True
        if self.entry["amount of items"] > 1:
            self.end_of_entry = False
        else:
            self.end_of_entry = True
        print(f"self.endofentry: {self.end_of_entry}")

    def init_image_mods(self):
        self.image_mods = {
            "break": False,
            "grayscale": False,
            "hflip": False,
            "vflip": False,
            "break_grayscale": False,
            "brightness": 0,
            "contrast": 1.0,
            "threshold": False,
            "edge": False,
            "grayscale_mode": "perceptual",  # or "simple"
        }

    def reset_image_mods(self):
        """Reset all image modifications to their default values and update the display."""
        self.init_image_mods()
        self.display_image(play_sound=False)

    def init_mixer(self):
        mixer.init()
        try:
            """
            If view.mute exists, then a session has been started before.
            Set mute and volume according to previous session's sound settings.
            """
            import __main__

            if hasattr(__main__, "view") and hasattr(__main__.view, "mute"):
                if __main__.view.mute is True:  # if view.mute exists and is True
                    self.mute = True
                    self.volume = mixer.music.get_volume()
                    mixer.music.set_volume(0.0)
                else:  # if view.mute exists and is False
                    self.mute = False
                    self.volume = __main__.view.volume
            else:
                self.volume = mixer.music.get_volume()
                self.mute = False
        except:  # view.mute does not exist, so init settings with default.
            self.volume = mixer.music.get_volume()
            self.mute = False

    def init_button_sizes(self):
        """Ensure all control buttons use a consistent size on any platform"""
        button_size = QtCore.QSize(60, 36)
        if sys.platform == "darwin":
            # macOS tends to render widgets slightly smaller
            button_size = QtCore.QSize(70, 40)

        icon_size = QtCore.QSize(32, 32)
        buttons = [
            self.previous_image,
            self.pause_timer,
            self.stop_session,
            self.next_image,
            self.grayscale_button,
            self.flip_horizontal_button,
            self.flip_vertical_button,
        ]
        for btn in buttons:
            btn.setFixedSize(button_size)
            btn.setIconSize(icon_size)

    def init_buttons(self):
        self.previous_image.clicked.connect(self.previous_playlist_position)
        self.next_image.clicked.connect(self.load_next_image)
        self.stop_session.clicked.connect(self.close)
        self.flip_horizontal_button.clicked.connect(self.flip_horizontal)
        self.flip_vertical_button.clicked.connect(self.flip_vertical)
        self.grayscale_button.clicked.connect(self.grayscale)
        self.pause_timer.clicked.connect(self.pause)

    def init_shortcuts(self):
        # Resize
        self.toggle_resize_key = QShortcut(QtGui.QKeySequence("R"), self)
        self.toggle_resize_key.activated.connect(self.toggle_resize)
        # Always on top
        self.always_on_top_key = QShortcut(QtGui.QKeySequence("A"), self)
        self.always_on_top_key.activated.connect(self.toggle_always_on_top)
        # Mute
        self.mute_key = QShortcut(QtGui.QKeySequence("M"), self)
        self.mute_key.activated.connect(self.toggle_mute)
        # Timer
        self.add_30 = QShortcut(QtGui.QKeySequence("Up"), self)
        self.add_30.activated.connect(self.add_30_seconds)
        self.add_60 = QShortcut(QtGui.QKeySequence("Ctrl+Up"), self)
        self.add_60.activated.connect(self.add_60_seconds)
        self.restart = QShortcut(QtGui.QKeySequence("Ctrl+Shift+Up"), self)
        self.restart.activated.connect(self.restart_timer)
        # Skip image
        self.skip_image_key = QShortcut(QtGui.QKeySequence("S"), self)
        self.skip_image_key.activated.connect(self.skip_image)
        # Frameless Window
        self.frameless_window = QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        self.frameless_window.activated.connect(self.toggle_frameless)
        # Image adjustments
        self.brightness_up = QShortcut(QtGui.QKeySequence("Ctrl+PgUp"), self)
        self.brightness_up.activated.connect(self.increase_brightness)
        self.brightness_down = QShortcut(QtGui.QKeySequence("Ctrl+PgDown"), self)
        self.brightness_down.activated.connect(self.decrease_brightness)
        self.contrast_up = QShortcut(QtGui.QKeySequence("PgUp"), self)
        self.contrast_up.activated.connect(self.increase_contrast)
        self.contrast_down = QShortcut(QtGui.QKeySequence("PgDown"), self)
        self.contrast_down.activated.connect(self.decrease_contrast)
        self.threshold_toggle = QShortcut(QtGui.QKeySequence("T"), self)
        self.threshold_toggle.activated.connect(self.toggle_threshold)
        self.edge_toggle = QShortcut(QtGui.QKeySequence("E"), self)
        self.edge_toggle.activated.connect(self.toggle_edge)
        self.reset_mods = QShortcut(QtGui.QKeySequence("Ctrl+0"), self)
        self.reset_mods.activated.connect(self.reset_image_mods)
        self.toggle_grayscale_mode_shortcut = QShortcut(
            QtGui.QKeySequence("Ctrl+G"), self
        )
        self.toggle_grayscale_mode_shortcut.activated.connect(
            self.toggle_grayscale_mode
        )

    # --- dynamic centring helpers ------------------------------------------
    # --- SessionDisplay ---------------------------------------------------

    def _adjust_progressbar_width(self):
        """
        Give the indicators_container just enough width for *all* currently
        rendered dots, then set the left/right spacers to equal stretch so
        the control buttons float back to dead-centre.
        """
        try:
            needed = max(
                self.image_progress.sizeHint().width(),
                self.entry_progress.sizeHint().width(),
            )
            self.indicators_container.setFixedWidth(needed + 12)  # +8 px margin

            # Re-centre: both spacer items get stretch=1, everything else = 0
            controls_layout: QtWidgets.QLayout = self.verticalLayout.itemAt(1).layout()
            for i in range(controls_layout.count()):
                item = controls_layout.itemAt(i)
                controls_layout.setStretch(i, 1 if item.spacerItem() else 0)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_progressbar_width()

    def closeEvent(self, event):
        """
        Stops timer and sound on close event.
        """
        self.timer.stop()
        self.close_timer.stop()
        # Store session sound settings globally for next session
        try:
            import __main__

            if hasattr(__main__, "view"):
                __main__.view.mute = self.mute
                __main__.view.volume = self.volume
        except:
            pass
        mixer.quit()
        self.closed.emit()
        event.accept()

    def mousePressEvent(self, event):
        """
        Stores the initial cursor position and whether the timer was active
        before any dragging begins.
        """
        self.old_position = event.globalPos()
        self.drag_start_position = event.globalPos()
        # Record if the timer is active at the start of a potential drag
        self.was_timer_active = self.timer.isActive()
        # Reset drag flag
        self.drag_timer_was_active = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Drags the window by the difference between the current cursor position and self.old_position.
        Pauses the timer on the first movement if it was active before dragging.
        """
        # Start a drag only if the cursor moved beyond the threshold
        if (
            event.globalPos() - self.drag_start_position
        ).manhattanLength() > self.drag_threshold:
            if not self.drag_timer_was_active:
                # Only pause timer if session is not finished
                if not self.session_finished and self.timer.isActive():
                    self.timer.stop()
                    self._set_timer_visuals(False)
                self.drag_timer_was_active = True

        if self.drag_timer_was_active:
            change = event.globalPos() - self.old_position
            self.move(self.x() + change.x(), self.y() + change.y())
            self.old_position = event.globalPos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        After dragging, restores the timer to its previous state (paused or running).
        """
        if self.drag_timer_was_active:
            if not self.session_finished:
                self.timer.stop()
                self._set_timer_visuals(False)
                if not self.was_timer_active:
                    self.pause()
            self.drag_timer_was_active = False
        # super().mouseReleaseEvent(event)

    def eventFilter(self, source, event):
        if self.session_finished and self.close_timer.isActive():
            if event.type() in (
                QtCore.QEvent.KeyPress,
                QtCore.QEvent.MouseButtonPress,
            ):
                self.cancel_close_countdown()

        if source is self.image_display:
            if self.session_finished:
                if event.type() == QtCore.QEvent.MouseButtonDblClick:
                    self.open_image_directory(event)
                    return True
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    self.old_position = event.globalPos()
                    self.drag_start_position = event.globalPos()
                    return True
            else:
                if event.type() == QtCore.QEvent.MouseButtonDblClick:
                    if self.was_timer_active:
                        self.pause()  # Always pause on double click
                    self.time_seconds += 0.7
                    self.open_image_directory(event)
                    return True
                if event.type() == QtCore.QEvent.MouseButtonPress:
                    self.old_position = event.globalPos()
                    self.drag_start_position = event.globalPos()
                    # Only toggle pause/resume if not part of a drag
                    if not self.drag_timer_was_active:
                        if self.timer.isActive():
                            self.timer.stop()
                            self._set_timer_visuals(False)
                        else:
                            self.timer.start(500)
                            self._set_timer_visuals(True)
                        self.display_time()
                    self.was_timer_active = self.timer.isActive()
                    self.drag_timer_was_active = False
                    return True
        return super(SessionDisplay, self).eventFilter(source, event)

    def skip_image(self):
        if self.playlist[self.playlist_position] == "break.png":
            print(f"No images to skip on break {self.playlist[self.playlist_position]}")
            self.setWindowTitle("No images to skip on break")
            return

        swap_indicies = list(range(self.playlist_position + 1, len(self.playlist)))
        random.shuffle(swap_indicies)
        while swap_indicies:
            swap_index = swap_indicies.pop()
            if self.playlist[swap_index] != "break.png":
                self.playlist[self.playlist_position], self.playlist[swap_index] = (
                    self.playlist[swap_index],
                    self.playlist[self.playlist_position],
                )
                break
        else:
            print(f"No images to skip to {self.playlist[self.playlist_position]}")
            self.setWindowTitle("No remaining unused images to skip to")
            return
        self.display_image()
        self.restart_timer()

    def toggle_mute(self):
        if self.mute is True:
            self.mute = False
            mixer.music.set_volume(self.volume)
        else:
            self.mute = True
            self.volume = mixer.music.get_volume()
            mixer.music.set_volume(0.0)

    def load_entry(self, resume_timer: bool = True):
        if self.entry["current"] >= self.entry["total"]:
            self.end_session()
            return
        self.entry["time"] = self.schedule[self.entry["current"]].time
        self.timer.stop()
        self.time_seconds = self.entry["time"]
        if resume_timer:
            self.timer.start(500)
            self._set_timer_visuals(True)
        else:
            self._set_timer_visuals(False)
        self.entry["amount of items"] = self.schedule[self.entry["current"]].images - 1
        # Update entry_progress dot indicator
        self.entry_progress.setMaximum(self.entry["total"])
        self.entry_progress.setValue(self.entry["current"] + 1)
        self.display_image()

    def end_session(self):
        self.session_finished = True
        self.timer.stop()
        # Prevent further countdown updates once the session is done
        self.timer.blockSignals(True)
        self.close_seconds = 15
        self.setWindowTitle("Session complete! Navigate images with arrows")
        self.session_info.setText(
            "Use arrows to browse. Double-click or Ctrl+O to open folder"
        )
        # Reset indices so reviewing previous images works correctly
        self.entry["current"] = max(0, self.entry["total"] - 1)
        self.entry["amount of items"] = 0

        self.playlist_position = max(0, int(self.total_scheduled_images))
        self.timer_display.setText(f"Done! Closing in {self.close_seconds}s...")
        # Grey-out / complete the bars
        self.image_progress.setValue(self.image_progress.maximum())
        self.entry_progress.setValue(self.entry_progress.maximum())
        self.update_close_title()
        self.close_timer.start(1000)

    def load_next_image(self):
        was_timer_active = self.timer.isActive()
        self.timer.stop()
        if self.session_finished:
            self.cancel_close_countdown()
            self.timer.blockSignals(True)
            if self.playlist_position == self.total_scheduled_images:
                return
            self.playlist_position += 1
            self.display_image()
            return
        if self.entry["current"] >= self.entry["total"]:  # End of schedule
            return
        if self.entry["amount of items"] == 0:  # End of entry
            self.entry["current"] += 1
            self.playlist_position += 1
            self.new_entry = True
            self.time_seconds = self.entry["time"]
            self.load_entry(was_timer_active)
        else:
            self.timer.stop()
            self.time_seconds = self.entry["time"]
            if was_timer_active:
                self.timer.start(500)
            self.playlist_position += 1
            self.entry["amount of items"] -= 1
            self.new_entry = False
            if self.entry["amount of items"] == 0:
                self.end_of_entry = True
            self.display_image()
        if was_timer_active:
            self.timer.start(500)
            self._set_timer_visuals(True)
        else:
            self._set_timer_visuals(False)

    def display_image(self, play_sound=True):
        print(self.entry)
        # Sounds
        if play_sound:
            if self.new_entry:
                with sound_file("new_entry.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()
                # self.new_entry = False
            elif self.entry["amount of items"] == 0:  # Last image in entry
                with sound_file("last_entry_image.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()
            elif self.entry["time"] > 10:
                with sound_file("new_image.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()

        if self.playlist_position >= len(self.playlist):  # Last image
            self.timer.stop()
            self.timer_display.setText(f"Done!")
            return
        else:
            # if (self.entry['amount of items'] == -1  # End of entry
            #         or os.path.basename(
            #             self.playlist[self.playlist_position]
            #         ) == 'break.png'):  # Break scheduled
            if (
                self.playlist[self.playlist_position] == ":/break/break.png"
            ):  # Break scheduled
                """
                Since the end of an entry has been reached, or a break is scheduled,
                configure for break image.

                """
                self.image_mods["break"] = True
                self.image_mods["break_grayscale"] = True
                self.entry["amount of items"] = 0
                self.setWindowTitle("Break")
                self.session_info.setText("Break")
                # Set image progress to break mode (single orange dot)
                self.image_progress.setMaximum(0)
                self.image_progress.setValue(1)
            else:
                self.image_mods["break"] = False
                self.image_mods["break_grayscale"] = False
                self.setWindowTitle(self.playlist[self.playlist_position])
                current_entry = self.schedule[self.entry["current"]]
                self.session_info.setText(
                    f' {self.entry["current"] + 1}/{self.entry["total"]} | '
                    f'{current_entry.images - self.entry["amount of items"]}'
                    f"/{current_entry.images}"
                )
                current_img_index = current_entry.images - self.entry["amount of items"]
                self.image_progress.setMaximum(current_entry.images)
                self.image_progress.setValue(current_img_index)
                self._adjust_progressbar_width()  # <- make room for new dot count
            #                 self.entry_progress.setFormat(
            #                     f"Entry {self.entry['current'] + 1}/{self.entry['total']}"
            # )
            # self.session_info.setText(
            #     f' {self.entry["current"] + 1}/{self.entry["total"]} | '
            #     f'{current_entry.images - self.entry["amount of items"]}'
            #     f"/{current_entry.images}"
            # )
            self.prepare_image_mods()

    def prepare_image_mods(self):
        """
        self.image gets modified depending on which value in self.image_mods
        is true.
        """
        # Break scheduled
        if self.image_mods["break"]:
            cvimage = self.convert_to_cvimage()
        # jpg file
        elif self.playlist[self.playlist_position][-3:].lower() == "jpg":
            cvimage = self.convert_to_cvimage()
        # Edge cases are handled
        else:
            # Read image as bytes and decode to preserve all channels (including alpha)
            with open(self.playlist[self.playlist_position], "rb") as f:
                file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
                cvimage = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)

        # Handle if cvimage is None or empty
        if cvimage is None or cvimage.size == 0:
            print(
                "Error: Could not load image at"
                f" {self.playlist[self.playlist_position]}"
            )
            self.setWindowTitle("Error processing image")
            return
        try:
            height, width = cvimage.shape[:2]
            channels = 1 if len(cvimage.shape) == 2 else cvimage.shape[2]
            if channels not in (1, 3, 4):
                raise ValueError(f"Unexpected channel count: {channels}")
            bytes_per_line = channels * width if channels > 1 else width
        except (AttributeError, ValueError, BufferError) as e:
            self.setWindowTitle("Error processing image")
            return
        # Brightness and contrast
        b = self.image_mods["brightness"]
        c = self.image_mods["contrast"]
        if b != 0 or c != 1.0:
            cvimage = cv2.convertScaleAbs(cvimage, alpha=c, beta=b)
        print(f"cvimage shape: {cvimage.shape}, channels: {channels}")
        # if channels == 4:
        #     return

        # Grayscale/threshold/edge
        grayscale_active = (
            self.image_mods["grayscale"] or self.image_mods["break_grayscale"]
        )
        if grayscale_active or self.image_mods["threshold"] or self.image_mods["edge"]:
            if self.image_mods.get("grayscale_mode", "perceptual") == "simple":
                gray = self.to_simple_grayscale(cvimage)
            else:
                gray = self.to_fidelous_grayscale(cvimage)

        if grayscale_active:
            cvimage = gray

        if self.image_mods["threshold"]:
            _, cvimage = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        if self.image_mods["edge"]:
            cvimage = cv2.Canny(gray, 100, 200)

        # Flip
        if self.image_mods["hflip"]:
            cvimage = cv2.flip(cvimage, 1)
        if self.image_mods["vflip"]:
            cvimage = cv2.flip(cvimage, 0)

        # Convert to QImage
        height, width = cvimage.shape[:2]
        if cvimage.ndim == 2:  # Grayscale image
            bytes_per_line = width
            self.image = QtGui.QImage(
                cvimage.data,
                width,
                height,
                bytes_per_line,
                QtGui.QImage.Format_Grayscale8,
            )
        else:
            channels = cvimage.shape[2]
            if channels == 4:  # If image has an alpha channel
                cvimage = cv2.cvtColor(cvimage, cv2.COLOR_BGRA2RGBA)
                fmt = QtGui.QImage.Format_RGBA8888
            elif channels == 3:
                cvimage = cv2.cvtColor(cvimage, cv2.COLOR_BGR2RGB)
                fmt = QtGui.QImage.Format_RGB888
            else:
                self.setWindowTitle("Error processing image")
                return
            bytes_per_line = width * channels
            self.image = QtGui.QImage(cvimage.data, width, height, bytes_per_line, fmt)

        # Convert to QPixmap
        self.image = QtGui.QPixmap.fromImage(self.image)
        if self.toggle_resize_status:  # If toggle resize is true
            self.image_display.setPixmap(
                self.image.scaled(
                    self.size(),
                    aspectRatioMode=QtCore.Qt.KeepAspectRatio,
                    transformMode=QtCore.Qt.SmoothTransformation,
                )
            )
            return
        # Display image scaled to window size in image display
        # If resized
        if self.size() != self.previous_size:
            resized_pixmap = self.image_display.pixmap()
            scaled_size = self.scaling_size.scaled(
                resized_pixmap.size(), QtCore.Qt.KeepAspectRatio
            )
            self.scaling_size = QtCore.QSize(scaled_size)

        # Get scaled pixmap
        self.image_scaled = self.image.scaled(
            self.scaling_size,
            aspectRatioMode=QtCore.Qt.KeepAspectRatioByExpanding,
            transformMode=QtCore.Qt.SmoothTransformation,
        )
        # Set
        self.image_display.setPixmap(self.image_scaled)
        # Resize
        self.image_display.resize(self.image_scaled.size())
        self.resize(
            self.image_scaled.size().width(),
            # 32 is the current height of the nav bar in px
            self.image_scaled.size().height() + 32,
        )
        # Save current size
        self.previous_size = self.size()

    def convert_to_cvimage(self):
        file = QtCore.QFile()
        file.setFileName(self.playlist[self.playlist_position])
        file.open(QtCore.QFile.OpenModeFlag.ReadOnly)
        ba = file.readAll()
        ba = ba.data()
        ba = np.asarray(bytearray(ba), dtype="uint8")
        file.close()
        return cv2.imdecode(ba, 1)

    def to_fidelous_grayscale(self, image):
        # Convert to RGB, handling alpha by compositing on white if present
        if image.ndim == 3 and image.shape[2] == 4:
            # Split channels
            b, g, r, a = cv2.split(image)
            rgb = cv2.merge([r, g, b]).astype(np.float32)
            gray = np.dot(rgb, [0.2126, 0.7152, 0.0722])
            gray = np.clip(gray, 0, 255).astype(np.uint8)
            # Stack grayscale and alpha back together as BGRA
            result = cv2.merge([gray, gray, gray, a])
            return result
        else:
            rgb = image[..., ::-1].astype(np.float32)  # BGR to RGB
            gray = np.dot(rgb, [0.2126, 0.7152, 0.0722])
            gray = np.clip(gray, 0, 255).astype(np.uint8)
            return gray

    def to_simple_grayscale(self, image):
        """Simple grayscale: convert BGR image to single channel grayscale."""
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def toggle_grayscale_mode(self):
        """Toggle between perceptual and simple grayscale modes."""
        if self.image_mods["grayscale_mode"] == "perceptual":
            self.image_mods["grayscale_mode"] = "simple"
            self.setWindowTitle("Simple Grayscale Mode")
        else:
            self.image_mods["grayscale_mode"] = "perceptual"
            self.setWindowTitle("Perceptual Grayscale Mode")
        self.display_image(play_sound=False)

    def flip_horizontal(self):
        if self.image_mods["hflip"]:
            self.image_mods["hflip"] = False
        else:
            self.image_mods["hflip"] = True
        self.display_image(play_sound=False)

    def flip_vertical(self):
        if self.image_mods["vflip"]:
            self.image_mods["vflip"] = False
        else:
            self.image_mods["vflip"] = True
        self.display_image(play_sound=False)

    def grayscale(self):
        if self.image_mods["grayscale"]:
            self.image_mods["grayscale"] = False
        else:
            self.image_mods["grayscale"] = True
        self.display_image(play_sound=False)

    def increase_brightness(self):
        self.image_mods["brightness"] = min(self.image_mods["brightness"] + 10, 100)
        self.display_image()

    def decrease_brightness(self):
        self.image_mods["brightness"] = max(self.image_mods["brightness"] - 10, -100)
        self.display_image()

    def increase_contrast(self):
        self.image_mods["contrast"] = min(self.image_mods["contrast"] + 0.1, 3.0)
        self.display_image()

    def decrease_contrast(self):
        self.image_mods["contrast"] = max(self.image_mods["contrast"] - 0.1, 0.1)
        self.display_image()

    def toggle_threshold(self):
        self.image_mods["threshold"] = not self.image_mods["threshold"]
        self.display_image()

    def toggle_edge(self):
        self.image_mods["edge"] = not self.image_mods["edge"]
        self.display_image()

    def toggle_resize(self):
        if self.toggle_resize_status is not True:
            self.toggle_resize_status = True
            self.sizePolicy().setHeightForWidth(False)
        else:
            self.toggle_resize_status = False
            self.sizePolicy().setHeightForWidth(True)

    def toggle_always_on_top(self):
        if self.toggle_always_on_top_status is not True:
            self.toggle_always_on_top_status = True
            self.setWindowFlag(
                QtCore.Qt.X11BypassWindowManagerHint, self.toggle_always_on_top_status
            )
            self.setWindowFlag(
                QtCore.Qt.WindowStaysOnTopHint, self.toggle_always_on_top_status
            )
            self.show()
        else:
            self.toggle_always_on_top_status = False
            self.setWindowFlag(
                QtCore.Qt.WindowStaysOnTopHint, self.toggle_always_on_top_status
            )
            self.show()

    def toggle_frameless(self):
        if self.frameless_status is not True:
            self.frameless_status = True
            self.setWindowFlag(QtCore.Qt.FramelessWindowHint, self.frameless_status)
            self.show()
        else:
            self.frameless_status = False
            self.setWindowFlag(QtCore.Qt.FramelessWindowHint, self.frameless_status)
            self.show()

    def previous_playlist_position(self):
        was_timer_active = self.timer.isActive()
        self.timer.stop()
        if self.session_finished:
            self.cancel_close_countdown()
            if self.playlist_position == 0:
                self.display_image()
                self._set_timer_visuals(False)
                return
            self.playlist_position -= 1
            self.display_image()
            self._set_timer_visuals(False)
            return
        # Skip_counter
        # if self.skip_count > 0:
        #     self.skip_count -= 1
        # First image
        if self.playlist_position == 0 or (
            self.entry["current"] == 0
            and self.entry["amount of items"] == self.schedule[0].images - 1
        ):
            """
            If it's the first image in the playlist or if the current entry
            is the first one and the position is at the beginning. The second
            case is in place for the skip function

            """
            self.time_seconds = self.entry["time"]
            self.update_timer_display()
            self.timer.stop()
            self.timer_display.setText("First image! Restarting timer...")
            QTest.qWait(1000)
            if was_timer_active:
                self.timer.start(500)
            self.load_entry(was_timer_active)
            self._set_timer_visuals(was_timer_active)
            return

        self.playlist_position -= 1  # Navigate to the previous position
        # End of entries
        if self.entry["current"] >= self.entry["total"]:
            self.entry["current"] = len(self.schedule) - 1
            self.timer.stop()
            self.entry["time"] = self.schedule[self.entry["current"]].time
            self.time_seconds = self.entry["time"]
            if was_timer_active:
                self.timer.start(500)
            self.entry["amount of items"] = 0
            self.end_of_entry = True
            self.display_image()
            self._set_timer_visuals(was_timer_active)
            return
        # At the beginning of a new entry

        if (
            self.entry["amount of items"] + 1
            == self.schedule[self.entry["current"]].images
            or self.session_info.text() == "Break"
        ):
            if self.entry["current"] != 0:
                self.entry["current"] -= 1
            self.timer.stop()
            self.entry["time"] = self.schedule[self.entry["current"]].time
            self.time_seconds = self.entry["time"]
            self.update_timer_display()
            if was_timer_active:
                self.timer.start(500)
            self.entry["amount of items"] = 0
            self.new_entry = True
            self.display_image()
            self._set_timer_visuals(was_timer_active)
            return
        self.entry["amount of items"] += 1
        self.time_seconds = self.entry["time"]
        self.update_timer_display()
        self.new_entry = False
        self.display_image()
        if was_timer_active:
            self.timer.start(500)
            self._set_timer_visuals(True)
        else:
            self._set_timer_visuals(False)

    # endregion

    # region Timer functions
    def format_seconds(self, sec):
        minutes = int(sec / 60)
        sec = int(self.time_seconds - (minutes * 60))
        return f"{minutes}:{sec}"

    def countdown(self):
        self.update_timer_display()
        if self.entry["time"] >= 30:
            if self.time_seconds == self.entry["time"] // 2:
                with sound_file("halfway.mp3") as p:
                    mixer.music.load(str(p))
                mixer.music.play()
        if self.time_seconds <= 10:
            if self.new_entry is False and self.end_of_entry is False:
                if self.time_seconds == 10:
                    with sound_file("first_alert.mp3") as p:
                        mixer.music.load(str(p))
                    mixer.music.play()
                elif self.time_seconds == 5:
                    with sound_file("second_alert.mp3") as p:
                        mixer.music.load(str(p))
                    mixer.music.play()
                elif self.time_seconds == 0.5:
                    with sound_file("third_alert.mp3") as p:
                        mixer.music.load(str(p))
                    mixer.music.play()
            else:
                if self.new_entry is True:
                    self.new_entry = False
                if self.end_of_entry is True:
                    self.end_of_entry = False
            if self.playlist[self.playlist_position] == ":/break/break.png":
                self.image_mods["break_grayscale"] = False
                self.prepare_image_mods()
        if self.time_seconds == 0:
            QTest.qWait(500)
            self.load_next_image()
            return
        self.time_seconds -= 0.5

    def update_timer_display(self):
        hr = int(self.time_seconds / 3600)
        self.hrs_list = list(str(hr))
        if len(self.hrs_list) == 1 or self.hrs_list[0] == "0":
            self.hrs_list.insert(0, "0")

        minutes = int((self.time_seconds / 3600 - hr) * 60)
        self.minutes_list = list(str(minutes))
        if len(self.minutes_list) == 1 or self.minutes_list[0] == "0":
            self.minutes_list.insert(0, "0")
        self.sec = list(
            str(int((((self.time_seconds / 3600 - hr) * 60) - minutes) * 60))
        )
        if len(self.sec) == 1 or self.sec[0] == "0":
            self.sec.insert(0, "0")
        self.display_time()

    # Constants for timer visuals
    PAUSE_BUTTON_RUNNING_STYLE = (
        "background: rgb(100, 120, 118); padding:2px; border:1px solid transparent;"
    )
    PAUSE_BUTTON_PAUSED_STYLE = (
        "background: rgb(100, 120, 118); padding:2px; border:1px solid white;"
    )
    TIMER_DISPLAY_RUNNING_STYLE = "color: white;"
    TIMER_DISPLAY_PAUSED_STYLE = "color: white; border:1px solid white;"

    def _set_timer_visuals(self, running: bool) -> None:
        """Update pause button and display border based on running state."""
        if running:
            self.pause_timer.setIcon(QtGui.QIcon(":/icons/icons/Pause.png"))
            self.pause_timer.setStyleSheet(self.PAUSE_BUTTON_RUNNING_STYLE)
            self.timer_display.setStyleSheet(self.TIMER_DISPLAY_RUNNING_STYLE)
        else:
            self.pause_timer.setIcon(QtGui.QIcon(":/icons/icons/Play2.png"))
            self.pause_timer.setStyleSheet(self.PAUSE_BUTTON_PAUSED_STYLE)
            self.timer_display.setStyleSheet(self.TIMER_DISPLAY_PAUSED_STYLE)

    def pause(self):
        # Do nothing if the session has finished
        if self.session_finished:
            return
        self.update_timer_display()  # ensure sec, minutes_list, hrs_list are set
        if self.timer.isActive():
            self.timer.stop()
            self._set_timer_visuals(False)
        else:
            self._set_timer_visuals(True)
            self.timer.start(500)
        self.display_time()

    def display_time(self):
        """
        Displays amount of time left depending on how many seconds are left.

        """
        # Hour or longer
        if self.time_seconds >= 3600:
            self.timer_display.setText(
                f"{self.hrs_list[0]}{self.hrs_list[1]}:"
                f"{self.minutes_list[0]}{self.minutes_list[1]}:"
                f"{self.sec[0]}{self.sec[1]}"
            )
        # Minute or longer
        elif self.time_seconds >= 60:
            self.timer_display.setText(
                f"{self.minutes_list[0]}{self.minutes_list[1]}:"
                f"{self.sec[0]}{self.sec[1]}"
            )
        # Less than a minute left
        else:
            self.timer_display.setText(f"{self.sec[0]}{self.sec[1]}")

    def add_30_seconds(self):
        if self.session_finished:
            return
        self.time_seconds += 30
        self.update_timer_display()

    def add_60_seconds(self):
        if self.session_finished:
            return
        self.time_seconds += 60
        self.update_timer_display()

    def restart_timer(self):
        if self.session_finished:
            return
        self.time_seconds = self.schedule[self.entry["current"]].time

    def update_close_title(self):
        self.setWindowTitle(
            f"Review mode - closing in {self.close_seconds}s (Ctrl+O opens folder)"
        )

    def close_countdown(self):
        if not self.close_timer.isActive():
            return
        self.close_seconds -= 1
        if self.close_seconds <= 0:
            self.close_timer.stop()
            self.close()
            return
        self.timer_display.setText(f"Done! Closing in {self.close_seconds}s...")
        self.update_close_title()

    def cancel_close_countdown(self):
        if self.close_timer.isActive():
            self.close_timer.stop()
            self.timer_display.setText("Done!")
            self.setWindowTitle("Session complete - review mode (Ctrl+O opens folder)")

    def open_image_directory(self, event=None):
        path = self.playlist[self.playlist_position]
        if path.startswith(":/"):
            return
        system = platform.system()
        if system == "Windows":
            QtCore.QProcess.startDetached(
                "explorer.exe", [f"/select,{Path(path).resolve()}"]
            )
        elif system == "Darwin":  # macOS
            QtCore.QProcess.startDetached("open", ["-R", path])
        else:  # Linux and other systems
            # Use xdg-open for Linux
            QtCore.QProcess.startDetached("xdg-open", ["-R", path])
        if event:
            event.accept()

    # endregion


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Disable Qt state restoration help button
    app.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton, True)
    # Session manager attribute is not universally supported, so ignore if not present
    if hasattr(QtCore.Qt, "AA_DisableSessionManager"):
        app.setAttribute(QtCore.Qt.AA_DisableSessionManager, True)

    view = MainApp()
    view.show_and_activate()

    sys.exit(app.exec_())
