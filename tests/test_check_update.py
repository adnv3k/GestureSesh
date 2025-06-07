import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
from datetime import datetime, timedelta
import requests

from check_update import UpdateChecker


class TestUpdateChecker(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for config files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.current_version = "0.3.0"

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("check_update.requests.get")
    def test_check_for_updates_new_version(self, mock_get):
        # Simulate GitHub API response with a newer version (0.4.2)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tag_name": "v0.4.2",
            "body": "Release notes for 0.4.2",
            "html_url": "https://github.com/adnv3k/GestureSesh/releases/tag/v0.4.2",
            "published_at": "2024-06-01T00:00:00Z",
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        checker = UpdateChecker(self.current_version)
        # Override config path to use temp file
        checker.config_path = self.config_path
        checker.config = {}
        update = checker.check_for_updates()
        self.assertIsInstance(update, dict)
        self.assertEqual(update["version"], "0.4.2")
        self.assertIn("Release notes for 0.4.2", update["notes"])

    @patch("check_update.requests.get")
    def test_check_for_updates_no_new_version(self, mock_get):
        # Simulate GitHub API response with same version (0.4.2)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tag_name": "v0.4.2",
            "body": "No updates",
            "html_url": "https://github.com/adnv3k/GestureSesh/releases/tag/v0.4.2",
            "published_at": "2024-06-01T00:00:00Z",
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        checker = UpdateChecker("0.4.2")
        checker.config_path = self.config_path
        checker.config = {}
        update = checker.check_for_updates()
        self.assertIsNone(update)

    def test_is_check_needed_first_time(self):
        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        checker.config = {}
        self.assertTrue(checker._is_check_needed())

    def test_is_check_needed_recent(self):
        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        # Set last_checked to now
        checker.config = {"last_checked": (datetime.now().isoformat())}
        self.assertFalse(checker._is_check_needed())

    def test_is_check_needed_old(self):
        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        old_time = (datetime.now() - timedelta(days=2)).isoformat()
        checker.config = {"last_checked": old_time}
        self.assertTrue(checker._is_check_needed())

    @patch("check_update.requests.get")
    def test_check_for_updates_network_error(self, mock_get):
        # Simulate a realistic network error from the requests library
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        checker.config = {}

        update = checker.check_for_updates()

        # Assert that the function correctly returns None on network failure
        self.assertIsNone(update)

