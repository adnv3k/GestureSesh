"""GitHub release polling with throttling, plus changelog extraction."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TypedDict

import requests
from packaging import version

from gesturesesh.utils.config import get_config_dir, load_config, save_config


GITHUB_REPO = "adnv3k/GestureSesh"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_CHANGELOG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/CHANGELOG.md"


class UpdateInfo(TypedDict):
    """A dictionary containing details of an available update."""

    version: str
    notes: str
    url: str
    pub_date: str


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

        try:
            local_changelog_path = Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"
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

        try:
            clean_version = version_tag.lstrip('v')

            version_patterns = [
                f"## [v{clean_version}] -",
                f"## [{clean_version}] -",
                f"## [v{clean_version}]",
                f"## [{clean_version}]",
                f"## v{clean_version} -",
                f"## {clean_version} -",
                f"## v{clean_version}",
                f"## {clean_version}"
            ]

            for pattern in version_patterns:
                pattern_escaped = re.escape(pattern)
                patterns_to_try = [
                    rf'^{pattern_escaped}.*?\n\n(.*?)(?=\n## |\Z)',
                    rf'^{pattern_escaped}.*?\n(.*?)(?=\n## |\Z)'
                ]

                for regex_pattern in patterns_to_try:
                    match = re.search(regex_pattern, changelog_content, re.MULTILINE | re.DOTALL)

                    if match:
                        notes = match.group(1).strip()
                        if notes and len(notes) > 10:
                            lines = []
                            for line in notes.split('\n'):
                                line = line.strip()
                                if line:
                                    lines.append(line)

                            if lines:
                                formatted_notes = '\n'.join(lines)
                                return formatted_notes

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

            self.config.setdefault("update_check", {})[
                "last_checked"
            ] = datetime.now().isoformat()
            self.config["update_check"]["cached_version"] = latest_tag
            save_config(self.config_path, self.config)

            if latest_v > self.current_v:
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
