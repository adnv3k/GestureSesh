"""Shared constants and helpers for the session display package.

Lives in its own module so submodules (timer, etc.) and the parent
``session_window`` can both import from it without circular dependencies.
"""

import contextlib
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
