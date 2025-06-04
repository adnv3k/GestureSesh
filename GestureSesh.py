import os
import sys
import random
import shelve
from pathlib import Path
import cv2
import numpy as np
from pygame import mixer
import subprocess
from dataclasses import dataclass

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import *

from check_update import Version
from main_window import Ui_MainWindow
from session_display import Ui_session_display
import resources_config


@dataclass
class ScheduleEntry:
    images: int
    time: int


__version__ = "0.4.3"

# Adding a folder will now include subdirectories.


class MainApp(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle(f"Reference Practice")
        self.session_schedule = []
        self.has_break = False
        self.valid_file_types = [".bmp", ".jpg", ".jpeg", ".png"]
        self.total_time = 0
        self.total_images = 0
        self.selection = {"folders": [], "files": []}
        self.init_buttons()
        self.init_shortcuts()
        self.init_preset()
        self.load_recent()
        self.check_version()
        self.entry_table.itemChanged.connect(self.update_total)
        self.dialog_buttons.accepted.connect(self.start_session)

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
        self.selected_items.setText(
            f'{len(checked_files["valid_files"])} file(s) added!'
        )
        if len(checked_files["invalid_files"]) > 0:
            self.selected_items.append(
                f'{len(checked_files["invalid_files"])} file(s) not added. '
                f'Supported file types: {", ".join(self.valid_file_types)}.'
            )
            QTest.qWait(500)
        QTest.qWait(3000)
        self.display_status()

    def open_folder(self):
        """
        Calls on self.check_files to check each file in the user selected directories
        Saves folder paths, and file names
        Displays message of result

        """
        # Subclassed QFileDialog
        selected_dir = FileDialog()
        if selected_dir.exec():
            # Example of result
            # ['D:/.../image_displayer/atest2',
            # 'D:/.../image_displayer/atest1']
            total_valid_files, total_invalid_files = 0, 0
            self.selected_items.clear()
            # TODO refactor so that calling os.walk is done just once
            directories = [x[0] for x in os.walk(selected_dir.selectedFiles()[0])]
            total_valid_files, total_invalid_files = self.scan_directories(directories)
            self.selected_items.append(
                f"{total_valid_files} file(s) added from "
                f"{len(directories)} folders!"
            )
            # TODO update error handling here to accomodate subfolder inclusion
            if total_invalid_files > 0:
                self.selected_items.append(
                    f"{total_invalid_files} file(s) not added. "
                    f'Supported file types: {", ".join(self.valid_file_types)}.'
                )
                QTest.qWait(1000)
            QTest.qWait(4000)
            self.display_status()
            return
        self.selected_items.setText(f"0 folder(s) added!")
        QTest.qWait(2000)
        self.display_status()

    def scan_directories(self, directories):
        total_valid_files, total_invalid_files = 0, 0
        for directory in directories:
            if not os.path.exists(directory):
                self.selection["folders"].remove(directory)
                continue
            checked_files = self.check_files([x[2] for x in os.walk(directory)][0])
            total_valid_files += len(checked_files["valid_files"])
            total_invalid_files += len(checked_files["invalid_files"])
            if directory not in self.selection["folders"]:
                self.selection["folders"].append(directory)
            for file in checked_files["valid_files"]:
                self.selection["files"].append(f"{directory}/{file}")
        return total_valid_files, total_invalid_files

    def check_files(self, files):
        """Checks if files are supported file types"""
        res = {"valid_files": [], "invalid_files": []}
        for file in files:
            if (
                file[-4:].lower() not in self.valid_file_types
                and file[-5:].lower() not in self.valid_file_types  # .jpeg
            ):
                # Since the file extension is not a valid file type,
                # add it to list of invalid files.
                res["invalid_files"].append(file)
            else:
                res["valid_files"].append(file)
        return res

    def remove_items(self):
        """Clears entire selection"""
        self.selection["files"].clear()
        self.selection["folders"].clear()
        self.selected_items.setText(f"All files and folders cleared!")
        QTest.qWait(2000)
        self.display_status()

    def remove_dupes(self):
        """
        Iterates through user selection of files while keeping seen files
        in memory.
        If a file has already been seen, it is deleted from the selection.

        """
        self.duplicates = []
        files = []
        i = len(self.selection["files"])
        while i > 0:
            i -= 1
            if os.path.basename(self.selection["files"][i]) in files:
                self.duplicates.append(self.selection["files"].pop(i))
            else:
                files.append(os.path.basename(self.selection["files"][i]))
        self.selected_items.setText(f"Removed {len(self.duplicates)} duplicates!")
        QTest.qWait(2000)
        self.display_status()

    def display_status(self):
        """Displays amount of files, and folders selected"""
        self.selected_items.setText(
            f'{len(self.selection["files"])} total files added from '
            f'{len(self.selection["folders"])} folder(s).'
        )

    def display_random_status(self):
        """Displays the randomization setting"""
        if self.randomize_selection.isChecked():
            self.selected_items.setText(f"Randomization on!")
        else:
            self.selected_items.setText(f"Randomization off!")
        QTest.qWait(2000)
        self.display_status()

    def load_recent(self):
        """
        Loads most recent session settings:
        Selected items
        Preset
        Randomization
        Removes breaks in case entire program closed during a session
        Displays status

        """
        if Path("recent").exists():
            try:
                os.chdir(Path("recent"))
                recent = shelve.open("recent")
                if recent["recent"].get("folders"):
                    self.selection["folders"] = recent["recent"]["folders"]
                    self.scan_directories(self.selection["folders"])
                self.preset_loader_box.setCurrentIndex(recent["recent_preset"])
                self.randomize_selection.setChecked(recent["randomized"])
                recent.close()
                os.chdir(Path(".."))
            except (Exception, KeyError):
                print("load_recent error")
                print(os.getcwd())
                os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
                return
            self.remove_breaks()
            self.display_status()
            self.selected_items.append(f"Recent session settings loaded!")
            self.update_total()

    # endregion

    # region Session Settings
    def append_schedule(self):
        """
        Adds entry information as a new row in the schedule
        Resets scrollboxes to 0.
        Updates total amount.

        """
        row = self.entry_table.rowCount()
        entry = [
            row + 1,  # entry number
            self.set_number_of_images.value(),
            self.set_minutes.value() * 60 + self.set_seconds.value(),
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
                self.selected_items.append("\nSelect a row in the table!")
                QTest.qWait(2000)
                self.display_status()
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
                self.selected_items.append("\nSelect a row in the table!")
                QTest.qWait(2000)
                self.display_status()
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
        # Hours
        hrs = int(sec / 3600)
        self.hrs_list = list(str(hrs))
        if len(self.hrs_list) == 1 or self.hrs_list[0] == "0":
            self.hrs_list.insert(0, "0")
        # Minutes
        minutes = int((sec / 3600 - hrs) * 60)
        self.minutes_list = list(str(minutes))
        if len(self.minutes_list) == 1 or self.minutes_list[0] == "0":
            self.minutes_list.insert(0, "0")
        # Seconds
        self.sec = list(str(int((((sec / 3600 - hrs) * 60) - minutes) * 60)))
        if len(self.sec) == 1 or self.sec[0] == "0":
            self.sec.insert(0, "0")
        return (
            f"{self.hrs_list[0]}{self.hrs_list[1]}:"
            f"{self.minutes_list[0]}{self.minutes_list[1]}:"
            f"{self.sec[0]}{self.sec[1]}"
        )

    # endregion

    # region Presets
    def init_preset(self):
        self.presets = {}
        # If the presets folder does not exist in file directory, then
        # create it and create shelve files there.
        if not Path("presets").exists():
            Path("presets").mkdir(exist_ok=True)
            os.chdir(Path("presets"))
            preset = shelve.open("preset")
            preset.close()
            os.chdir(Path(".."))
        # Load data from preset files then update presets
        else:
            try:
                os.chdir(Path("presets"))
                pre = shelve.open("preset")
                preset_list = list(pre.keys())
                for preset in preset_list:
                    self.presets[preset] = pre[preset]
                pre.close()
                os.chdir(Path(".."))
                self.update_presets()
            except (Exception, KeyError):
                print("init_preset error")
                print(os.getcwd())
                os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))

    def update_presets(self):
        """
        Populates the configuration with preset.
        """
        self.preset_loader_box.clear()
        self.preset_names = []
        for p in [*self.presets]:
            if p not in self.preset_names:
                self.preset_names.append(p)
        self.preset_loader_box.addItems(self.preset_names)
        self.update_total()

    def save(self):
        if self.entry_table.rowCount() <= 0:
            self.selected_items.setText(f"Cannot save an empty schedule!")
            QTest.qWait(4000)
            self.display_status()
            return
        preset_name = self.preset_loader_box.currentText()
        if preset_name == "":
            self.selected_items.setText(f"Cannot save an empty name!")
            QTest.qWait(5500)
            self.display_status()
            return
        # Get table entries
        tmppreset = {}
        for row in range(self.entry_table.rowCount()):
            tmppreset[row] = []
            for column in range(self.entry_table.columnCount()):
                tmppreset[row].append(self.entry_table.item(row, column).text())
        # Save preset to file
        os.chdir(Path("presets"))
        preset = shelve.open("preset")
        preset[preset_name] = tmppreset
        preset.close()
        os.chdir(Path(".."))
        # Load preset to new name
        self.selected_items.setText(f"{preset_name} saved!")
        if self.presets.get(preset_name):
            self.presets[preset_name] = tmppreset
        else:
            self.presets[preset_name] = tmppreset
            self.update_presets()
            self.preset_loader_box.setCurrentIndex(self.preset_loader_box.count() - 1)
        QTest.qWait(3000)
        self.display_status()

    def delete(self):
        preset_name = self.preset_loader_box.currentText()
        if preset_name == "":
            self.selected_items.setText(f"Cannot delete an empty field!")
            QTest.qWait(4000)
            self.display_status()
            return
        os.chdir(Path("presets"))
        preset = shelve.open("preset")
        del preset[preset_name]
        preset.close()
        os.chdir(Path(".."))
        del self.presets[preset_name]
        self.selected_items.setText(f"{preset_name} deleted!")
        self.preset_loader_box.removeItem(self.preset_loader_box.currentIndex())
        QTest.qWait(2000)
        self.display_status()

    def load(self):
        preset_name = self.preset_loader_box.currentText()
        # If the current text in the preset field exists as the key for a saved
        # preset, then update the schedule
        if self.presets.get(preset_name):
            self.remove_rows()
            rows = list(self.presets[preset_name].keys())
            columns = list(self.presets[preset_name][0])
            for row in range(len(rows)):
                self.entry_table.insertRow(row)
                for column in range(len(columns)):
                    item = QTableWidgetItem(self.presets[preset_name][row][column])
                    item.setTextAlignment(4)
                    if column == 0:
                        item.setFlags(QtCore.Qt.ItemIsEnabled)
                    self.entry_table.setItem(row, column, item)

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
        self.selected_items.append(f"Recent session settings saved!")

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
                self.selected_items.setText(f"Schedule items must be numbers!")
                return False

        # Check if empty schedule
        if len(self.session_schedule) == 0:
            self.selected_items.setText(f"Schedule cannot be empty.")
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
                    f'Image removed from selection. {len(self.selection["files"])} total files.'
                )
                self.selected_items.append(
                    f"Previous directory: \n{os.path.dirname(file)}"
                )
                return False

        # Check if there are enough selected images for the schedule
        if self.total_scheduled_images > len(self.selection["files"]):
            self.selected_items.setText(
                f"Not enough images selected. Add more images, or schedule fewer images."
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
        """Removes breaks images from the selection of files"""
        i = len(self.selection["files"])
        while i > 0:
            i -= 1
            if os.path.basename(self.selection["files"][i]) == "break.png":
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
        """Saves current selection, selected preset, and randomization setting"""
        self.recent = {}
        if not Path("recent").exists():
            Path("recent").mkdir(exist_ok=True)
        os.chdir(Path("recent"))
        file = shelve.open("recent")
        file["recent"] = self.selection
        file["recent_preset"] = self.preset_loader_box.currentIndex()
        file["randomized"] = self.randomize_selection.isChecked()
        file.close()
        os.chdir(Path(".."))

    # endregion

    # region
    # Updates
    def check_version(self):
        """
        Checks if the current version is the newest one. If not, an update
        notice is displayed in the display.

        """
        current_version = Version(__version__)
        if not current_version.is_newest():
            update_type = current_version.update_type()
            if type(update_type) == str:
                self.selected_items.append(
                    f"\n{update_type} available!"
                    f"\nPlease visit the site to download!"
                )
                content = current_version.content()
                self.selected_items.append(
                    f"v{current_version.newest_version}\n" f"{content}"
                )
        else:
            if current_version.allowed is True:
                self.selected_items.append(f"Up to date.")

    # endregion


class SessionDisplay(QWidget, Ui_session_display):
    closed = QtCore.pyqtSignal()  # Needed here for close event to work.

    def __init__(self, schedule=None, items=None, total=None):
        super().__init__()
        self.setupUi(self)
        self.init_sizing()
        self.init_scaling_size()
        self.init_button_sizes()
        self.drag_timer_was_active = False
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
        self.init_sounds()
        self.init_mixer()
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
        }

    def init_sounds(self):
        """
        Gets absolute path to sounds.
        PyInstaller creates a temp folder, and stores dependencies path in _MEIPASS.
        If the temp folder is not found, then use the current file path.

        """
        relative_path = "sounds"
        try:
            base_path = sys._MEIPASS
        except (Exception, FileNotFoundError):
            print("Temp folder not found.")
            base_path = os.path.abspath(".")
        self.sounds_dir = os.path.join(base_path, relative_path)

    def init_mixer(self):
        mixer.init()
        try:
            """
            If view.mute exists, then a session has been started before.
            Set mute and volume according to previous session's sound settings.
            """
            if view.mute is True:  # if view.mute exists and is True
                self.mute = True
                self.volume = mixer.music.get_volume()
                mixer.music.set_volume(0.0)
            else:  # if view.mute exists and is False
                self.mute = False
                self.volume = view.volume
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
        self.skip_image_key = QShortcut(QtGui.QKeySequence('S'), self)
        self.skip_image_key.activated.connect(self.skip_image)
        # Frameless Window
        self.frameless_window = QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        self.frameless_window.activated.connect(self.toggle_frameless)

    def closeEvent(self, event):
        """
        Stops timer and sound on close event.
        """
        self.timer.stop()
        self.close_timer.stop()
        view.mute = self.mute
        view.volume = self.volume
        mixer.quit()
        self.closed.emit()
        event.accept()

    def mousePressEvent(self, event):
        """
        Stores the initial cursor position and whether the timer was active
        before any dragging begins.
        """
        self.old_position = event.globalPos()
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
        if not self.session_finished and not self.drag_timer_was_active:
            self.timer.stop()
            self._set_timer_visuals(False)
            self.drag_timer_was_active = True
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
            print(
                "No images to skip on break"
                f" {self.playlist[self.playlist_position]}"
            )
            self.setWindowTitle("No images to skip on break")
            return

        swap_indicies = list(range(self.playlist_position + 1, len(self.playlist)))
        random.shuffle(swap_indicies)
        while swap_indicies:
            swap_index = swap_indicies.pop()
            if self.playlist[swap_index] != "break.png":
                self.playlist[self.playlist_position], self.playlist[swap_index] = self.playlist[swap_index], self.playlist[self.playlist_position]
                break
        else:
            print(
                "No images to skip to"
                f" {self.playlist[self.playlist_position]}"
            )
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
        self.playlist_position = max(0, len(self.playlist) - 1)
        self.timer_display.setText(f"Done! Closing in {self.close_seconds}s...")
        self.update_close_title()
        self.close_timer.start(1000)

    def load_next_image(self):
        was_timer_active = self.timer.isActive()
        self.timer.stop()
        if self.session_finished:
            self.cancel_close_countdown()
            self.timer.blockSignals(True)
            if self.playlist_position >= len(self.playlist) - 1:
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
            self.update_timer_display()
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

    def display_image(self):
        print(self.entry)
        # Sounds

        if self.new_entry:
            sound_file = Path(self.sounds_dir) / "new_entry.mp3"
            mixer.music.load(str(sound_file))
            mixer.music.play()
            # self.new_entry = False
        elif self.entry["amount of items"] == 0:  # Last image in entry
            sound_file = Path(self.sounds_dir) / "last_entry_image.mp3"
            mixer.music.load(str(sound_file))
            mixer.music.play()
        elif self.entry["time"] > 10:
            sound_file = Path(self.sounds_dir) / "new_image.mp3"
            mixer.music.load(str(sound_file))
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
                os.path.basename(self.playlist[self.playlist_position]) == "break.png"
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
            cvimage = cv2.imread(self.playlist[self.playlist_position])

        # Handle if cvimage is None or empty
        if cvimage is None or cvimage.size == 0:
            print(
                f"Error: Could not load image at {self.playlist[self.playlist_position]}"
            )
            self.setWindowTitle("Error processing image")
            return

        try:
            height, width, channels = cvimage.shape
            # Ensure channels is 1 (grayscale), 3 (BGR), or 4 (BGRA)
            if channels not in (1, 3, 4):
                raise ValueError(f"Unexpected channel count: {channels}")
            bytes_per_line = channels * width
        except (AttributeError, ValueError, BufferError) as e:
            print(f"Error processing image: {e}")
            self.setWindowTitle("Error processing image")
            return

        # Grayscale
        if self.image_mods["grayscale"] or self.image_mods["break_grayscale"]:
            cvimage = cv2.cvtColor(cvimage, cv2.COLOR_BGR2GRAY)
            self.image = QtGui.QImage(
                cvimage.data, width, height, width, QtGui.QImage.Format_Grayscale8
            )
        else:
            self.image = QtGui.QImage(
                cvimage.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888
            ).rgbSwapped()

        # Flip
        if self.image_mods["hflip"]:
            self.image = self.image.mirrored(horizontal=True)
            if not self.image_mods["vflip"]:
                self.image = self.image.mirrored(vertical=True)
            else:
                self.image = self.image.mirrored(vertical=False)
        else:
            self.image = self.image.mirrored(horizontal=False)
            if not self.image_mods["vflip"]:
                self.image = self.image.mirrored(vertical=True)
            else:
                self.image = self.image.mirrored(vertical=False)

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

    def flip_horizontal(self):
        if self.image_mods["hflip"]:
            self.image_mods["hflip"] = False
        else:
            self.image_mods["hflip"] = True
        self.display_image()

    def flip_vertical(self):
        if self.image_mods["vflip"]:
            self.image_mods["vflip"] = False
        else:
            self.image_mods["vflip"] = True
        self.display_image()

    def grayscale(self):
        if self.image_mods["grayscale"]:
            self.image_mods["grayscale"] = False
        else:
            self.image_mods["grayscale"] = True
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
                return
            self.playlist_position -= 1
            self.display_image()
            self._set_timer_visuals(True)
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
                mixer.music.load(os.path.join(self.sounds_dir, "halfway.mp3"))
                mixer.music.play()
        if self.time_seconds <= 10:
            if self.new_entry is False and self.end_of_entry is False:
                if self.time_seconds == 10:
                    mixer.music.load(os.path.join(self.sounds_dir, "first_alert.mp3"))
                    mixer.music.play()
                elif self.time_seconds == 5:
                    mixer.music.load(os.path.join(self.sounds_dir, "second_alert.mp3"))
                    mixer.music.play()
                elif self.time_seconds == 0.5:
                    mixer.music.load(os.path.join(self.sounds_dir, "third_alert.mp3"))
                    mixer.music.play()
            else:
                if self.new_entry is True:
                    self.new_entry = False
                if self.end_of_entry is True:
                    self.end_of_entry = False
            if os.path.basename(self.playlist[self.playlist_position]) == "break.png":
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

    def _set_timer_visuals(self, running: bool) -> None:
        """Update pause button and display border based on running state."""
        if running:
            self.pause_timer.setIcon(QtGui.QIcon(":/icons/icons/Pause.png"))
            self.pause_timer.setStyleSheet(
                "background: rgb(100, 120, 118); padding:2px; border:1px solid transparent;"
            )
            self.timer_display.setStyleSheet("color: white;")
        else:
            self.pause_timer.setIcon(QtGui.QIcon(":/icons/icons/Play2.png"))
            self.pause_timer.setStyleSheet(
                "background: rgb(100, 120, 118); padding:2px; border:1px solid white;"
            )
            self.timer_display.setStyleSheet("color: white; border:1px solid white;")

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
        directory = os.path.dirname(path)
        if sys.platform.startswith("darwin"):
            subprocess.call(["open", "-R", path])
        elif os.name == "nt":
            subprocess.call(["explorer", "/select,", path.replace("/", "\\")])
        if sys.platform.startswith("linux"):
            subprocess.call(["xdg-open", directory])
        if event:
            event.accept()

    # endregion


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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QtWidgets.QApplication.setStyle("Fusion")
    view = MainApp()
    view.show()
    sys.exit(app.exec())
