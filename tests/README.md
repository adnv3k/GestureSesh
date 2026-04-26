# GestureSesh Test Suite

This directory contains automated tests for GestureSesh. Most tests are pytest-compatible Python tests; a few packaging checks are platform-specific shell scripts.

## Running Tests

```bash
# Full Python test suite
python -m pytest -q

# Focused app/session tests
python -m pytest tests/test_gesturesesh.py -q
python -m pytest tests/test_selection_order.py -q
python -m pytest tests/test_session_shortcuts.py -q
python -m pytest tests/test_session_image_loader.py -q
python -m pytest tests/test_scan_directories.py -q

# GUI smoke flow
python tools/smoke_gui_test.py
```

## Test Layout

- `test_gesturesesh.py` - MainApp logic and session orchestration tests that share the larger mocked main-window fixture.
- `test_selection_order.py` - Selection order helpers and Selection Order Viewer dialog mutation/performance rules.
- `test_session_shortcuts.py` - Session display shortcut ownership and shortcut-map registration.
- `test_session_image_loader.py` - Session image loader cache behavior and dtype normalization.
- `test_scan_directories.py` - Directory scanning behavior, symlink handling, duplicate filtering, and file type checks.
- `test_update_checker.py` - UpdateChecker changelog parsing, version checks, network handling, and config behavior.
- `test_update_checker_suite.py` - Update checker runner with unit, integration, debug, and no-network modes.
- `debug_changelog.py` - Interactive changelog parsing/debug utility.
- `test_app_launch.sh` - Bash launch check.
- `test_dmg.sh` - macOS DMG packaging check.
- `test_windows_build.ps1` - Windows build check.

## Update Checker Runner

```bash
# Run all update-checker modes without network access
python tests/test_update_checker_suite.py --mode all --no-network

# Run only unit tests
python tests/test_update_checker_suite.py --mode unit --quiet

# Run debug analysis
python tests/test_update_checker_suite.py --mode debug

# Run integration tests
python tests/test_update_checker_suite.py --mode integration
```

## Coverage Notes

- Core selection-order behavior is covered by pure helper tests and dialog logic tests.
- Thumbnail loading has a regression test to ensure the viewer queues only visible rows plus a small buffer, instead of loading every selected image at once.
- Main/session behavior is covered at the orchestration level with mocked Qt widgets; manual QA is still useful for subjective UI smoothness with very large real image libraries.
- Update checker tests use the local `CHANGELOG.md`; network-dependent checks can be skipped with `--no-network`.
