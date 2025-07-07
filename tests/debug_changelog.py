#!/usr/bin/env python3
"""
Debug script to understand why changelog parsing isn't working.
"""

import sys
import os
import re
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_changelog():
    """Debug the changelog parsing."""
    print("Debugging changelog parsing...")
    
    # Fetch the actual changelog
    GITHUB_CHANGELOG_URL = "https://raw.githubusercontent.com/adnv3k/GestureSesh/main/CHANGELOG.md"
    
    try:
        response = requests.get(GITHUB_CHANGELOG_URL, timeout=10)
        response.raise_for_status()
        changelog_content = response.text
        
        print(f"Changelog fetched successfully ({len(changelog_content)} chars)")
        
        # Show the first few lines to understand format
        lines = changelog_content.split('\n')
        print("\nFirst 30 lines of changelog:")
        for i, line in enumerate(lines[:30]):
            print(f"{i+1:2}: {repr(line)}")
        
        # Test different patterns
        version_tag = "v0.5.0"
        clean_version = version_tag.lstrip('v')
        
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
        
        print(f"\nTesting patterns for version: {version_tag}")
        for pattern in version_patterns:
            print(f"\nPattern: {repr(pattern)}")
            pattern_escaped = re.escape(pattern)
            
            # First, just check if the pattern exists
            simple_match = re.search(pattern_escaped, changelog_content, re.MULTILINE)
            if simple_match:
                print(f"  ✅ Simple pattern found at position {simple_match.start()}")
                # Show context around the match
                start = max(0, simple_match.start() - 50)
                end = min(len(changelog_content), simple_match.end() + 200)
                context = changelog_content[start:end]
                print(f"  Context: {repr(context)}")
            else:
                print(f"  ❌ Simple pattern not found")
            
            # Now try the full regex
            full_match = re.search(
                rf'^{pattern_escaped}.*?\n\n(.*?)(?=\n## |$)', 
                changelog_content, 
                re.MULTILINE | re.DOTALL
            )
            
            if full_match:
                print(f"  ✅ Full regex matched!")
                notes = full_match.group(1).strip()
                print(f"  Extracted notes ({len(notes)} chars): {notes[:200]}...")
                return
            else:
                print(f"  ❌ Full regex didn't match")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_changelog()
