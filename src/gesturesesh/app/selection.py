"""Selection and file-loading behavior for the main window."""

from __future__ import annotations

import os
import importlib

from gesturesesh.app.file_dialog import FileDialog
from gesturesesh.session_window import BREAK_IMAGE_PATH
from gesturesesh.ui.dialogs import run_image_manager_dialog


class MainAppSelectionMixin:
    """Selection management methods mixed into ``MainApp``."""

    def open_files(self):
        main_module = importlib.import_module("gesturesesh.main")
        selected_files = main_module.QFileDialog().getOpenFileNames()
        if not selected_files or not selected_files[0]:
            self.show_temporary_status("0 file(s) added!", 2000)
            return

        checked_files = self.check_files(selected_files[0])
        keys_seen = {}
        for existing_file in self.selection["files"]:
            key = self._file_identity_key(existing_file)
            keys_seen[key] = keys_seen.get(key, 0) + 1

        duplicate_count = 0
        for file_path in checked_files["valid_files"]:
            key = self._file_identity_key(file_path)
            if keys_seen.get(key, 0) > 0:
                duplicate_count += 1
            keys_seen[key] = keys_seen.get(key, 0) + 1

        self.selection["files"].extend(checked_files["valid_files"])
        added = len(checked_files["valid_files"])

        self.show_temporary_status(
            f"{added} file(s) added."
            + (
                f" {duplicate_count} duplicate(s) detected."
                if duplicate_count > 0
                else ""
            ),
            4000,
        )

        if len(checked_files["invalid_files"]) > 0:
            self.show_temporary_status(
                f'{len(checked_files["invalid_files"])} file(s) not added. '
                f'Supported file types: {", ".join(sorted(self.valid_file_types))}.',
                duration_ms=4000,
                is_error=True,
            )

    def open_folder(self):
        """
        Calls on self.check_files to check each file in the user selected directories
        Saves folder paths, and file names
        Displays message of result

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
                    f'Supported file types: {", ".join(sorted(self.valid_file_types))}.',
                    duration_ms=4000,
                    is_error=True,
                )
            return

        self.show_temporary_status("0 folder(s) added!", 2000)

    def scan_directories(self, directories):
        """Scan a list of directories and collect valid files from all subfolders, robust to symlinks, permissions, and case."""
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

    def _file_identity_key(self, file_path):
        try:
            stat = os.stat(file_path)
            return ("inode", stat.st_dev, stat.st_ino)
        except (OSError, PermissionError):
            return ("path", os.path.normcase(os.path.abspath(file_path)))

    def _duplicate_indices(self, file_paths):
        index_by_key = {}
        for index, file_path in enumerate(file_paths):
            key = self._file_identity_key(file_path)
            index_by_key.setdefault(key, []).append(index)

        duplicates = set()
        for indices in index_by_key.values():
            if len(indices) > 1:
                duplicates.update(indices)
        return duplicates

    def remove_items(self):
        """Clears entire selection"""
        self.selection["files"].clear()
        self.selection["folders"].clear()
        self.show_temporary_status("All files and folders cleared!", 2000)

    def _is_session_window_open(self):
        display = getattr(self, "display", None)
        if display is None:
            return False
        try:
            return bool(display.isVisible())
        except RuntimeError:
            return False

    def open_image_manager(self):
        files = [f for f in self.selection["files"] if f != BREAK_IMAGE_PATH]
        if not files:
            self.show_temporary_status("No loaded images to manage.", 2000)
            return

        notice_text = None
        if self._is_session_window_open():
            notice_text = (
                "Changes in this window do not affect the current session. "
                "They apply the next time you start a session."
            )

        updated_files = run_image_manager_dialog(
            parent=self,
            files=files,
            duplicate_indices_fn=self._duplicate_indices,
            on_no_duplicates=lambda: self.show_temporary_status("No duplicates found.", 2000),
            notice_text=notice_text,
        )
        if updated_files is None:
            return

        self.selection["files"] = updated_files
        self.display_status()
        self.show_temporary_status(
            f"{len(self.selection['files'])} image(s) in current selection.", 2500
        )

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
