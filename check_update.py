import os
import json
import platform
from pathlib import Path
from typing import Optional, Dict, Any, TypedDict
from datetime import datetime, timedelta
from collections import OrderedDict

from PyQt5.QtWidgets import QMainWindow
import requests
from packaging import version

# --- App-Specific Constants ---
APP_NAME = "GestureSesh"
GITHUB_REPO = "adnv3k/GestureSesh"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


# --- Define a structured dictionary for update information ---
class UpdateInfo(TypedDict):
    """A dictionary containing details of an available update."""

    version: str
    notes: str
    url: str
    pub_date: str


# --- Platform-Specific Configuration Path ---
def get_config_dir() -> Path:
    """Returns the cross-platform application data directory."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support" / APP_NAME
    elif system == "Windows":
        # The 'APPDATA' environment variable points to C:\Users\<user>\AppData\Roaming
        return Path(os.getenv("APPDATA", "")) / APP_NAME
    else:  # Linux and other Unix-likes
        return Path.home() / ".config" / APP_NAME


# --- Configuration File Handling (using JSON) ---
def load_config(app: QMainWindow) -> Dict[str, Any]:
    """Loads configuration from a JSON file."""
    path = get_config_dir() / "config.json"
    # Check if config file exists for first-time launch
    if not path.exists():
        config = {}
        # Save a default config to mark as initialized
        app.selected_items.clear()
        save_config(path, config)
        return {}

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
        # Ensure 'update_check' is first, then all other keys in their original order
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


class UpdateChecker:
    """
    Handles checking for application updates in a safe and efficient manner.
    """

    def __init__(self, current_version: str):
        self.current_v = version.parse(current_version)
        self.config_path = get_config_dir() / "config.json"
        self.config = load_config(self.config_path)

    def _is_check_needed(self) -> bool:
        last_checked_str = self.config.get("update_check", {}).get("last_checked")
        if not last_checked_str:
            return True

        try:
            last_checked_dt = datetime.fromisoformat(last_checked_str)
            return datetime.now() - last_checked_dt > timedelta(hours=24)
        except ValueError:
            return True
        except ValueError:
            print("Invalid date format in config for 'last_checked'. Checking again.")
            return True

    def check_for_updates(self) -> Optional[UpdateInfo]:
        """
        Checks for the latest release on GitHub if needed.

        Returns:
            An UpdateInfo dictionary if a new version is available, otherwise None.
        """
        if not self._is_check_needed():
            return None

        try:
            response = requests.get(GITHUB_RELEASES_URL, timeout=10)
            response.raise_for_status()

            data = response.json()
            latest_tag = data.get("tag_name", "").lstrip("v")
            if not latest_tag:
                return None

            latest_v = version.parse(latest_tag)

            # Update the check timestamp regardless
            self.config.setdefault("update_check", {})[
                "last_checked"
            ] = datetime.now().isoformat()
            self.config["update_check"]["cached_version"] = latest_tag
            save_config(self.config_path, self.config)

            if latest_v > self.current_v:
                return UpdateInfo(
                    version=str(latest_v),
                    notes=data.get("body", "No release notes provided."),
                    url=data.get("html_url", ""),
                    pub_date=data.get("published_at", ""),
                )

        except requests.exceptions.RequestException:
            return None

        return None
