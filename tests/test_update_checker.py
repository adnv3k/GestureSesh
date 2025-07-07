#!/usr/bin/env python3
"""
Test script to verify check_update.py changelog parsing works correctly.
"""

import sys
import os
# Add the src directory to sys.path to import gesturesesh modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from gesturesesh.update_checker import UpdateChecker

def test_changelog_parsing():
    """Test the changelog parsing functionality."""
    print("Testing UpdateChecker changelog parsing...")
    
    # Create a mock UpdateChecker instance
    checker = UpdateChecker("0.4.0")  # Simulate current version
    
    # Test the changelog parsing method
    test_versions = ["v0.5.0", "0.5.0"]
    
    for version in test_versions:
        print(f"\nTesting version: {version}")
        notes = checker._fetch_changelog_notes(version)
        print(f"Extracted notes (first 200 chars): {notes[:200]}...")
        
        if "### Added" in notes or "Enhanced dot indicator" in notes or "New version" in notes:
            print("✅ Changelog parsing appears to be working!")
        else:
            print("⚠️ Changelog parsing may not be working as expected")

if __name__ == "__main__":
    try:
        test_changelog_parsing()
    except Exception as e:
        print(f"❌ Test failed: {e}")
