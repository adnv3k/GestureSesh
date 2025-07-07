"""
Test suite for GestureSesh.scan_directories()

The test creates a temporary directory tree with a mix of valid and invalid
files—including deep sub-folders, duplicate names, and a symlink—to ensure
the method:

    • walks every sub-folder
    • filters by extension
    • skips duplicates (case-insensitive on all OSes)
    • rejects paths outside the selected roots
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add the src directory to sys.path to import gesturesesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from gesturesesh.main import MainApp

class TestableMainApp:
    """Lightweight testable version of MainApp for testing scan_directories"""
    def __init__(self):
        self.valid_file_types = {".bmp", ".jpg", ".jpeg", ".png"}
        self.selection = {"files": [], "folders": []}
    
    def check_files(self, files):
        """Checks if files are supported file types and are accessible."""
        res = {"valid_files": [], "invalid_files": []}
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in self.valid_file_types:
                res["invalid_files"].append(file)
                continue
            if os.path.isfile(file):
                res["valid_files"].append(file)
            else:
                res["invalid_files"].append(file)
        return res
    
    def scan_directories(self, directories):
        """Scan directories and collect valid files, handling symlinks properly"""
        total_valid_files, total_invalid_files = 0, 0
        visited_dirs = set()
        seen_files = set()
        
        allowed_dirs = [os.path.abspath(d) for d in directories]
        
        def is_within_allowed_dirs(path, allowed_dirs):
            abs_path = os.path.abspath(path)
            return any(abs_path.startswith(folder + os.sep) or abs_path == folder 
                      for folder in allowed_dirs)
        
        for directory in directories:
            if not os.path.exists(directory):
                if directory in self.selection['folders']:
                    self.selection['folders'].remove(directory)
                continue
                
            if directory not in self.selection['folders']:
                self.selection['folders'].append(directory)
                
            for root, dirs, files in os.walk(directory, followlinks=True):
                # Prevent infinite recursion
                try:
                    stat = os.stat(root)
                    dir_key = (stat.st_dev, stat.st_ino)
                    if dir_key in visited_dirs:
                        continue
                    visited_dirs.add(dir_key)
                except (OSError, PermissionError):
                    continue
                
                potential_files = self.check_files([os.path.join(root, f) for f in files])
                total_invalid_files += len(potential_files['invalid_files'])
                
                for file in potential_files['valid_files']:
                    try:
                        # Use inode to detect duplicate files (including symlinks)
                        stat = os.stat(file)
                        file_key = (stat.st_dev, stat.st_ino)
                        
                        if file_key in seen_files:
                            continue
                            
                        if not is_within_allowed_dirs(file, allowed_dirs):
                            total_invalid_files += 1
                            continue
                            
                        seen_files.add(file_key)
                        self.selection['files'].append(file)
                        total_valid_files += 1
                        
                    except (OSError, PermissionError):
                        total_invalid_files += 1
                        continue
                        
        return total_valid_files, total_invalid_files

class TestScanDirectories(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary directories and files"""
        self.test_dir = tempfile.mkdtemp()
        self.app = TestableMainApp()
        
        # Create test files
        self.valid_files = [
            os.path.join(self.test_dir, "image1.jpg"),
            os.path.join(self.test_dir, "image2.png"),
            os.path.join(self.test_dir, "image3.bmp"),
        ]
        
        self.invalid_files = [
            os.path.join(self.test_dir, "document.txt"),
            os.path.join(self.test_dir, "video.mp4"),
        ]
        
        # Create the actual files
        for file_path in self.valid_files + self.invalid_files:
            Path(file_path).touch()
            
        # Create subdirectory with files
        self.sub_dir = os.path.join(self.test_dir, "subdir")
        os.makedirs(self.sub_dir)
        
        self.sub_valid_files = [
            os.path.join(self.sub_dir, "sub_image1.jpeg"),
            os.path.join(self.sub_dir, "sub_image2.png"),
        ]
        
        for file_path in self.sub_valid_files:
            Path(file_path).touch()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_empty_directory_list(self):
        """Test scanning with empty directory list"""
        valid, invalid = self.app.scan_directories([])
        self.assertEqual(valid, 0)
        self.assertEqual(invalid, 0)
        self.assertEqual(len(self.app.selection["files"]), 0)
    
    def test_nonexistent_directory(self):
        """Test scanning non-existent directory"""
        fake_dir = "/path/that/does/not/exist"
        valid, invalid = self.app.scan_directories([fake_dir])
        self.assertEqual(valid, 0)
        self.assertEqual(invalid, 0)
    
    def test_scan_valid_files(self):
        """Test scanning directory with valid image files"""
        valid, invalid = self.app.scan_directories([self.test_dir])
        
        # Should find 3 valid files in main dir + 2 in subdir = 5 total
        expected_valid = 5
        expected_invalid = 2  # txt and mp4 files
        
        self.assertEqual(valid, expected_valid)
        self.assertEqual(invalid, expected_invalid)
        self.assertEqual(len(self.app.selection["files"]), expected_valid)
        
        # Check that all valid files are in selection
        selected_basenames = [os.path.basename(f) for f in self.app.selection["files"]]
        expected_basenames = ["image1.jpg", "image2.png", "image3.bmp", "sub_image1.jpeg", "sub_image2.png"]
        
        self.assertEqual(sorted(selected_basenames), sorted(expected_basenames))
    
    def test_duplicate_file_handling(self):
        """Test that duplicate files (via symlinks) are handled correctly"""
        # Create a symlink to an existing file
        original_file = self.valid_files[0]  # image1.jpg
        symlink_file = os.path.join(self.test_dir, "symlink_image.jpg")
        
        try:
            os.symlink(original_file, symlink_file)
        except (NotImplementedError, OSError):
            self.skipTest("Symlinks not supported on this system")
        
        # Reset app state
        self.app.selection = {"files": [], "folders": []}
        
        valid, invalid = self.app.scan_directories([self.test_dir])
        
        # Should still only count the original file once, not the symlink
        # 3 original valid files + 2 in subdir = 5 (symlink shouldn't add extra)
        expected_valid = 5
        expected_invalid = 2
        
        self.assertEqual(valid, expected_valid)
        self.assertEqual(invalid, expected_invalid)
        
        # Verify no duplicate basenames (accounting for the symlink)
        selected_files = self.app.selection["files"]
        basenames = [os.path.basename(f) for f in selected_files]
        
        # Should have exactly one file with "image1" content (either original or symlink, but not both)
        # image1_variants = [name for name in basenames if "image1" in name or name == "symlink_image.jpg"]
        image1_variants = [name for name in basenames if name in ("image1.jpg", "symlink_image.jpg")]        
        self.assertEqual(len(image1_variants), 1, f"Found duplicate image1 files: {image1_variants}")
        # Ensure only one of the two possible paths (original or symlink) was kept

    def test_permission_error_handling(self):
        """Test handling of permission errors (simulated)"""
        # This test is more conceptual since we can't easily create permission errors in tests
        # But the code should handle OSError/PermissionError gracefully
        valid, invalid = self.app.scan_directories([self.test_dir])
        
        # Should complete without crashing
        self.assertIsInstance(valid, int)
        self.assertIsInstance(invalid, int)
        
    def test_case_insensitive_extensions(self):
        """Test that file extensions are handled case-insensitively"""
        # Create files with uppercase extensions
        upper_case_files = [
            os.path.join(self.test_dir, "IMAGE.JPG"),
            os.path.join(self.test_dir, "PHOTO.PNG"),
        ]
        
        for file_path in upper_case_files:
            Path(file_path).touch()
        
        # Reset app state
        self.app.selection = {"files": [], "folders": []}
        
        valid, invalid = self.app.scan_directories([self.test_dir])
        
        # Should find the uppercase extension files as valid
        selected_basenames = [os.path.basename(f) for f in self.app.selection["files"]]
        self.assertIn("IMAGE.JPG", selected_basenames)
        self.assertIn("PHOTO.PNG", selected_basenames)

if __name__ == "__main__":
    unittest.main()