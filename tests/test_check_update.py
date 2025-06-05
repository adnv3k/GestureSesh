import unittest
from unittest.mock import patch, MagicMock

from check_update import Version

# Patch sys.modules to avoid actual shelve and requests usage
with patch.dict('sys.modules', {'shelve': __import__('shelve'), 'requests': __import__('requests')}):
    class TestVersion(unittest.TestCase):
        @patch('check_update.shelve.open')
        def test_get_last_checked_no_file(self, mock_shelve_open):
            # Simulate no last_checked in shelve
            mock_db = {}
            mock_shelve_open.return_value.__enter__.return_value = mock_db
            v = Version('1.0.0')
            self.assertIn(v.last_checked, (False, [unittest.mock.ANY, '1.0.0']))

        @patch('check_update.shelve.open')
        def test_get_last_checked_existing(self, mock_shelve_open):
            # Simulate existing last_checked in shelve
            mock_db = {'last_checked': ['2024-01-01', '1.0.0']}
            mock_shelve_open.return_value.__enter__.return_value = mock_db
            v = Version('1.0.0')
            self.assertEqual(v.last_checked, ['2024-01-01', '1.0.0'])

        @patch('check_update.requests.get')
        @patch('check_update.shelve.open')
        def test_get_newest_version_allowed(self, mock_shelve_open, mock_requests_get):
            # Simulate allowed check and GitHub response
            mock_db = {'last_checked': ['2024-01-01', '1.0.0']}
            mock_shelve_open.return_value.__enter__.return_value = mock_db
            mock_response = MagicMock()
            mock_response.json.return_value = [{'tag_name': 'v1.2.3', 'name': 'Release', 'target_commitish': 'main', 'prerelease': False, 'draft': False}]
            mock_response.raise_for_status.return_value = None
            mock_requests_get.return_value = mock_response

            v = Version('1.0.0')
            v.allowed = True
            newest = v.get_newest_version()
            self.assertEqual(newest, '1.2.3')

        @patch('check_update.requests.get')
        @patch('check_update.shelve.open')
        def test_get_newest_version_not_allowed(self, mock_shelve_open, mock_requests_get):
            mock_db = {'last_checked': ['2024-01-01', '1.0.0']}
            mock_shelve_open.return_value.__enter__.return_value = mock_db
            v = Version('1.0.0')
            v.allowed = False
            v.last_checked = ['2024-01-01', '1.1.0']
            newest = v.get_newest_version()
            self.assertEqual(newest, '1.1.0')

        @patch('check_update.requests.get')
        @patch('check_update.shelve.open')
        def test_is_newest_patch(self, mock_shelve_open, mock_requests_get):
            mock_db = {'last_checked': ['2024-01-01', '1.0.0']}
            mock_shelve_open.return_value.__enter__.return_value = mock_db
            mock_response = MagicMock()
            mock_response.json.return_value = [{
                'tag_name': 'v1.0.0',
                'name': 'Patch release',
                'target_commitish': 'main',
                'prerelease': False,
                'draft': False,
                'body': 'Patch notes'
            }]
            mock_response.raise_for_status.return_value = None
            mock_requests_get.return_value = mock_response

            v = Version('1.0.0')
            v.allowed = True
            v.r_json = mock_response.json.return_value
            v.newest_version = '1.0.0'
            self.assertFalse(v.is_newest())
            self.assertTrue(v.patch_available)

        @patch('check_update.requests.get')
        @patch('check_update.shelve.open')
        def test_is_valid_update(self, mock_shelve_open, mock_requests_get):
            mock_db = {'last_checked': ['2024-01-01', '1.0.0']}
            mock_shelve_open.return_value.__enter__.return_value = mock_db
            v = Version('1.0.0')
            v.r_json = [{
                'tag_name': 'v1.1.0',
                'name': 'Release',
                'target_commitish': 'main',
                'prerelease': False,
                'draft': False
            }]
            self.assertTrue(v.is_valid_update())
            v.r_json[0]['target_commitish'] = 'dev'
            self.assertFalse(v.is_valid_update())
            v.r_json[0]['target_commitish'] = 'main'
            v.r_json[0]['prerelease'] = True
            self.assertFalse(v.is_valid_update())
            v.r_json[0]['prerelease'] = False
            v.r_json[0]['draft'] = True
            self.assertFalse(v.is_valid_update())

        def test_update_type(self):
            v = Version('1.0.0')
            v.newest_version = '2.0.0'
            self.assertEqual(v.update_type(), 'Major update')
            v.newest_version = '1.1.0'
            self.assertEqual(v.update_type(), 'Feature update')
            v.newest_version = '1.0.1'
            self.assertEqual(v.update_type(), 'Minor update')
            v.newest_version = '1.0.0'
            self.assertIsNone(v.update_type())
            v.patch_available = True
            self.assertEqual(v.update_type(), 'Patch')

        def test_content(self):
            v = Version('1.0.0')
            v.r_json = [{'body': 'Release notes'}]
            self.assertEqual(v.content(), 'Release notes')
            v.r_json = None
            self.assertEqual(v.content(), '')

if __name__ == '__main__':
    unittest.main()