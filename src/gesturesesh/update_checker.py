import os
import json
import platform
from pathlib import Path
from typing import Optional, Dict, Any, TypedDict
from datetime import datetime, timedelta
from collections import OrderedDict
import re

from PyQt5.QtWidgets import QMainWindow
import requests
from packaging import version

# --- App-Specific Constants ---
APP_NAME = "GestureSesh"
GITHUB_REPO = "adnv3k/GestureSesh"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_CHANGELOG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/CHANGELOG.md"


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
def load_config(config_path_or_app) -> Dict[str, Any]:
    """Loads configuration from a JSON file."""
    # Handle both old signature (app) and new signature (path)
    if hasattr(config_path_or_app, 'selected_items'):
        # Old signature: app object passed
        app = config_path_or_app
        path = get_config_dir() / "config.json"
        # Check if config file exists for first-time launch
        if not path.exists():
            config = {}
            # Save a default config to mark as initialized
            app.selected_items.clear()
            save_config(path, config)
            return {}
    else:
        # New signature: path object passed
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

    def _fetch_changelog_notes(self, version_tag: str) -> str:
        """
        Fetches release notes from local CHANGELOG.md for the specified version.
        
        Args:
            version_tag: The version tag (e.g., 'v0.5.0' or '0.5.0')
            
        Returns:
            Formatted release notes from changelog, or fallback message if not found.
        """
        changelog_content = None
        
        # Read local changelog file
        try:
            # Navigate up from src/gesturesesh/ to project root for CHANGELOG.md
            local_changelog_path = Path(__file__).parent.parent.parent / "CHANGELOG.md"
            if local_changelog_path.exists():
                with open(local_changelog_path, 'r', encoding='utf-8') as f:
                    changelog_content = f.read()
                print(f"✅ Using local changelog file: {local_changelog_path}")
            else:
                print(f"❌ Local changelog not found at: {local_changelog_path}")
                return f"New version {version_tag} is available! Unable to fetch detailed release notes."
        except Exception as e:
            print(f"❌ Error reading local changelog: {e}")
            return f"New version {version_tag} is available! Unable to fetch detailed release notes."
        
        # Parse the changelog content
        try:
            # Clean the version tag
            clean_version = version_tag.lstrip('v')
            
            # Try to find the version section in changelog
            version_patterns = [
                f"## [v{clean_version}] -",    # Standard GitHub format: ## [v0.5.0] - 2025-01-15
                f"## [{clean_version}] -",     # Alternative: ## [0.5.0] - 2025-01-15
                f"## [v{clean_version}]",      # Just version: ## [v0.5.0]
                f"## [{clean_version}]",       # Just version: ## [0.5.0]
                f"## v{clean_version} -",      # Standard format: ## v0.5.0 - 2025-07-05
                f"## {clean_version} -",       # Alternative: ## 0.5.0 - 2025-07-05
                f"## v{clean_version}",        # Just version: ## v0.5.0
                f"## {clean_version}"          # Just version: ## 0.5.0
            ]
            
            for pattern in version_patterns:
                # Use regex to find the version section and extract content until next version
                pattern_escaped = re.escape(pattern)
                # Try two different patterns: one with empty line after header, one without
                patterns_to_try = [
                    rf'^{pattern_escaped}.*?\n\n(.*?)(?=\n## |\Z)',  # With empty line
                    rf'^{pattern_escaped}.*?\n(.*?)(?=\n## |\Z)'     # Without empty line
                ]
                
                for regex_pattern in patterns_to_try:
                    match = re.search(regex_pattern, changelog_content, re.MULTILINE | re.DOTALL)
                    
                    if match:
                        notes = match.group(1).strip()
                        if notes and len(notes) > 10:  # Ensure we have substantial content
                            # Clean up the notes - remove extra whitespace and format nicely
                            lines = []
                            for line in notes.split('\n'):
                                line = line.strip()
                                if line:
                                    lines.append(line)
                            
                            if lines:
                                # Join with proper formatting
                                formatted_notes = '\n'.join(lines)
                                return formatted_notes
            
            # If no specific version found, return a generic message
            return f"New version {version_tag} is available! Check the changelog for details."
            
        except Exception as e:
            print(f"Error parsing changelog: {e}")
            return f"New version {version_tag} is available! Check the release page for details."

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
                # Get release notes from changelog instead of GitHub release body
                changelog_notes = self._fetch_changelog_notes(data.get("tag_name", ""))
                
                return UpdateInfo(
                    version=str(latest_v),
                    notes=changelog_notes,
                    url=data.get("html_url", ""),
                    pub_date=data.get("published_at", ""),
                )

        except requests.exceptions.RequestException:
            return None

        return None
