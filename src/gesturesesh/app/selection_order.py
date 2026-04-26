"""Selection ordering helpers shared by the main and session windows."""

from __future__ import annotations

import os
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from gesturesesh.session.constants import BREAK_IMAGE_PATH


@dataclass(frozen=True)
class SelectionStats:
    total_files: int
    folder_count: int
    scheduled_images: int
    extra_images: int
    shortage_images: int
    missing_files: int
    duplicate_files: int
    extension_counts: dict[str, int]


def scheduled_image_count(schedule) -> int:
    """Return the number of real images required by a schedule."""
    return sum(max(0, int(getattr(entry, "images", 0))) for entry in schedule or [])


def effective_selection_order(files, randomize=False, rng=None) -> list[str]:
    """Return the order a session should use without mutating the source list."""
    ordered = [path for path in files if path != BREAK_IMAGE_PATH]
    if randomize:
        shuffled = list(ordered)
        (rng or random).shuffle(shuffled)
        return shuffled
    return ordered


def playlist_with_breaks(files, schedule, break_path=BREAK_IMAGE_PATH) -> list[str]:
    """Return a session playlist with break placeholders inserted."""
    playlist = list(files)
    current_index = 0
    for entry in schedule or []:
        image_count = int(getattr(entry, "images", 0))
        if image_count == 0:
            playlist.insert(current_index, break_path)
            current_index += 1
        else:
            current_index += image_count
    return playlist


def real_image_paths(files) -> list[str]:
    """Return only user-selected images, excluding internal break markers."""
    return [path for path in files if path != BREAK_IMAGE_PATH]


def duplicate_indices(files) -> set[int]:
    """Return indices after the first occurrence of the same filesystem target."""
    seen = set()
    duplicates = set()
    for index, file_path in enumerate(files):
        if file_path == BREAK_IMAGE_PATH:
            continue
        try:
            stat = os.stat(file_path)
            key = (stat.st_dev, stat.st_ino)
        except (OSError, PermissionError):
            key = os.path.normcase(os.path.abspath(file_path))
        if key in seen:
            duplicates.add(index)
        else:
            seen.add(key)
    return duplicates


def remove_duplicate_paths(files) -> list[str]:
    """Keep the first occurrence of each duplicate target."""
    duplicates = duplicate_indices(files)
    return [path for index, path in enumerate(files) if index not in duplicates]


def selection_stats(files, folders=None, schedule=None) -> SelectionStats:
    """Compute summary information used by the selection viewer."""
    real_files = real_image_paths(files)
    scheduled = scheduled_image_count(schedule)
    missing = sum(1 for path in real_files if not Path(path).is_file())
    duplicate_count = len(duplicate_indices(real_files))
    extensions = Counter(Path(path).suffix.lower() or "(none)" for path in real_files)
    extra = max(0, len(real_files) - scheduled) if scheduled else len(real_files)
    shortage = max(0, scheduled - len(real_files))

    return SelectionStats(
        total_files=len(real_files),
        folder_count=len(folders or []),
        scheduled_images=scheduled,
        extra_images=extra,
        shortage_images=shortage,
        missing_files=missing,
        duplicate_files=duplicate_count,
        extension_counts=dict(sorted(extensions.items())),
    )


def remaining_required_images(schedule, playlist, playlist_position) -> int:
    """Return remaining real image slots from the current playlist position."""
    if not schedule:
        return len(real_image_paths(playlist[playlist_position:]))

    required = 0
    cursor = 0
    for entry in schedule:
        count = int(getattr(entry, "images", 0))
        slots = count if count > 0 else 1
        for slot_offset in range(slots):
            playlist_index = cursor + slot_offset
            if playlist_index < playlist_position:
                continue
            if count > 0:
                required += 1
        cursor += slots
    return required
