"""Shared constants and helpers for the session display package.

Lives in its own module so submodules (timer, etc.) and the parent
``session_window`` can both import from it without circular dependencies.
"""

import contextlib
import os
from importlib import resources
from pathlib import Path


BREAK_IMAGE_PATH = ":/break/break.png"

SUPPORTED_IMAGE_TYPES = {
    ".avif",
    ".bmp",
    ".gif",
    ".jxl",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

SUPPORTED_ANIMATED_TYPES = {".avif", ".gif", ".jxl", ".webp"}


def is_hidden_file(path) -> bool:
    """Return True for hidden/sidecar files that should not be treated as images.

    Matches any dotfile (basename starting with ``.``). The important case is the
    macOS AppleDouble sidecar ``._name.ext``: it mirrors a real file's extension
    (so an extension check alone accepts it) but holds resource-fork metadata
    rather than image data. These are generated when files are copied to
    FAT/exFAT/SMB/USB volumes and, if added to the playlist, fail to decode at
    display time. Other dotfiles (``.DS_Store``, ``.thumbnails``, etc.) are OS
    noise too, so we skip the whole class.
    """
    return os.path.basename(str(path)).startswith(".")


def sound_file(name: str):
    """Return a context manager yielding the path to an embedded sound file."""
    try:
        return resources.as_file(resources.files("sounds") / name)
    except ModuleNotFoundError:
        print("ModuleNotFoundError in sound_file")
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        sound_path = project_root / "sounds" / name

        @contextlib.contextmanager
        def sound_file_context():
            yield str(sound_path)

        return sound_file_context()
