"""Hidden dotfiles and macOS AppleDouble sidecars (``._name.ext``) must never be
treated as images: they share a real file's extension but hold metadata, so they
would be added to the playlist and then fail to decode at display time."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

from gesturesesh.app.selection import MainAppSelectionMixin
from gesturesesh.session.constants import is_hidden_file


class TestIsHiddenFile(unittest.TestCase):
    def test_appledouble_and_dotfiles_are_hidden(self):
        for path in (
            "/photos/._image1.jpg",
            "._image1.jpg",
            "/photos/.DS_Store",
            "/photos/.hidden.png",
        ):
            self.assertTrue(is_hidden_file(path), path)

    def test_normal_files_are_not_hidden(self):
        for path in (
            "/photos/image1.jpg",
            "image1.jpg",
            "/photos/my._weird.jpg",  # only a leading "._" basename counts
            "/a.dotted.dir/image.png",
        ):
            self.assertFalse(is_hidden_file(path), path)


class TestCheckFilesSkipsHidden(unittest.TestCase):
    """Exercises the real ``MainAppSelectionMixin.check_files``."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.fake = types.SimpleNamespace(
            valid_file_types={".jpg", ".jpeg", ".png", ".bmp"}
        )

    def _make(self, name):
        path = os.path.join(self.tmp, name)
        Path(path).touch()
        return path

    def test_appledouble_excluded_silently(self):
        real = self._make("image1.jpg")
        sidecar = self._make("._image1.jpg")
        ds_store = self._make(".DS_Store")

        result = MainAppSelectionMixin.check_files(
            self.fake, [real, sidecar, ds_store]
        )

        self.assertEqual(result["valid_files"], [real])
        # Hidden files are skipped silently, not reported as "unsupported".
        self.assertEqual(result["invalid_files"], [])

    def test_unsupported_extension_still_reported(self):
        real = self._make("image1.jpg")
        doc = self._make("notes.txt")

        result = MainAppSelectionMixin.check_files(self.fake, [real, doc])

        self.assertEqual(result["valid_files"], [real])
        self.assertEqual(result["invalid_files"], [doc])


if __name__ == "__main__":
    unittest.main()
