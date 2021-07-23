import os, sys
os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))
import requests
import shelve
from datetime import datetime

class Version():
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        self.get_last_checked()
        self.get_newest_version()

    def get_newest_version(self):
        if self.check_allowed():
            # Grab json from github
            try:
                r = requests.get('https://api.github.com/repos/adnv3k/Image-Queuer/releases')
                self.r_json = r.json()
            except:
                print('Cannot connect to api.github')
                return

            # Get newest version from json
            self.newest_version = self.r_json[0]['tag_name'][1:]
        else:
            self.newest_version = self.last_checked[1]

    def check_allowed(self):
        if self.last_checked == False:
            return True
        # Change format from datetime object to str elements [year, month, day]
        last_checked = str(self.last_checked[0]).split('-')
        now = str(datetime.now().date()).split('-')
        # If more than 1 month or 3 days
        if int(now[1]) > int(last_checked[1]) or int(now[2]) > int(last_checked[2])+2:
            return True

        return False

    def is_newest(self):
        if self.current_version == self.newest_version:
            return True
        if self.is_valid_update():
            self.save_to_recent()
            print('savetorecent called')
            return False
    
    def is_valid_update(self):
        if self.r_json[0]['target_commitish'] != 'main':
            return False
        if self.r_json[0]['prerelease'] != 'false':
            return False
        if self.r_json[0]['draft'] != 'false':
            return False
        return True

    def get_last_checked(self):
        if not os.path.exists(r'.\recent'):
            os.mkdir(r'.\recent')
        os.chdir(r'.\recent')
        f = shelve.open('recent')
        try:
            self.last_checked = f['last_checked']
        except:
            f['last_checked'] = [datetime.now().date(),self.current_version]
            self.last_checked = False
        f.close()
        os.chdir(r'..\\')

    # Saves date checked
    def save_to_recent(self):
        os.chdir(r'.\recent')
        f = shelve.open('recent')
        f['last_checked'] = [datetime.now().date(),self.newest_version]
        f.close()
        os.chdir(r'..\\')
        
    def update_type(self):
        current_version = self.current_version.split('.')
        newest_version = self.newest_version.split('.')
        update_type = None
        for i in range(len(current_version)):
            if int(current_version[i]) < int(newest_version[i]):
                update_type = i
                break
        if update_type == 0:
            return 'Major'
        elif update_type == 1:
            return 'Feature'
        elif update_type == 2:
            return 'Minor'
    def content(self):
        return self.r_json[0]['body']
