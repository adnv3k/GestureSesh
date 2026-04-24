# main.py - GestureSesh main application module

import sys
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsOpacityEffect,
    QMainWindow,
    QShortcut,
)

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from gesturesesh.app.models import ScheduleEntry, StatusMessage
from gesturesesh.app.presets import MainAppPresetsMixin
from gesturesesh.app.selection import MainAppSelectionMixin
from gesturesesh.app.session import MainAppSessionMixin
from gesturesesh.app.status import MainAppStatusMixin
from gesturesesh.session_window import (
    BREAK_IMAGE_PATH,
    SUPPORTED_IMAGE_TYPES,
    SessionDisplay,
)
from gesturesesh.update_checker import UpdateChecker, load_config, save_config
from gesturesesh.ui.main_window import Ui_MainWindow
from gesturesesh.utils import resources_config  # noqa: F401


__version__ = "0.5.1"


class MainApp(
    MainAppSelectionMixin,
    MainAppStatusMixin,
    MainAppPresetsMixin,
    MainAppSessionMixin,
    QMainWindow,
    Ui_MainWindow,
):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Reference Practice")
        self.config = load_config(self)
        self.session_schedule = []
        self.has_break = False
        self.valid_file_types = set(SUPPORTED_IMAGE_TYPES)
        self.selection = {"files": [], "folders": []}

        self.status_timer = QtCore.QTimer()
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(self.display_status)

        self.status_messages = []
        self.current_animation_group = None
        self.showing_default_status = True

        self.status_update_timer = QtCore.QTimer()
        self.status_update_timer.setSingleShot(True)
        self.status_update_timer.timeout.connect(self._update_status_display_text)

        self.status_opacity_effect = QGraphicsOpacityEffect()
        self.selected_items.setGraphicsEffect(self.status_opacity_effect)

        self.init_buttons()
        self.init_shortcuts()
        self.init_preset()
        self.load_recent()
        self.check_version()
        self.entry_table.itemChanged.connect(self.update_total)
        self.dialog_buttons.accepted.connect(self.start_session)
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
        """Removes breaks images from the selection of files"""
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

    def show_and_activate(self):
        self.show()
        self.raise_()
        self.activateWindow()


def main():
    """Main entry point for the GestureSesh application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    app.setAttribute(QtCore.Qt.AA_DisableWindowContextHelpButton, True)
    if hasattr(QtCore.Qt, "AA_DisableSessionManager"):
        app.setAttribute(QtCore.Qt.AA_DisableSessionManager, True)

    view = MainApp()
    view.show_and_activate()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
