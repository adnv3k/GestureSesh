import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import random
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
)

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gesturesesh.app.models import ScheduleEntry
from gesturesesh.app.selection_order import (
    effective_selection_order,
    playlist_with_breaks,
    remaining_required_images,
    selection_stats,
)
from gesturesesh.session_window import BREAK_IMAGE_PATH
from gesturesesh.ui.dialogs import ImageManagerDialog


class TestSelectionOrderHelpers(unittest.TestCase):
    def test_effective_selection_order_randomizes_copy(self):
        items = ["a.jpg", "b.jpg", "c.jpg"]
        rng = random.Random(10)
        ordered = effective_selection_order(items, randomize=True, rng=rng)

        assert items == ["a.jpg", "b.jpg", "c.jpg"]
        assert Counter(ordered) == Counter(items)

    def test_playlist_with_breaks_does_not_mutate_files(self):
        items = ["a.jpg", "b.jpg", "c.jpg"]
        schedule = [
            ScheduleEntry(images=2, time=30),
            ScheduleEntry(images=0, time=15),
            ScheduleEntry(images=1, time=30),
        ]

        playlist = playlist_with_breaks(items, schedule)

        assert items == ["a.jpg", "b.jpg", "c.jpg"]
        assert playlist == ["a.jpg", "b.jpg", BREAK_IMAGE_PATH, "c.jpg"]

    def test_selection_stats_counts_missing_duplicates_and_schedule(self):
        with tempfile.TemporaryDirectory() as tempdir:
            existing = os.path.join(tempdir, "image.JPG")
            Path(existing).touch()
            missing = os.path.join(tempdir, "missing.png")
            files = [existing, existing, missing]
            schedule = [ScheduleEntry(images=4, time=30)]

            stats = selection_stats(files, folders=[tempdir], schedule=schedule)

            assert stats.total_files == 3
            assert stats.folder_count == 1
            assert stats.scheduled_images == 4
            assert stats.shortage_images == 1
            assert stats.missing_files == 1
            assert stats.duplicate_files == 1
            assert stats.extension_counts[".jpg"] == 2
            assert stats.extension_counts[".png"] == 1

    def test_remaining_required_images_counts_from_current_position(self):
        schedule = [
            ScheduleEntry(images=2, time=30),
            ScheduleEntry(images=0, time=15),
            ScheduleEntry(images=2, time=30),
        ]
        playlist = ["a.jpg", "b.jpg", BREAK_IMAGE_PATH, "c.jpg", "d.jpg"]

        assert remaining_required_images(schedule, playlist, 0) == 4
        assert remaining_required_images(schedule, playlist, 2) == 2
        assert remaining_required_images(schedule, playlist, 3) == 2


class TestImageManagerDialogLogic(unittest.TestCase):
    def test_move_buttons_reorder_unlocked_selection(self):
        dialog = ImageManagerDialog(
            parent=None,
            files=["a.jpg", "b.jpg", "c.jpg"],
            valid_file_types={".jpg"},
        )
        dialog._reselect_indices([1])

        dialog._move_selected(-1)
        assert dialog.working_files == ["b.jpg", "a.jpg", "c.jpg"]

        dialog._move_to_edge(1)
        assert dialog.working_files == ["a.jpg", "c.jpg", "b.jpg"]

    def test_locked_and_break_rows_are_not_removed_or_moved(self):
        dialog = ImageManagerDialog(
            parent=None,
            files=["shown.jpg", BREAK_IMAGE_PATH, "upcoming.jpg"],
            valid_file_types={".jpg"},
            locked_until=0,
        )
        dialog._reselect_indices([0, 1, 2])

        dialog._remove_selected()
        assert dialog.working_files == ["shown.jpg", BREAK_IMAGE_PATH]

        dialog._reselect_indices([1])
        dialog._move_selected(-1)
        assert dialog.working_files == ["shown.jpg", BREAK_IMAGE_PATH]

    def test_check_files_filters_to_supported_existing_images(self):
        with tempfile.TemporaryDirectory() as tempdir:
            image = os.path.join(tempdir, "image.jpg")
            text = os.path.join(tempdir, "notes.txt")
            Path(image).touch()
            Path(text).touch()
            dialog = ImageManagerDialog(
                parent=None,
                files=[],
                valid_file_types={".jpg"},
            )

            assert dialog._check_files([image, text]) == [image]

    def test_thumbnail_queue_is_limited_to_visible_rows(self):
        with tempfile.TemporaryDirectory() as tempdir:
            image_paths = []
            image = QtGui.QImage(16, 16, QtGui.QImage.Format_RGB32)
            image.fill(QtGui.QColor("red"))
            for index in range(80):
                path = os.path.join(tempdir, f"image_{index}.png")
                image.save(path)
                image_paths.append(path)

            dialog = ImageManagerDialog(
                parent=None,
                files=image_paths,
                valid_file_types={".png"},
            )
            dialog._queue_visible_thumbnails()

            assert 0 < len(dialog._pending_thumbnail_rows) < len(image_paths)
