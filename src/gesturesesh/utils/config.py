"""Cross-platform config-file location and JSON load/save."""

import json
import os
import platform
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict


APP_NAME = "GestureSesh"


def get_config_dir() -> Path:
    """Returns the cross-platform application data directory."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library/Application Support" / APP_NAME
    elif system == "Windows":
        return Path(os.getenv("APPDATA", "")) / APP_NAME
    else:
        return Path.home() / ".config" / APP_NAME


def load_config(config_path_or_app) -> Dict[str, Any]:
    """Loads configuration from a JSON file.

    Accepts either a Path or a MainApp instance (legacy signature). When given
    an app, it locates the default config and clears the selected_items widget
    on first launch.
    """
    if hasattr(config_path_or_app, 'selected_items'):
        app = config_path_or_app
        path = get_config_dir() / "config.json"
        if not path.exists():
            config = {}
            app.selected_items.clear()
            save_config(path, config)
            return {}
    else:
        path = config_path_or_app

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Failed to load or parse config file at {path}: {e}")
        return {}


def save_config(path: Path, config: Dict[str, Any]):
    """Saves configuration to a JSON file with 'update_check' as the first key."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        ordered = OrderedDict()
        if "update_check" in config:
            ordered["update_check"] = config["update_check"]
        if "recent_session" in config:
            ordered["recent_session"] = config["recent_session"]
        for k, v in config.items():
            if k not in ["update_check", "recent_session"]:
                ordered[k] = v
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ordered, f, indent=4)
    except IOError as e:
        print(f"Failed to save config file at {path}: {e}")
