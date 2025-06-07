import os
import json
import platform
from pathlib import Path
from typing import Optional, Dict, Any, TypedDict
from datetime import datetime, timedelta

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
def load_config(path: Path) -> Dict[str, Any]:
    """Loads configuration from a JSON file."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Failed to load or parse config file at {path}: {e}")
        return {}


def save_config(path: Path, config: Dict[str, Any]):
    """Saves configuration to a JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
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
        """Determines if an update check should be performed based on time."""
        last_checked_str = self.config.get("last_checked")
        if not last_checked_str:
            print("No last check time found. A check is needed.")
            return True

        try:
            last_checked_dt = datetime.fromisoformat(last_checked_str)
            if datetime.now() - last_checked_dt > timedelta(hours=24):
                print(
                    "More than 24 hours have passed since the last check. A check is"
                    " needed."
                )
                return True
        except ValueError:
            print("Invalid date format in config for 'last_checked'. Checking again.")
            return True

        # print("An update check was performed within the last 24 hours. Skipping.")
        return False

    def check_for_updates(self) -> Optional[UpdateInfo]:
        """
        Checks for the latest release on GitHub if needed.

        Returns:
            An UpdateInfo dictionary if a new version is available, otherwise None.
        """
        if not self._is_check_needed():
            return None

        print(f"Checking for new releases at {GITHUB_RELEASES_URL}...")
        try:
            # We specifically ask for the 'latest' release, which is the most recent
            # non-prerelease, non-draft release.
            response = requests.get(GITHUB_RELEASES_URL, timeout=10)
            response.raise_for_status()

            # Update the check timestamp regardless of whether an update is found
            self.config["last_checked"] = datetime.now().isoformat()
            save_config(self.config_path, self.config)

            data = response.json()
            latest_tag = data.get("tag_name", "").lstrip("v")
            if not latest_tag:
                print("Latest release found has no tag name.")
                return None

            latest_v = version.parse(latest_tag)

            print(
                f"Current version: {self.current_v}, Latest version found: {latest_v}"
            )

            if latest_v > self.current_v:
                print(f"A new version is available: {latest_v}")
                update_info: UpdateInfo = {
                    "version": str(latest_v),
                    "notes": data.get("body", "No release notes provided."),
                    "url": data.get("html_url", ""),
                    "pub_date": data.get("published_at", ""),
                }
                return update_info

        except requests.exceptions.RequestException as e:
            print(f"Update check failed due to a network error: {e}")
            # Don't update the timestamp on failure, so it will try again next time.
            return None
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Failed to parse API response from GitHub: {e}")
            return None

        return None
