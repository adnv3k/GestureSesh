#!/usr/bin/env python3
"""
Enhanced test suite for UpdateChecker changelog parsing functionality.
Combines unit tests with debugging capabilities for changelog parsing.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add the src directory to sys.path to import gesturesesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

try:
    from gesturesesh.update_checker import UpdateChecker
    import requests
except ImportError as e:
    print(f"Warning: Could not import dependencies: {e}")
    print("This test requires the gesturesesh.update_checker module and requests library.")
    sys.exit(1)


class TestUpdateCheckerChangelog(unittest.TestCase):
    """Test suite for UpdateChecker with focus on changelog parsing."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.current_version = "0.4.0"  # Simulate being on an older version

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_changelog_parsing_with_real_data(self):
        """Test changelog parsing with actual GitHub data."""
        print("\n=== Testing Changelog Parsing with Real Data ===")
        
        checker = UpdateChecker(self.current_version)
        
        # Test different version formats
        test_versions = ["v0.5.0", "0.5.0"]
        
        for version in test_versions:
            print(f"\nTesting version format: {version}")
            notes = checker._fetch_changelog_notes(version)
            print(f"Extracted notes (first 200 chars): {notes[:200]}...")
            
            # Verify we got meaningful content
            self.assertIsInstance(notes, str, "Notes should be a string")
            self.assertGreater(len(notes), 10, "Notes should have substantial content")
            
            # Check for expected content patterns
            if "### Added" in notes or "Enhanced dot indicator" in notes:
                print("✅ Successfully parsed actual changelog content")
                self.assertIn("### Added", notes, "Should contain changelog sections")
            elif "New version" in notes:
                print("✅ Got fallback message (expected when version not found)")
                self.assertIn("New version", notes, "Should contain fallback message")
            else:
                print("⚠️ Unexpected content format")

    def test_changelog_parsing_patterns(self):
        """Test different changelog format patterns."""
        print("\n=== Testing Changelog Format Patterns ===")
        
        # Mock changelog content with different formats
        mock_changelog_formats = [
            # Format 1: [v0.5.0] - date
            """
## [Unreleased]

### Added
- New features

## [v0.5.0] - 2025-01-15

### Added
- Enhanced dot indicator with customizable themes
- Improved session display capabilities

### Changed
- Updated UI components

## [v0.4.0] - 2024-12-01
""",
            # Format 2: v0.5.0 - date
            """
## Unreleased

### Added
- New features

## v0.5.0 - 2025-01-15

### Added
- Enhanced dot indicator with customizable themes
- Improved session display capabilities

### Changed
- Updated UI components

## v0.4.0 - 2024-12-01
""",
            # Format 3: Just version number
            """
## Unreleased

## v0.5.0

### Added
- Enhanced dot indicator with customizable themes
- Improved session display capabilities

## v0.4.0
"""
        ]
        
        checker = UpdateChecker(self.current_version)
        
        for i, changelog_content in enumerate(mock_changelog_formats):
            print(f"\nTesting format {i+1}...")
            
            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.text = changelog_content
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                notes = checker._fetch_changelog_notes("v0.5.0")
                
                print(f"Extracted: {notes[:100]}...")
                
                # Should find the version section
                self.assertIn("DotIndicator", notes, 
                             f"Should parse format {i+1} correctly")
                self.assertIn("### Added", notes, 
                             f"Should include section headers for format {i+1}")

    @patch("builtins.open", side_effect=FileNotFoundError("Local file not found"))
    @patch("gesturesesh.update_checker.Path.exists", return_value=False)
    def test_changelog_network_error_handling(self, mock_exists, mock_open):
        """Test graceful handling when both network and local file access fail."""
        print("\n=== Testing Network Error Handling ===")
        
        checker = UpdateChecker(self.current_version)
        notes = checker._fetch_changelog_notes("v0.5.0")
        
        print(f"Fallback notes: {notes}")
        
        # Should return a fallback message when both network and local fail
        self.assertIn("Unable to fetch detailed release notes", notes)
        self.assertIn("v0.5.0", notes)

    @patch("builtins.open", side_effect=FileNotFoundError("Local file not found"))
    @patch("gesturesesh.update_checker.Path.exists", return_value=False)
    def test_changelog_parsing_error_handling(self, mock_exists, mock_open):
        """Test handling when changelog content cannot be accessed."""
        print("\n=== Testing Malformed Content Handling ===")
        
        checker = UpdateChecker(self.current_version)
        notes = checker._fetch_changelog_notes("v0.5.0")
        
        print(f"Fallback notes: {notes}")
        
        # Should return fallback when no content can be accessed
        self.assertIn("Unable to fetch detailed release notes", notes)

    @patch("gesturesesh.update_checker.requests.get")
    def test_full_update_check_with_changelog(self, mock_get):
        """Test complete update check flow with changelog integration."""
        print("\n=== Testing Full Update Check Flow ===")
        
        # Mock GitHub API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tag_name": "v0.5.0",
            "html_url": "https://github.com/adnv3k/GestureSesh/releases/tag/v0.5.0",
            "published_at": "2025-01-15T10:00:00Z"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        checker.config = {}  # Reset config to ensure check is needed
        
        update_info = checker.check_for_updates()
        
        self.assertIsNotNone(update_info, "Should detect available update")
        self.assertEqual(update_info["version"], "0.5.0")
        
        print(f"Update info: {update_info}")
        print(f"Release notes preview: {update_info['notes'][:200]}...")
        
        # Verify changelog content is included (local file should be used)
        self.assertIn("macOS support", update_info["notes"])
        self.assertIn("### Added", update_info["notes"])


class TestUpdateCheckerCore(unittest.TestCase):
    """Core UpdateChecker functionality tests (originally from test_check_update.py)."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.current_version = "0.3.0"

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    @patch("gesturesesh.update_checker.requests.get")
    def test_check_for_updates_new_version(self, mock_get):
        """Test detection of new version availability."""
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
        checker.config_path = self.config_path
        checker.config = {}
        update = checker.check_for_updates()
        
        self.assertIsInstance(update, dict)
        self.assertEqual(update["version"], "0.4.2")
        # Should now contain changelog content instead of GitHub release body
        self.assertIn("Mute now works properly", update["notes"])

    @patch("gesturesesh.update_checker.requests.get")
    def test_check_for_updates_no_new_version(self, mock_get):
        """Test behavior when no new version is available."""
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
        """Test that check is needed on first run."""
        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        checker.config = {}
        self.assertTrue(checker._is_check_needed())

    def test_is_check_needed_recent(self):
        """Test that check is not needed when recently checked."""
        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        checker.config = {"update_check": {"last_checked": datetime.now().isoformat()}}
        self.assertFalse(checker._is_check_needed())

    def test_is_check_needed_old(self):
        """Test that check is needed when last check was old."""
        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        old_time = (datetime.now() - timedelta(days=2)).isoformat()
        checker.config = {"update_check": {"last_checked": old_time}}
        self.assertTrue(checker._is_check_needed())

    @patch("gesturesesh.update_checker.requests.get")
    def test_check_for_updates_network_error(self, mock_get):
        """Test graceful handling of network errors during update check."""
        # Simulate a realistic network error from the requests library
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        checker = UpdateChecker(self.current_version)
        checker.config_path = self.config_path
        checker.config = {}

        update = checker.check_for_updates()
        self.assertIsNone(update)


def debug_changelog_patterns():
    """Debug function to test changelog patterns interactively."""
    print("\n" + "="*60)
    print("CHANGELOG PATTERN DEBUGGING")
    print("="*60)
    
    # Test with actual GitHub changelog
    GITHUB_CHANGELOG_URL = "https://raw.githubusercontent.com/adnv3k/GestureSesh/main/CHANGELOG.md"
    
    try:
        response = requests.get(GITHUB_CHANGELOG_URL, timeout=10)
        response.raise_for_status()
        changelog_content = response.text
        
        print(f"✅ Fetched changelog ({len(changelog_content)} chars)")
        
        # Show first 40 lines
        lines = changelog_content.split('\n')
        print("\nFirst 40 lines of changelog:")
        for i, line in enumerate(lines[:40]):
            print(f"{i+1:2}: {repr(line)}")
        
        # Test pattern matching
        version_tag = "v0.5.0"
        clean_version = version_tag.lstrip('v')
        
        patterns = [
            f"## [v{clean_version}] -",    # [v0.5.0] - date
            f"## [{clean_version}] -",     # [0.5.0] - date
            f"## [v{clean_version}]",      # [v0.5.0]
            f"## [{clean_version}]",       # [0.5.0]
            f"## v{clean_version} -",      # v0.5.0 - date
            f"## {clean_version} -",       # 0.5.0 - date
            f"## v{clean_version}",        # v0.5.0
            f"## {clean_version}"          # 0.5.0
        ]
        
        print(f"\nTesting patterns for version: {version_tag}")
        print("-" * 50)
        
        for pattern in patterns:
            print(f"\nPattern: {repr(pattern)}")
            pattern_escaped = re.escape(pattern)
            
            # Simple search
            if re.search(pattern_escaped, changelog_content, re.MULTILINE):
                print("  ✅ Pattern found in changelog")
                
                # Try full extraction
                match = re.search(
                    rf'^{pattern_escaped}.*?\n\n(.*?)(?=\n## |$)', 
                    changelog_content, 
                    re.MULTILINE | re.DOTALL
                )
                
                if match:
                    content = match.group(1).strip()
                    print(f"  ✅ Successfully extracted {len(content)} chars")
                    print(f"  Preview: {content[:100]}...")
                    return content
                else:
                    print("  ❌ Pattern found but extraction failed")
            else:
                print("  ❌ Pattern not found")
        
        print("\n❌ No patterns matched")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def run_interactive_tests():
    """Run tests with interactive output."""
    print("GestureSesh Update Checker - Enhanced Test Suite")
    print("=" * 50)
    
    # Run debug patterns first
    debug_result = debug_changelog_patterns()
    
    # Run unit tests
    print("\n" + "="*60)
    print("RUNNING UNIT TESTS")
    print("="*60)
    
    # Create a test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestUpdateCheckerChangelog)
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if debug_result:
        print("✅ Changelog pattern debugging successful")
    else:
        print("⚠️ Changelog pattern debugging had issues")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_interactive_tests()
    sys.exit(0 if success else 1)
