import os
import requests
import shelve
from datetime import datetime
import platform
from pathlib import Path
from typing import Optional, Any

# --- Cross-platform user data directory ---
if platform.system() == "Darwin":
    BASE_DIR = Path.home() / "Library/Application Support/GestureSesh"
elif platform.system() == "Windows":
    BASE_DIR = Path(os.getenv("APPDATA")) / "GestureSesh"
else:
    BASE_DIR = Path.home() / ".config" / "GestureSesh"

RECENT_DIR = BASE_DIR / "recent"
RECENT_DIR.mkdir(parents=True, exist_ok=True)

GITHUB_RELEASES_URL = 'https://api.github.com/repos/adnv3k/GestureSesh/releases'

class Version:
    def __init__(self, current_version: str):
        self.current_version = current_version
        self.last_checked = self.get_last_checked()
        self.allowed = self.check_allowed()
        self.patch_available = False
        self.r_json: Optional[Any] = None
        self.newest_version = self.get_newest_version()

    def get_newest_version(self) -> str:
        if self.last_checked is False:
            return self.current_version
        if self.allowed:
            print('Check allowed')
            print('Checking releases...')
            try:
                r = requests.get(GITHUB_RELEASES_URL, timeout=5)
                r.raise_for_status()
                self.r_json = r.json()
                if not self.r_json or not isinstance(self.r_json, list):
                    print('No releases found.')
                    return self.current_version
            except Exception as e:
                print(f'Cannot connect to GitHub: {e}')
                return self.current_version
            newest_version = self.r_json[0].get('tag_name', '')[1:] or self.current_version
            print(f'newest_version: {newest_version}')
            return newest_version
        else:
            newest_version = self.last_checked[1]
            print('Not allowed (get_newest_version)')
            return newest_version

    def check_allowed(self) -> bool:
        if self.last_checked is False:
            return False
        last_checked = str(self.last_checked[0]).split('-')
        now = str(datetime.now().date()).split('-')
        print(f'last_checked_date: {last_checked}\nNow: {now}')
        # Allow check if a new month or more than 1 day has passed
        if int(now[1]) > int(last_checked[1]) or int(now[2]) > int(last_checked[2]) + 1:
            return True
        print(
            f'Check not allowed',
            f'{int(last_checked[2]) + 1 - int(now[2])} days until allowed'
        )
        with shelve.open(str(RECENT_DIR / "recent")) as f:
            f['last_checked'] = [datetime.now().date(), self.current_version]
        return False

    def is_newest(self) -> bool:
        """
        Checks if the current version is up to date.
        """
        self.save_to_recent()
        print(self.last_checked)
        print(f'current version: {self.current_version}')

        if self.current_version == self.newest_version:
            if self.allowed and self.r_json:
                if 'patch' in self.r_json[0].get('name', '').lower():
                    print('Patch available')
                    self.patch_available = True
                    if self.is_valid_update():
                        return False # version not newest
                print('Up to date')
            return True

        # There is a newer version
        if not self.allowed:
            print('Out of date')
            return True # version is not newest, but self.allowed = False means don't proceed.
        if self.is_valid_update():
            return False
        return True

    def is_valid_update(self) -> bool:
        if not self.r_json or not isinstance(self.r_json, list):
            return False
        release = self.r_json[0]
        if release.get('target_commitish', '').lower() != 'main':
            return False
        if release.get('prerelease'):
            return False
        if release.get('draft'):
            return False
        return True

    def get_last_checked(self):
        if not RECENT_DIR.exists():
            print(f'Recent folder not found')
            RECENT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with shelve.open(str(RECENT_DIR / "recent")) as f:
                last_checked = f.get('last_checked', False)
                if last_checked:
                    print(f'Save exists. last_checked: {last_checked}')
                else:
                    f['last_checked'] = [datetime.now().date(), self.current_version]
                    print('last_checked not found')
                    return False
                return last_checked
        except Exception as e:
            print(f"Error accessing recent: {e}")
            return False

    def save_to_recent(self):
        try:
            with shelve.open(str(RECENT_DIR / "recent")) as f:
                f['last_checked'] = [datetime.now().date(), self.newest_version]
        except Exception as e:
            print(f"Error saving to recent: {e}")

    def update_type(self) -> Optional[str]:
        if self.patch_available:
            return 'Patch'
        current_version = self.current_version.split('.')
        newest_version = self.newest_version.split('.')
        update_type = None
        for i in range(min(len(current_version), len(newest_version))):
            try:
                if int(current_version[i]) < int(newest_version[i]):
                    update_type = i
                    break
            except ValueError:
                continue
        if update_type == 0:
            return 'Major update'
        elif update_type == 1:
            return 'Feature update'
        elif update_type == 2:
            return 'Minor update'
        return None

    def content(self) -> str:
        if self.r_json and isinstance(self.r_json, list):
            return self.r_json[0].get('body', '')
        return ''
