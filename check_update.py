import os
import requests
import shelve
from datetime import datetime


class Version:
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.last_checked = self.get_last_checked()
        self.allowed = self.check_allowed()
        self.patch_available = False
        self.newest_version = self.get_newest_version()

    def get_newest_version(self):
        if self.last_checked is False:
            newest_version = self.current_version
        elif self.allowed:
            print('Check allowed')
            # Grab json from github
            print('Checking releases...')
            try:
                r = requests.get(
                    'https://api.github.com/repos/adnv3k/GestureSesh/releases'
                )
                self.r_json = r.json()
            except (Exception, ConnectionError):
                print('Cannot connect to api.github')
                return
            # Get newest version from json
            newest_version = self.r_json[0]['tag_name'][1:]
            print(f'newest_version: {newest_version}')
        else:
            newest_version = self.last_checked[1]
            print('Not allowed (get_newest_version)')
        return newest_version

    def check_allowed(self):
        if self.last_checked is False:
            return False
        # Change format from datetime object to str elements [year, month, day]
        last_checked = str(self.last_checked[0]).split('-')
        now = str(datetime.now().date()).split('-')
        print(
            f'last_checked_date: {last_checked}\n'
            f'Now: {now}'
        )
        # If more than 1 month or 1 days
        print(
            f'Month: {int(now[1])}\n'
            f'last_checked month: {int(last_checked[1])}\n'
            f'Day: {int(now[2])}\n'
            f'last_checked day + 1: {int(last_checked[2]) + 1}'
        )
        if int(now[1]) > int(last_checked[1]) or int(now[2]) > int(last_checked[2]) + 1:
            return True
        print(
            f'Check not allowed',
            f'{int(last_checked[2]) + 1 - int(now[2])} days until allowed'
        )
        os.chdir(r'.\recent')
        f = shelve.open('recent')
        f['last_checked'] = [datetime.now().date(), self.current_version]
        f.close()
        os.chdir(r'..\\')
        return False

    def is_newest(self):
        """
        Checks if the current version is up to date.
        """
        self.save_to_recent()
        print(self.last_checked)
        print(f'current version: {self.current_version}')

        if self.current_version == self.newest_version:
            if self.allowed:
                if 'patch' in self.r_json[0]['name'].lower():
                    print('Patch available')
                    self.patch_available = True
                    if self.is_valid_update():
                        # self.save_to_recent()
                        # print('self.is_valid_update = True. save_to_recent called')
                        return False # version not newest
                print('Up to date')

            return True

        # There is a newer version
        if not self.allowed:
            print('Out of date')
            return True # version is not newest, but self.allowed = False means don't proceed.
        if self.is_valid_update():
            # self.save_to_recent()
            # print('save_to_recent called')
            return False

    def is_valid_update(self):
        if self.r_json[0]['target_commitish'].lower() != 'main':
            return False
        if self.r_json[0]['prerelease']:
            return False
        if self.r_json[0]['draft']:
            return False
        return True

    def get_last_checked(self):
        if not os.path.exists(r'.\recent'):
            print(f'Recent folder not found')
            os.mkdir(r'.\recent')
        os.chdir(r'.\recent')
        f = shelve.open('recent')
        try:
            last_checked = f['last_checked']
            print(f'Save exists. last_checked: {last_checked}')
        except (Exception, KeyError): # First time opening app
            f['last_checked'] = [datetime.now().date(), self.current_version]
            last_checked = False
            print('last_checked not found')
        f.close()
        os.chdir(r'..\\')
        return last_checked

    # Saves date checked
    def save_to_recent(self):
        os.chdir(r'.\recent')
        f = shelve.open('recent')
        f['last_checked'] = [datetime.now().date(), self.newest_version]
        f.close()
        os.chdir(r'..\\')

    def update_type(self):
        if self.patch_available:
            return 'Patch'
        current_version = self.current_version.split('.')
        newest_version = self.newest_version.split('.')
        update_type = None
        for i in range(len(current_version)):
            if int(current_version[i]) < int(newest_version[i]):
                update_type = i
                break
        if update_type == 0:
            return 'Major update'
        elif update_type == 1:
            return 'Feature update'
        elif update_type == 2:
            return 'Minor update'

    def content(self):
        return self.r_json[0]['body']
