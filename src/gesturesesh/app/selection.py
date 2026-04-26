"""Selection and file-loading behavior for the main window."""

from __future__ import annotations

import os

from PyQt5.QtWidgets import QFileDialog

from gesturesesh.app.file_dialog import FileDialog


class MainAppSelectionMixin:
    """Selection management methods mixed into ``MainApp``."""

    def open_files(self):
        selected_files = QFileDialog().getOpenFileNames()
        checked_files = self.check_files(selected_files[0])
        self.selection["files"].extend(checked_files["valid_files"])

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
        Calls on self.check_files to check each file in the user selected directories.
        Saves folder paths and file names. Displays a message of the result.
        """
        selected_dir = FileDialog()
        if selected_dir.exec():
            directories = selected_dir.selectedFiles()
            total_valid_files, total_invalid_files = self.scan_directories(directories)

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

        self.show_temporary_status("0 folder(s) added!", 2000)

    def scan_directories(self, directories):
        """Scan directories and collect valid files from all subfolders, robust to symlinks, permissions, and case."""
        total_valid_files, total_invalid_files = 0, 0
        visited = set()
        seen_paths = set()

        allowed_dirs = [os.path.abspath(d) for d in directories]

        def is_within_allowed_dirs(path, allowed_dirs):
            abs_path = os.path.abspath(path)
            return any(
                abs_path.startswith(folder + os.sep) or abs_path == folder
                for folder in allowed_dirs
            )

        for directory in directories:
            if not os.path.exists(directory):
                if directory in self.selection["folders"]:
                    self.selection["folders"].remove(directory)
                continue
            if directory not in self.selection["folders"]:
                self.selection["folders"].append(directory)
            for root, dirs, files in os.walk(directory, followlinks=True):
                try:
                    stat = os.stat(root)
                    key = (stat.st_dev, stat.st_ino)
                    if key not in visited:
                        visited.add(key)
                except OSError:
                    continue

                potential_files = self.check_files(
                    [os.path.join(root, f) for f in files]
                )
                total_invalid_files += len(potential_files["invalid_files"])

                for file in potential_files["valid_files"]:
                    try:
                        stat = os.stat(file)
                        file_key = (stat.st_dev, stat.st_ino, file)

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

    def check_files(self, files):
        """Checks if files are supported file types and are accessible."""
        res = {"valid_files": [], "invalid_files": []}
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in self.valid_file_types:
                res["invalid_files"].append(file)
                continue
            if os.path.isfile(file):
                res["valid_files"].append(file)
            else:
                res["invalid_files"].append(file)
        return res

    def remove_items(self):
        """Clears entire selection."""
        self.selection["files"].clear()
        self.selection["folders"].clear()
        self.show_temporary_status("All files and folders cleared!", 2000)

    def remove_dupes(self):
        """Remove duplicate files from selection (case-sensitive)."""
        if not self.selection["files"]:
            self.show_temporary_status("No files to check for duplicates")
            return

        original_count = len(self.selection["files"])
        seen_files = set()
        unique_files = []

        for file_path in self.selection["files"]:
            try:
                stat = os.stat(file_path)
                file_key = (stat.st_dev, stat.st_ino, file_path)

                if file_key not in seen_files:
                    seen_files.add(file_key)
                    unique_files.append(file_path)
            except (OSError, PermissionError):
                unique_files.append(file_path)

        self.selection["files"] = unique_files
        removed_count = original_count - len(unique_files)

        if removed_count > 0:
            self.show_temporary_status(f"Removed {removed_count} duplicate file(s)")
        else:
            self.show_temporary_status("No duplicates found")

        self.display_status()
