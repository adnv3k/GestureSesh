# GestureSesh Test Suite

This directory contains automated tests for the GestureSesh application.

## Update Checker Tests

### Core Files
- **`test_update_checker.py`** - Comprehensive test suite for UpdateChecker functionality
  - `TestUpdateCheckerChangelog` - Tests for changelog parsing and content extraction
  - `TestUpdateCheckerCore` - Tests for core update checking logic (version comparison, network handling, etc.)
- **`test_update_checker_suite.py`** - Test runner with multiple modes and debug capabilities
- **`debug_changelog.py`** - Interactive debug utility for changelog analysis

### Running Tests

#### Individual Test File
```bash
# Run with pytest (recommended)
python -m pytest tests/test_update_checker.py -v

# Run directly
python tests/test_update_checker.py
```

#### Test Suite Runner
```bash
# Run all tests
python tests/test_update_checker_suite.py --mode all --no-network

# Run only unit tests
python tests/test_update_checker_suite.py --mode unit --quiet

# Run debug analysis
python tests/test_update_checker_suite.py --mode debug

# Run integration tests
python tests/test_update_checker_suite.py --mode integration
```

#### Debug Utility
```bash
# Interactive changelog debugging
python tests/debug_changelog.py
```

### Test Coverage
- ✅ Changelog parsing (multiple formats)
- ✅ Version comparison logic
- ✅ Network error handling
- ✅ Configuration management
- ✅ Update detection workflow
- ✅ Content extraction and formatting

## Other Tests
- `test_gesturesesh.py` - Main application tests
- `test_scan_directories.py` - Directory scanning functionality
- `test_app_launch.sh` - Application launch tests (bash)
- `test_dmg.sh` - macOS DMG packaging tests (bash)
- `test_windows_build.ps1` - Windows build tests (PowerShell)

## Notes
- Update checker tests use local `CHANGELOG.md` file for testing
- Network tests can be skipped with `--no-network` flag
- All tests pass and provide comprehensive coverage of update functionality
