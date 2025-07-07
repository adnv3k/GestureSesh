#!/usr/bin/env python3
"""
GestureSesh - A drawing practice application for artists.

Entry point script to run the application.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and run the main function
from gesturesesh.main import main

if __name__ == "__main__":
    main()
