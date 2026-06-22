"""Reveal a file in the OS file manager, highlighting it when possible.

Shared by the session window and the Manage Order dialog so their
"open folder" actions land on — and select — the specific image the user is
looking at, instead of merely opening its containing directory.
"""

from __future__ import annotations

import platform
from pathlib import Path

from PyQt5 import QtCore


def reveal_in_file_manager(path: str) -> bool:
    """Open the OS file manager with *path* highlighted.

    On Windows and macOS the file itself is selected; Linux has no portable
    "select" flag, so the containing folder is opened instead. If the file is
    gone, fall back to opening its parent directory so the user still lands
    nearby. Qt resource paths (``:/...``) and empty paths are ignored.

    Returns ``True`` when a command was dispatched, ``False`` otherwise.
    """
    if not path or path.startswith(":/"):
        return False

    resolved = Path(path).resolve()
    system = platform.system()

    if resolved.exists():
        if system == "Windows":
            QtCore.QProcess.startDetached("explorer.exe", ["/select,", str(resolved)])
        elif system == "Darwin":
            QtCore.QProcess.startDetached("open", ["-R", str(resolved)])
        else:  # Linux and other systems: no universal reveal-and-select.
            QtCore.QProcess.startDetached("xdg-open", [str(resolved.parent)])
        return True

    # The file no longer exists; open its folder if that still does.
    parent = resolved.parent
    if not parent.is_dir():
        return False
    if system == "Windows":
        QtCore.QProcess.startDetached("explorer.exe", [str(parent)])
    elif system == "Darwin":
        QtCore.QProcess.startDetached("open", [str(parent)])
    else:
        QtCore.QProcess.startDetached("xdg-open", [str(parent)])
    return True
