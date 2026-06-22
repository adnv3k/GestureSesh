"""Tests for reveal_in_file_manager (utils/file_reveal.py)."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from gesturesesh.utils.file_reveal import reveal_in_file_manager


class TestRevealInFileManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.file = os.path.join(self.tmp, "img.png")
        with open(self.file, "w") as f:
            f.write("x")
        self.resolved = str(Path(self.file).resolve())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _patches(self, system):
        return (
            patch("gesturesesh.utils.file_reveal.platform.system", lambda: system),
            patch("gesturesesh.utils.file_reveal.QtCore.QProcess.startDetached"),
        )

    def test_windows_selects_file(self):
        sys_patch, start_patch = self._patches("Windows")
        with sys_patch, start_patch as mock_start:
            self.assertTrue(reveal_in_file_manager(self.file))
            mock_start.assert_called_once_with(
                "explorer.exe", ["/select,", self.resolved]
            )

    def test_macos_reveals_file(self):
        sys_patch, start_patch = self._patches("Darwin")
        with sys_patch, start_patch as mock_start:
            self.assertTrue(reveal_in_file_manager(self.file))
            mock_start.assert_called_once_with("open", ["-R", self.resolved])

    def test_linux_opens_parent(self):
        sys_patch, start_patch = self._patches("Linux")
        with sys_patch, start_patch as mock_start:
            self.assertTrue(reveal_in_file_manager(self.file))
            mock_start.assert_called_once_with(
                "xdg-open", [str(Path(self.resolved).parent)]
            )

    def test_resource_path_ignored(self):
        sys_patch, start_patch = self._patches("Darwin")
        with sys_patch, start_patch as mock_start:
            self.assertFalse(reveal_in_file_manager(":/break.png"))
            mock_start.assert_not_called()

    def test_empty_path_ignored(self):
        sys_patch, start_patch = self._patches("Darwin")
        with sys_patch, start_patch as mock_start:
            self.assertFalse(reveal_in_file_manager(""))
            mock_start.assert_not_called()

    def test_missing_file_falls_back_to_folder(self):
        missing = os.path.join(self.tmp, "gone.png")
        sys_patch, start_patch = self._patches("Darwin")
        with sys_patch, start_patch as mock_start:
            self.assertTrue(reveal_in_file_manager(missing))
            mock_start.assert_called_once_with(
                "open", [str(Path(missing).resolve().parent)]
            )

    def test_missing_file_and_folder_returns_false(self):
        missing = os.path.join(self.tmp, "nope", "gone.png")
        sys_patch, start_patch = self._patches("Darwin")
        with sys_patch, start_patch as mock_start:
            self.assertFalse(reveal_in_file_manager(missing))
            mock_start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
